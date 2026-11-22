"""Check complete runtime dependency and hash consistency across both locks."""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DependencyLockConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        cls.lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
        cls.packages = {pkg["name"]: pkg for pkg in cls.lock["package"]}
        cls.requirement_lines = (ROOT / "requirements.lock").read_text(
            encoding="utf-8"
        ).splitlines()

    def test_all_direct_project_and_extra_pins_match_lock(self):
        pins = list(self.project["project"]["dependencies"])
        for group in ("audit", "browser"):
            pins.extend(self.project["dependency-groups"][group])
        for pin in pins:
            with self.subTest(pin=pin):
                self.assertIn("==", pin)
                name, version = pin.split("==", 1)
                normalized = name.lower().replace("_", "-")
                self.assertIn(normalized, self.packages)
                self.assertEqual(self.packages[normalized]["version"], version)

    def test_all_runtime_and_pdf_export_artifact_hashes_match_lock(self):
        direct = [pin.split("==", 1)[0].lower().replace("_", "-")
                  for pin in self.project["project"]["dependencies"]]
        for name in (*direct, "pdfminer-six"):
            with self.subTest(package=name):
                matching = [
                    i for i, line in enumerate(self.requirement_lines)
                    if line.startswith(name + "==")
                ]
                self.assertEqual(len(matching), 1)
                index = matching[0]
                version = self.requirement_lines[index].split("==", 1)[1].split()[0]
                hashes = set()
                for line in self.requirement_lines[index + 1:]:
                    part = line.strip().rstrip(" \\")
                    if not part.startswith("--hash=sha256:"):
                        break
                    hashes.add(part.removeprefix("--hash=sha256:"))
                pkg = self.packages[name]
                self.assertEqual(version, pkg["version"])
                locked = {
                    item["hash"].split(":", 1)[1]
                    for item in [pkg["sdist"], *pkg.get("wheels", [])]
                }
                self.assertEqual(hashes, locked)
                self.assertTrue(hashes)

    def test_audit_tools_have_exact_version_pins(self):
        for pin in self.project["dependency-groups"]["audit"]:
            with self.subTest(pin=pin):
                self.assertRegex(pin, r"^[a-zA-Z0-9_.-]+==[0-9][0-9.]*$")


if __name__ == "__main__":
    unittest.main()
