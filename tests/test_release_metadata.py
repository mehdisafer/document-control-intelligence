"""Release metadata and application identity must agree before tagging GitHub.

These are source- and runtime-level tests, not evidence of a deployment.
"""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import secrets
import tempfile
import tomllib
import unittest

from fastapi.testclient import TestClient

from dci import __version__
from dci.api import create_app
from dci.config import Settings


ROOT = Path(__file__).resolve().parents[1]
DIST_NAME = "document-control-intelligence"


def release_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]["version"]


class ReleaseIdentityTests(unittest.TestCase):
    def test_project_lock_and_installed_package_versions_agree(self):
        project_version = release_version()
        with (ROOT / "uv.lock").open("rb") as stream:
            lock = tomllib.load(stream)
        candidates = [p for p in lock["package"] if p["name"] == DIST_NAME]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source"], {"editable": "."})
        self.assertEqual(candidates[0]["version"], project_version)
        self.assertEqual(__version__, project_version)
        self.assertEqual(metadata.version(DIST_NAME), project_version)

    def test_api_application_and_healthz_return_the_installed_version(self):
        with tempfile.TemporaryDirectory(prefix="dci-release-version-") as directory:
            root = Path(directory)
            token = secrets.token_urlsafe(32)
            auth_file = root / "auth.json"
            auth_file.write_text(json.dumps({
                "schema_version": "1.0",
                "actors": [{
                    "name": "release-test-reader",
                    "roles": ["reader"],
                    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                }],
            }))
            app = create_app(Settings(home=root / "state", auth_file=auth_file))
            self.assertEqual(app.version, release_version())
            with TestClient(app) as client:
                response = client.get("/healthz")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), {
                    "status": "alive", "version": release_version(),
                })

    def test_local_compose_and_terraform_image_tags_match(self):
        version = release_version()
        for filename, count in [("compose.yaml", 2), ("compose.llm.yaml", 1)]:
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                tags = re.findall(r"^\s*image:\s*dci:([^\s#]+)", text, re.MULTILINE)
                self.assertEqual(len(tags), count)
                self.assertEqual(tags, [version] * count)
        terraform = (ROOT / "infra/terraform/main.tf").read_text(encoding="utf-8")
        self.assertIn("dci:" + version, terraform)

    def test_release_notes_and_license_match_package(self):
        with (ROOT / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)["project"]
        version = project["version"]
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertEqual(set(project["license-files"]), {"LICENSE", "NOTICE"})
        for filename in project["license-files"]:
            self.assertTrue((ROOT / filename).is_file(), filename)
        notes = ROOT / f"docs/RELEASE_NOTES_{version}.md"
        self.assertTrue(notes.is_file(), str(notes))
        self.assertIn(f"# Document Control Intelligence {version}",
                      notes.read_text(encoding="utf-8"))
