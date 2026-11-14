#!/usr/bin/env python3
"""Focused repository-secret check. This is not a general DLP certification."""
import argparse
import json
from pathlib import Path
import re
import subprocess

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_classic_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "github_fine_grained_token": re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    "aws_access_key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "openai_key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{40,}"),
}
BLOCKED_NAMES = {"credentials.json", "auth.json", ".env", "id_rsa", "id_ed25519"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="Also inspect every reachable commit blob")
    args = parser.parse_args()
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    findings, inspected = [], 0

    def inspect(path, content, ref="working-tree"):
        nonlocal inspected
        inspected += 1
        if Path(path).name in BLOCKED_NAMES or path.endswith((".db", ".db-wal", ".tfstate")):
            findings.append({"path": path, "ref": ref, "rule": "runtime_or_secret_file"})
        text = content.decode("utf-8", errors="ignore")
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": path, "ref": ref, "rule": name})

    for path in filter(None, paths):
        if Path(path).is_file():
            inspect(path, Path(path).read_bytes())
    if args.history:
        commits = subprocess.check_output(["git", "rev-list", "--all"]).decode().splitlines()
        seen = set()
        for commit in commits:
            lines = subprocess.check_output(["git", "ls-tree", "-rz", commit]).decode().split("\0")
            for line in filter(None, lines):
                metadata, path = line.split("\t", 1)
                _, kind, sha = metadata.split()
                if kind != "blob" or sha in seen:
                    continue
                seen.add(sha)
                inspect(path, subprocess.check_output(["git", "cat-file", "blob", sha]), commit)
    print(json.dumps({"checked_objects": inspected, "findings": findings,
                      "scope": "Known credential formats and runtime filenames; manual content review still required"}, indent=2))
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
