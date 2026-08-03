"""Build the SOT-2376 public legal-action counterfactual oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.battle_vs import run  # noqa: E402


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def public_state(state: dict[str, Any], allowlist: list[str]) -> dict[str, Any]:
    return {key: state[key] for key in allowlist if key in state}


def action_signature(action: list[int], option_types: list[int]) -> list[int]:
    """Represent a root action without option/card identities."""

    return sorted(option_types[index] for index in action if 0 <= index < len(option_types))


def paired_values(event: dict[str, Any], shared_worlds_required: int) -> list[dict[str, Any]]:
    by_action: dict[tuple[int, ...], dict[int, float]] = {}
    for world_index, world in enumerate(event.get("world_roots") or []):
        for row in world.get("actions") or []:
            value = row.get("value_mean")
            if value is not None:
                by_action.setdefault(tuple(row["action"]), {})[world_index] = float(value)
    pairs = []
    for left, right in combinations(sorted(by_action), 2):
        shared = sorted(set(by_action[left]) & set(by_action[right]))
        if len(shared) < shared_worlds_required:
            continue
        deltas = [by_action[left][world] - by_action[right][world] for world in shared]
        pairs.append(
            {
                "left": list(left),
                "right": list(right),
                "sharedWorlds": len(shared),
                "relativeOutcome": statistics.fmean(deltas),
            }
        )
    return pairs


def build_rows(
    manifest: dict[str, Any], reports: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    allowlist = manifest["publicFeatureAllowlist"]
    required = int(manifest["searchBudget"]["sharedWorldsRequired"])
    rows: list[dict[str, Any]] = []
    for split in manifest["splits"]:
        for report in reports.get(split, []):
            for match in report["matches"]:
                match_key = sha256_bytes(canonical([match["agent_seed"], match["semantic_seat"]]))
                for event in match["determinization_telemetry"]:
                    state = event.get("public_state") or {}
                    option_types = [int(value) for value in state.get("legal_option_types") or []]
                    features = public_state(state, allowlist)
                    state_fingerprint = sha256_bytes(canonical(features))
                    for pair_index, pair in enumerate(paired_values(event, required)):
                        left = action_signature(pair.pop("left"), option_types)
                        right = action_signature(pair.pop("right"), option_types)
                        if left == right:
                            continue
                        rows.append(
                            {
                                "schemaVersion": "1.0.0",
                                "split": split,
                                "publicFeatures": features,
                                "leftActionTypes": left,
                                "rightActionTypes": right,
                                **pair,
                                "publicStateFingerprint": state_fingerprint,
                                "provenanceFingerprint": sha256_bytes(
                                    canonical([match_key, event["step"], pair_index])
                                ),
                            }
                        )
    return sorted(
        rows,
        key=lambda row: (row["split"], row["provenanceFingerprint"]),
    )


def coverage_metrics(
    manifest: dict[str, Any], reports: dict[str, list[dict[str, Any]]]
) -> dict[str, int | float]:
    required = int(manifest["searchBudget"]["sharedWorldsRequired"])
    eligible_pairs = supported_pairs = eligible_states = 0
    for split_reports in reports.values():
        for report in split_reports:
            for match in report["matches"]:
                for event in match["determinization_telemetry"]:
                    actions = {
                        tuple(row["action"])
                        for world in event.get("world_roots") or []
                        for row in world.get("actions") or []
                    }
                    pairs = len(actions) * (len(actions) - 1) // 2
                    if pairs:
                        eligible_states += 1
                        eligible_pairs += pairs
                        supported_pairs += len(paired_values(event, required))
    return {
        "eligiblePublicStates": eligible_states,
        "eligibleActionPairs": eligible_pairs,
        "supportedActionPairs": supported_pairs,
        "coverage": supported_pairs / eligible_pairs if eligible_pairs else 0.0,
    }


def diagnostics(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    oracle_path: Path,
    coverage: dict[str, int | float] | None = None,
) -> dict[str, Any]:
    try:
        oracle_label = str(oracle_path.relative_to(ROOT))
    except ValueError:
        oracle_label = str(oracle_path)
    split_units = {
        split: {row["provenanceFingerprint"] for row in rows if row["split"] == split}
        for split in manifest["splits"]
    }
    overlap = {
        f"{left}:{right}": sorted(split_units[left] & split_units[right])
        for left, right in combinations(manifest["splits"], 2)
    }
    split_seeds = {
        split: set(int(seed) for seed in phase["seeds"])
        for split, phase in manifest["splits"].items()
    }
    seed_overlap = {
        f"{left}:{right}": sorted(split_seeds[left] & split_seeds[right])
        for left, right in combinations(manifest["splits"], 2)
    }
    by_split = {}
    for split in manifest["splits"]:
        selected = [row for row in rows if row["split"] == split]
        signals = [abs(row["relativeOutcome"]) for row in selected]
        by_split[split] = {
            "actionPairs": len(selected),
            "publicStates": len({row["publicStateFingerprint"] for row in selected}),
            "nonZeroPairwiseLabels": sum(value > 1e-12 for value in signals),
            "pairwiseSignalRate": (
                sum(
                    value >= manifest["preregisteredGates"]["minimumPairwiseSignal"]
                    for value in signals
                )
                / len(signals)
                if signals
                else 0.0
            ),
            "relativeOutcomeMin": min((row["relativeOutcome"] for row in selected), default=None),
            "relativeOutcomeMax": max((row["relativeOutcome"] for row in selected), default=None),
        }
    if coverage is None:
        states = len({(row["split"], row["publicStateFingerprint"]) for row in rows})
        coverage = {
            "eligiblePublicStates": states,
            "eligibleActionPairs": len(rows),
            "supportedActionPairs": len(rows),
            "coverage": 1.0 if rows else 0.0,
        }
    return {
        "schemaVersion": "1.0.0",
        "axis": manifest["axis"],
        "oracle": oracle_label,
        "oracleSha256": sha256_file(oracle_path),
        "artifactFingerprint": sha256_bytes(
            canonical({"manifest": manifest, "oracleSha256": sha256_file(oracle_path)})
        ),
        "publicFeatureAllowlist": manifest["publicFeatureAllowlist"],
        "forbiddenLearningFeatures": manifest["forbiddenLearningFeatures"],
        "splitOverlap": overlap,
        "seedOverlap": seed_overlap,
        "splitLeakagePassed": all(not values for values in overlap.values())
        and all(not values for values in seed_overlap.values()),
        "coverage": coverage,
        "splits": by_split,
        "preregisteredGates": manifest["preregisteredGates"],
        "screenEligible": (
            coverage["coverage"] >= manifest["preregisteredGates"]["minimumCoverage"]
            and by_split["train"]["pairwiseSignalRate"]
            >= manifest["preregisteredGates"]["minimumPairwiseSignal"]
        ),
        "kaggleSubmissionPerformed": False,
    }


def collect_reports(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    reports: dict[str, list[dict[str, Any]]] = {}
    for split, phase in manifest["splits"].items():
        reports[split] = []
        seeds = phase["seeds"]
        if seeds != list(range(seeds[0], seeds[0] + len(seeds))):
            raise ValueError(f"{split} seeds must be contiguous for the battle harness")
        for opponent in manifest["opponents"]:
            reports[split].append(
                run(
                    str((ROOT / opponent["repo"]).resolve()),
                    opponent["id"],
                    len(seeds),
                    seeds[0],
                    public_telemetry_only=True,
                )
            )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostics", required=True, type=Path)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--write-reports", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    reports = json.loads(args.reports.read_text()) if args.reports else collect_reports(manifest)
    if args.write_reports:
        args.write_reports.parent.mkdir(parents=True, exist_ok=True)
        args.write_reports.write_text(json.dumps(reports, sort_keys=True) + "\n")
    rows = build_rows(manifest, reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    result = diagnostics(manifest, rows, args.output.resolve(), coverage_metrics(manifest, reports))
    args.diagnostics.parent.mkdir(parents=True, exist_ok=True)
    args.diagnostics.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
