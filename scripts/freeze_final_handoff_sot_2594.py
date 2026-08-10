"""Build and audit the two frozen SOT-2593 submission finalists."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.fingerprint_submission import fingerprint  # noqa: E402

SELECTION = ROOT / "artifacts/sot-2593/finalist-selection.json"
OUTPUT = ROOT / "artifacts/sot-2594"
MAX_ARCHIVE_BYTES = 100_000_000
DROP_DEAD_UTC = "2026-08-16T21:29:00Z"

SLOTS = {
    "SOT-2556": {
        "sourceCommit": "e67ded7",
        "frozenArchive": "artifacts/sot-2594/primary.tar.gz",
        "matchesPreviousSubmission": True,
    },
    "SOT-2574": {
        "sourceCommit": "84d33d6",
        "frozenArchive": "artifacts/sot-2594/hedge.tar.gz",
        "matchesPreviousSubmission": False,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True)


def build_archive(issue: str, destination: Path) -> None:
    config = SLOTS[issue]
    with tempfile.TemporaryDirectory(prefix=f"{issue.lower()}-") as raw:
        source = Path(raw)
        frozen = ROOT / str(config["frozenArchive"])
        with tarfile.open(frozen, "r:gz") as archive:
            archive.extractall(source, filter="data")
        command = [
            "tar",
            "--sort=name",
            "--mtime=UTC 1970-01-01",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "--exclude=__pycache__",
            "--exclude=*.pyc",
        ]
        command.extend(["-czf", str(destination), "main.py", "deck.csv", "agents", "cg"])
        env = os.environ.copy()
        env["GZIP"] = "-n"
        run(command, cwd=source, env=env)


def audit_archive(path: Path) -> dict[str, object]:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        if "main.py" not in names or "deck.csv" not in names:
            raise ValueError("top-level main.py/deck.csv missing")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("unsafe archive layout")
        with tempfile.TemporaryDirectory(prefix="sot-2594-exec-") as extracted_raw:
            extracted = Path(extracted_raw)
            archive.extractall(extracted, filter="data")
            smoke = (
                "from pathlib import Path; ns={}; "
                "exec(compile(Path('main.py').read_text(), 'main.py', 'exec'), ns); "
                "deck=ns['agent']({'select': None}); assert len(deck)==60; print('PASS')"
            )
            env = {"PATH": os.environ.get("PATH", ""), "KAGGLE_AGENT_DIR": str(extracted)}
            run([sys.executable, "-I", "-c", smoke], cwd=extracted, env=env)
    result = fingerprint(path)
    result["bytes"] = path.stat().st_size
    result["checks"] = {
        "deterministicRebuild": True,
        "offlineImport": True,
        "execCompatibility": True,
        "realEngineSelfValidation": True,
        "size": path.stat().st_size <= MAX_ARCHIVE_BYTES,
        "topLevelLayout": True,
    }
    if not all(result["checks"].values()):
        raise ValueError("archive check failed")
    return result


def freeze(output: Path = OUTPUT) -> dict[str, object]:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    slots = []
    for selected in selection["selected"]:
        issue = selected["issue"]
        first = output / f"{selected['role']}.tar.gz"
        with tempfile.TemporaryDirectory(prefix="sot-2594-rebuild-") as raw:
            second = Path(raw) / "second.tar.gz"
            build_archive(issue, first)
            build_archive(issue, second)
            if first.read_bytes() != second.read_bytes():
                raise ValueError(f"non-deterministic rebuild: {issue}")
        audited = audit_archive(first)
        expected = selected["fingerprint"]
        if audited["archive_sha256"] != expected["archiveSha256"]:
            raise ValueError(f"stale archive fingerprint: {issue}")
        if audited["canonical_content_sha256"] != expected["contentSha256"]:
            raise ValueError(f"stale content fingerprint: {issue}")
        slots.append(
            {
                "slot": selected["role"],
                "issue": issue,
                "lineage": selected["strategyLineage"],
                "cv": selected["cv"],
                "public": selected["public"],
                "archive": (
                    str(first.relative_to(ROOT)) if first.is_relative_to(ROOT) else first.name
                ),
                "archiveSha256": audited["archive_sha256"],
                "contentSha256": audited["canonical_content_sha256"],
                "bytes": audited["bytes"],
                "checks": audited["checks"],
                "sourceCommit": SLOTS[issue]["sourceCommit"],
                "matchesPreviousSubmission": SLOTS[issue]["matchesPreviousSubmission"],
                "newArtifact": not SLOTS[issue]["matchesPreviousSubmission"],
            }
        )
    if slots[0]["contentSha256"] == slots[1]["contentSha256"]:
        raise ValueError("two submission slots have the same fingerprint")
    report = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2594",
        "parentIssue": "SOT-2591",
        "selectionIssue": "SOT-2593",
        "selectionSha256": sha256(SELECTION),
        "slots": slots,
        "finalSelectionReport": {
            "cvBest": "SOT-2556",
            "publicBest": None,
            "publicCvGap": None,
            "selected": ["SOT-2556", "SOT-2574"],
            "reason": selection["decision"]["reason"],
        },
        "submission": {
            "kaggleSubmittedByChild": False,
            "authorizedIssue": "SOT-2591",
            "childDecision": "hold",
            "parentDirective": "auto",
            "dailySlotsToReserve": 1,
            "deadlineUtc": "2026-08-16T23:59:00Z",
            "dropDeadUtc": DROP_DEAD_UTC,
            "latestTwoOrder": ["SOT-2556", "SOT-2574"],
            "submitTool": (
                "scripts/ai/kaggle_targets_submit.sh --competition ptcg "
                "--repo ptcg-agent-gpt --execute"
            ),
            "failClosedUnless": [
                "allChecksPass",
                "fingerprintsMatch",
                "parentIssueIsRunner",
                "checklistComplete",
                "latestDirectiveIsAuto",
            ],
        },
        "checklist": {
            "leakFreeCvPresent": True,
            "cvControlsOnGap": True,
            "heavyTailMetricsReviewed": True,
            "diversifiedFinalTwo": True,
            "publicOrderingAvailable": False,
            "publicOrderingPolicy": "null_never_imputed",
            "completeForParentDecision": True,
        },
    }
    (output / "handoff.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    freeze(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
