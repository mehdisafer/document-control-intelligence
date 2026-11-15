"""Real SQLite startup contention, plus isolated error-classification unit checks.

The thread/process/lock tests use fresh temporary databases, not doubles.
Only unsupported-WAL, I/O error and corrupt-migration injection use mocks.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import multiprocessing
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import time
import unittest
from unittest.mock import MagicMock, patch

from dci.config import Settings
from dci.store import Store, StoreError


def _process_start(home, barrier, results):
    try:
        barrier.wait(timeout=15)
        store = Store(Settings(home=Path(home)))
        with closing(store.connect()) as conn:
            result = (conn.execute("PRAGMA user_version").fetchone()[0],
                      conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])
        results.put(("ok", result))
    except BaseException as exc:
        results.put(("error", type(exc).__name__ + ": " + str(exc)))
        raise


class SQLiteStartupTests(unittest.TestCase):
    def assert_schema(self, home):
        with closing(sqlite3.connect(Path(home) / "control.db")) as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_simultaneous_thread_startup_repeated_on_fresh_databases(self):
        with tempfile.TemporaryDirectory() as directory:
            for iteration in range(6):
                home = Path(directory) / str(iteration)
                barrier = Barrier(8)
                def start(_):
                    barrier.wait(timeout=10)
                    return Store(Settings(home=home))
                with ThreadPoolExecutor(max_workers=8) as pool:
                    stores = list(pool.map(start, range(8)))
                self.assertEqual(len(stores), 8)
                self.assert_schema(home)

    def test_independent_processes_share_one_atomic_initial_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            context = multiprocessing.get_context("spawn")
            barrier, results = context.Barrier(4), context.Queue()
            processes = [context.Process(target=_process_start, args=(directory, barrier, results))
                         for _ in range(4)]
            try:
                for process in processes:
                    process.start()
                outcomes = [results.get(timeout=25) for _ in processes]
                for process in processes:
                    process.join(timeout=10)
                    self.assertEqual(process.exitcode, 0)
                self.assertEqual(outcomes, [("ok", (1, 1))] * 4)
                self.assert_schema(directory)
            finally:
                for process in processes:
                    if process.pid is not None and process.is_alive():
                        process.terminate()
                        process.join(timeout=5)
                results.close()
                results.join_thread()

    def test_real_exclusive_lock_is_retried_until_released(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with closing(sqlite3.connect(home / "control.db", isolation_level=None)) as blocker:
                blocker.execute("CREATE TABLE sentinel(value TEXT)")
                blocker.execute("INSERT INTO sentinel VALUES('preserved')")
                blocker.execute("BEGIN EXCLUSIVE")
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(Store, Settings(home=home))
                    try:
                        time.sleep(0.15)
                        self.assertFalse(future.done())
                    finally:
                        blocker.rollback()
                    store = future.result(timeout=10)
                with closing(store.connect()) as conn:
                    self.assertEqual(conn.execute("SELECT value FROM sentinel").fetchone()[0], "preserved")
            self.assert_schema(home)

    def test_lock_budget_expires_and_later_initialization_still_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            with closing(sqlite3.connect(store.db, isolation_level=None)) as blocker:
                blocker.execute("BEGIN IMMEDIATE")
                started = time.monotonic()
                with self.assertRaises(sqlite3.OperationalError) as raised:
                    store.migrate(timeout_seconds=0.2)
                elapsed = time.monotonic() - started
                self.assertEqual(raised.exception.sqlite_errorcode & 0xFF, sqlite3.SQLITE_BUSY)
                self.assertGreaterEqual(elapsed, 0.15)
                self.assertLess(elapsed, 2.0)
                blocker.rollback()
            store.migrate()
            self.assert_schema(directory)

    def test_future_schema_is_not_downgraded_or_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            with closing(store.connect()) as conn:
                conn.execute("PRAGMA user_version=2")
            with self.assertRaises(StoreError) as raised:
                store.migrate()
            self.assertEqual(raised.exception.code, "SCHEMA_TOO_NEW")
            with closing(store.connect()) as conn:
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)

    def test_non_lock_operational_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            error = sqlite3.OperationalError("injected I/O failure")
            error.sqlite_errorcode = sqlite3.SQLITE_IOERR
            with patch.object(store, "connect", side_effect=error) as connect:
                with self.assertRaises(sqlite3.OperationalError) as raised:
                    store.migrate()
                self.assertIs(raised.exception, error)
                connect.assert_called_once()

    def test_unsupported_wal_is_explicit_and_connection_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            connection = MagicMock()
            connection.in_transaction = False
            connection.execute.return_value.fetchone.return_value = ("delete",)
            with patch.object(store, "connect", return_value=connection) as connect:
                with self.assertRaises(StoreError) as raised:
                    store.migrate()
                self.assertEqual(raised.exception.code, "WAL_UNAVAILABLE")
                connect.assert_called_once()
                connection.close.assert_called_once()

    def test_failed_migration_rolls_back_partial_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            corrupt = "CREATE TABLE partial_table(id INTEGER);\nTHIS IS INVALID;\n"
            with patch("dci.store.Path.read_text", return_value=corrupt):
                with self.assertRaises(sqlite3.OperationalError):
                    Store(Settings(home=home))
            with closing(sqlite3.connect(home / "control.db")) as conn:
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='partial_table'").fetchone())
            Store(Settings(home=home))
            self.assert_schema(home)

    def test_connection_setup_failure_closes_its_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            connection = MagicMock()
            connection.execute.side_effect = sqlite3.OperationalError("injected setup failure")
            with patch("dci.store.sqlite3.connect", return_value=connection):
                with self.assertRaises(sqlite3.OperationalError):
                    store.connect()
            connection.close.assert_called_once()

    def test_invalid_migration_budgets_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Settings(home=Path(directory)))
            for budget in (0, -1, 11, float("inf"), float("nan")):
                with self.subTest(budget=budget), self.assertRaises(ValueError):
                    store.migrate(timeout_seconds=budget)
