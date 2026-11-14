#!/usr/bin/env python3
"""Check semantic acceptance requirements on an actually executed demo report."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    with open(args.report) as handle:
        report = json.load(handle)
    cases = {case["scenario"]: case for case in report["cases"]}
    required = {"accepted", "contradictory", "abstention", "correction", "injection", "partial",
                "versioned", "scanned", "duplicate"}
    assert set(cases) == required, "The complete nine-scenario demo must run"
    for name in ("accepted", "correction", "injection", "partial", "versioned", "scanned", "duplicate"):
        assert cases[name]["eligible"] and cases[name]["idempotent_publication"], name
        assert cases[name].get("export_sha256"), name
    assert not cases["contradictory"]["eligible"]
    assert cases["contradictory"]["final_reconciliation"]["status"] == "contradictory"
    assert not cases["abstention"]["eligible"]
    assert cases["partial"]["final_reconciliation"]["status"] == "partial"
    assert any(e["action"] == "field.corrected" for e in cases["correction"]["audit"])
    assert any(u["duplicate"] for u in cases["duplicate"]["uploads"])
    assert all(report["restore"]["export_equality"].values())
    assert len(report["restore"]["export_equality"]) == 7
    assert report["restore"]["database_integrity"] == "ok"
    assert all(j["outcome"] == "done" for j in report["jobs"])
    print("All nine executed demo scenarios and seven restored exports satisfy their assertions.")


if __name__ == "__main__":
    main()
