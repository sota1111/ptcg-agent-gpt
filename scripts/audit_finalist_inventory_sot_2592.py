#!/usr/bin/env python3
"""Fail-closed audit for the SOT-2592 converged finalist inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(inventory_path: Path, repo_root: Path) -> dict[str, Any]:
    inventory = _load(inventory_path)
    errors: list[str] = []
    required = {"entity", "time", "seed", "submission_lineage"}
    contract = inventory.get("selectionContract", {})
    if set(contract.get("requiredIsolationDimensions", [])) != required:
        errors.append("selection contract must require entity/time/seed/submission_lineage")
    if contract.get("kaggleSubmissionAllowed") is not False:
        errors.append("child inventory must prohibit Kaggle submission")
    if contract.get("publicResultPolicy") != "missing_public_is_null_and_never_imputed":
        errors.append("missing public results must fail toward CV, never be imputed")

    records = inventory.get("auditedTerminalArtifacts")
    if not isinstance(records, list) or not records:
        errors.append("auditedTerminalArtifacts must be a non-empty list")
        records = []
    finalist_ids: list[str] = []
    for record in records:
        issue = record.get("issue", "<missing>")
        paths = record.get("paths", {})
        hashes = record.get("sha256", {})
        loaded: dict[str, dict[str, Any]] = {}
        for kind in ("manifest", "handoff", "summary", "fingerprint"):
            relative = paths.get(kind)
            expected = hashes.get(kind)
            if not isinstance(relative, str) or not isinstance(expected, str):
                errors.append(f"{issue}: missing {kind} path/hash")
                continue
            path = repo_root / relative
            if not path.is_file():
                errors.append(f"{issue}: missing {relative}")
                continue
            if _sha256(path) != expected:
                errors.append(f"{issue}: {kind} provenance hash mismatch")
            loaded[kind] = _load(path)

        if len(loaded) != 4:
            continue
        manifest, handoff, summary, fingerprint = (
            loaded["manifest"],
            loaded["handoff"],
            loaded["summary"],
            loaded["fingerprint"],
        )
        if any(document.get("issue") != issue for document in (manifest, handoff, summary)):
            errors.append(f"{issue}: source issue identity mismatch")
        submitted = handoff.get(
            "kaggleSubmitted", handoff.get("submission", {}).get("kaggle_submitted")
        )
        if submitted is not False:
            errors.append(f"{issue}: Kaggle submission must be false")
        candidate = handoff.get("terminal", {}).get("candidate")
        if candidate is not None:
            errors.append(f"{issue}: rejected candidate was re-enabled")

        if record.get("status") != "finalist":
            if not record.get("exclusionReasons"):
                errors.append(f"{issue}: excluded artifact requires explicit reasons")
            continue
        finalist_ids.append(issue)
        isolation = record.get("isolation")
        if not isinstance(isolation, dict) or set(isolation) != required:
            errors.append(f"{issue}: incomplete isolation dimensions")
        elif any(isolation[name] != 0 for name in required):
            errors.append(f"{issue}: isolation overlap is non-zero")
        summary_isolation = summary.get("isolation", {})
        normalized = {
            "entity": max(
                summary_isolation.get("entityOverlap", 0),
                summary_isolation.get("policyEntityOverlap", 0),
                summary_isolation.get("deckEntityOverlap", 0),
            ),
            "time": summary_isolation.get("timeOverlap"),
            "seed": summary_isolation.get("seedOverlap"),
            "submission_lineage": summary_isolation.get(
                "submissionLineageOverlap", summary_isolation.get("lineageOverlap")
            ),
        }
        if normalized != isolation:
            errors.append(f"{issue}: inventory isolation does not match audited summary")
        if summary.get("operationalAuditPassed") is not True:
            errors.append(f"{issue}: source operational audit did not pass")
        if record.get("public") != {"rating": None, "submissionId": None, "observedAt": None}:
            errors.append(f"{issue}: unavailable public result must remain explicit null")
        fp = record.get("fingerprint", {})
        if fp.get("archiveSha256") != fingerprint.get("archive_sha256"):
            errors.append(f"{issue}: archive fingerprint mismatch")
        if fp.get("contentSha256") != fingerprint.get("canonical_content_sha256"):
            errors.append(f"{issue}: content fingerprint mismatch")
        result = handoff.get("result", {})
        cv = record.get("cv", {})
        if (cv.get("matches"), cv.get("wins")) != (result.get("matches"), result.get("wins")):
            errors.append(f"{issue}: CV result does not match handoff")

    if finalist_ids != inventory.get("frozenFinalists"):
        errors.append("frozenFinalists must exactly match ordered finalist records")
    lineages = {r.get("strategyLineage") for r in records if r.get("status") == "finalist"}
    if len(lineages) != len(finalist_ids):
        errors.append("finalist strategy lineages must be unique")
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "issue": inventory.get("issue"),
        "audited": len(records),
        "finalists": finalist_ids,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(audit(args.inventory, args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
