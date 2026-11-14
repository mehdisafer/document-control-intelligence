"""Explicit local commands; no startup downloads, external provisioning or cloud fallback."""

import argparse
import json
import logging
from pathlib import Path

from .config import Settings


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dci", description="Document Control Intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a new local workspace and external actor credentials")
    init.add_argument("--home", type=Path, default=Path(".data"))
    corpus = sub.add_parser("corpus", help="Generate synthetic documents and ground truth")
    corpus.add_argument("--output", type=Path, required=True)
    corpus.add_argument("--seed", type=int, default=42)
    corpus.add_argument("--per-split", type=int, default=12)
    train = sub.add_parser("train", help="Train local statistical heads from train PDFs only")
    train.add_argument("--manifest", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    for name in ("serve", "worker", "backup"):
        command = sub.add_parser(name)
        command.add_argument("--config", type=Path)
        if name == "serve":
            command.add_argument("--host", default="127.0.0.1")
            command.add_argument("--port", type=int, default=8000)
        elif name == "worker":
            command.add_argument("--once", action="store_true")
        else:
            command.add_argument("--output", type=Path, required=True)
    restore = sub.add_parser("restore", help="Restore a verified snapshot to a new directory")
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)
    demo = sub.add_parser("demo", help="Execute the synthetic API-to-export demonstration")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--profile", choices=["baseline", "local-linear", "local-llm"], default="baseline")
    demo.add_argument("--model-path", type=Path)
    demo.add_argument("--llm-config", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = getattr(args, "config", None)
    settings = Settings.model_validate_json(config.read_text()) if config else None
    if args.command == "init":
        from .demo import provision_auth
        from .store import Store
        auth, _ = provision_auth(args.home.resolve())
        settings = Settings(home=args.home.resolve(), auth_file=auth)
        Store(settings)
        (args.home / "config.json").write_text(settings.model_dump_json(indent=2) + "\n")
        print(json.dumps({"configuration": str(args.home / "config.json"),
                          "credentials_file": str(args.home / "credentials.json"),
                          "note": "Keep actor credentials outside source control. Tokens are not printed."}))
    elif args.command == "corpus":
        from .corpus import generate_corpus
        if args.output.exists():
            parser.error("Corpus output must be a new directory")
        manifest = generate_corpus(args.output, seed=args.seed, per_split=args.per_split)
        print(json.dumps({"manifest": manifest["manifest_path"], "documents": len(manifest["documents"])}))
    elif args.command == "train":
        from .local_model import train_model
        if args.output.exists():
            parser.error("Model output must not exist; use a new versioned path")
        print(json.dumps(train_model(args.manifest, args.output), indent=2))
    elif args.command == "serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings or Settings.from_env()), host=args.host, port=args.port,
                    timeout_keep_alive=5, limit_concurrency=32, limit_max_requests=10000)
    elif args.command == "worker":
        from .worker import serve
        serve(settings or Settings.from_env(), once=args.once)
    elif args.command == "demo":
        from .demo import run_demo
        result = run_demo(args.output, profile=args.profile, model_path=args.model_path,
                          llm_config_file=args.llm_config)
        print(json.dumps({"evidence": str(args.output / "result.json"), "profile": args.profile,
                          "cases": [{"scenario": c["scenario"], "eligible": c["eligible"],
                                     "reconciliation": c["final_reconciliation"]["status"],
                                     "published": "publication" in c} for c in result["cases"]],
                          "elapsed_seconds": result["elapsed_seconds"]}, indent=2))
    elif args.command == "backup":
        from .operations import backup
        from .store import Store
        print(json.dumps(backup(Store(settings or Settings.from_env()), args.output), indent=2))
    elif args.command == "restore":
        from .operations import restore
        print(json.dumps(restore(args.snapshot, args.output), indent=2))


if __name__ == "__main__":
    main()
