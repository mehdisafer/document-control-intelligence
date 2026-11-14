#!/usr/bin/env python3
"""Export the reviewed Pydantic boundaries; --check detects stale wire schemas."""
import argparse
import json
from pathlib import Path

from dci.config import Settings
from dci.llm import LlamaConfig
from dci.models import CheckResult, Extraction, ParsedDocument, Reconciliation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "contracts"
    models = {"parsed-document-v1": ParsedDocument, "extraction-v1": Extraction,
              "document-checks-v1": CheckResult, "reconciliation-v1": Reconciliation,
              "configuration-v1": Settings, "local-llm-configuration-v1": LlamaConfig}
    stale = []
    for name, model in models.items():
        path = destination / (name + ".schema.json")
        expected = json.dumps(model.model_json_schema(), sort_keys=True, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != expected:
                stale.append(path.name)
        else:
            path.write_text(expected)
    print(json.dumps({"schemas": len(models), "mode": "check" if args.check else "export", "stale": stale}))
    return bool(stale)


if __name__ == "__main__":
    raise SystemExit(main())
