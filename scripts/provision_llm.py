#!/usr/bin/env python3
"""Download only reviewed public model/runtime artifacts; never run at ingestion."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tarfile

ARTIFACTS = [
    ("models/Qwen3-0.6B-Q4_K_M.gguf", "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/1208e45d782fe18602c5eaf10e5758d5b0f24c03/Qwen3-0.6B-Q4_K_M.gguf", "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"),
    ("llama/llama-b12359-bin-ubuntu-x64.tar.gz", "https://github.com/ggml-org/llama.cpp/releases/download/b12359/llama-b12359-bin-ubuntu-x64.tar.gz", "0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".runtime"))
    args = parser.parse_args()
    for relative, url, expected in ARTIFACTS:
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        candidate = target if target.exists() else target.with_suffix(target.suffix + ".partial")
        if not target.exists():
            subprocess.run(["curl", "--fail", "--location", "--max-time", "300", "--silent", "--show-error", url,
                            "--output", str(candidate)], check=True, timeout=310)
        with candidate.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise SystemExit(f"Digest mismatch for {relative}; refusing to load or overwrite")
        if candidate != target:
            candidate.rename(target)
        print(f"Verified {relative}: {actual}")
        if relative.endswith(".tar.gz"):
            destination = args.output / "llama/bin"
            if not destination.exists():
                with tarfile.open(target) as archive:
                    archive.extractall(destination, filter="data")


if __name__ == "__main__":
    main()
