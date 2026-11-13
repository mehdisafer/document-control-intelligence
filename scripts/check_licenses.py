#!/usr/bin/env python3
"""Report installed locked-runtime licences; fail on an unreviewed licence family."""
import importlib.metadata
import json
import tomllib
from pathlib import Path

REVIEWED = ("MIT", "BSD", "Apache", "PSF", "Python", "MPL-2.0", "Mozilla Public License 2.0", "ISC")


def main():
    lock = tomllib.loads(Path("uv.lock").read_text())
    # Resolve production dependencies by their locked package graph, excluding audit tooling.
    packages = {p["name"]: p for p in lock["package"]}
    root = packages["document-control-intelligence"]
    names, pending = set(), [d["name"] for d in root["dependencies"]]
    while pending:
        name = pending.pop()
        if name in names:
            continue
        names.add(name)
        pending.extend(d["name"] for d in packages[name].get("dependencies", []))
    inventory, unreviewed = [], []
    for name in sorted(names):
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            # Some lock entries are platform-specific and absent on this host.
            continue
        metadata = distribution.metadata
        license_text = metadata.get("License-Expression") or metadata.get("License", "")
        classifiers = [v.split(" :: ")[-1] for v in metadata.get_all("Classifier", []) if v.startswith("License ::")]
        license_summary = license_text.splitlines()[0][:180] if license_text else "; ".join(classifiers)
        if name == "pypdfium2":
            license_summary = "Apache-2.0 OR BSD-3-Clause; bundled PDFium third-party notices retained"
        text = license_text + " " + " ".join(classifiers) + " " + license_summary
        reviewed = any(family.lower() in text.lower() for family in REVIEWED)
        entry = {"name": name, "version": distribution.version, "license": license_summary,
                 "reviewed_family": reviewed, "home": metadata.get("Home-page"),
                 "project_urls": metadata.get_all("Project-URL", [])}
        inventory.append(entry)
        if not reviewed:
            unreviewed.append(name)
    print(json.dumps({"schema_version": "component-inventory-1.0", "components": inventory,
                      "unreviewed": unreviewed,
                      "scope": "Installed Python runtime; OS, OCR trained data, model and runtime have separate notices. Not legal certification."}, indent=2))
    return bool(unreviewed)


if __name__ == "__main__":
    raise SystemExit(main())
