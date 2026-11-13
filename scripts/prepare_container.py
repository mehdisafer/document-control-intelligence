#!/usr/bin/env python3
"""Prepare explicit local container configuration without starting a service."""
import argparse
import json
from pathlib import Path

from dci.config import Settings
from dci.demo import provision_auth


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=["baseline", "local-linear", "local-llm"], default="baseline")
    args = parser.parse_args()
    credentials = args.output.resolve().with_name(args.output.name + "-credentials.json")
    if credentials.exists():
        raise SystemExit("External credential destination already exists; refusing overwrite")
    auth, _ = provision_auth(args.output.resolve())
    (args.output / "credentials.json").rename(credentials)
    auth.chmod(0o644)
    settings = Settings(home=Path("/var/lib/dci"), auth_file=Path("/etc/dci/auth.json"),
                        profile=args.profile,
                        model_path=Path("/models/local-linear.json") if args.profile == "local-linear" else None,
                        llm_config_file=Path("/etc/dci/llm.json") if args.profile == "local-llm" else None,
                        max_workers=1 if args.profile == "local-llm" else 2)
    (args.output / "config.json").write_text(settings.model_dump_json(indent=2) + "\n")
    if args.profile == "local-llm":
        from dci.llm import LlamaConfig
        model = LlamaConfig(model_path=Path("/models/Qwen3-0.6B-Q4_K_M.gguf"),
                            runtime_binary=Path("/llama/llama-server"))
        (args.output / "llm.json").write_text(model.model_dump_json(indent=2) + "\n")
    # Plaintext bearer tokens stay outside the mounted configuration directory.
    print(json.dumps({"configuration_directory": str(args.output.resolve()),
                      "auth_file": str(auth), "profile": args.profile,
                      "credentials_file": str(credentials),
                      "next": "Mount only configuration_directory. Keep the separate credentials file private."}))


if __name__ == "__main__":
    main()
