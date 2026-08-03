"""Build and diagnose the SOT-2345 diversified public-state oracle corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.battle_vs import run  # noqa: E402
from ptcg_agent.runtime_dataset import (  # noqa: E402
    PUBLIC_FEATURE_ALLOWLIST,
    provenance_fingerprint,
    public_feature_vector,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def heuristic_value(state: dict[str, Any]) -> float:
    """Reproduce the champion's default public components without card identities."""

    def score(side: dict[str, Any]) -> float:
        value = 2.0 * max(0, 6 - int(side.get("prize_count", 0)))
        value += 0.3 * int(side.get("pokemon_count", 0))
        value += 0.2 * int(side.get("board_energy_count", 0))
        value += 0.004 * int(side.get("hp_total", 0))
        value += 0.06 * int(side.get("hand_count", 0))
        if int(side.get("deck_count", 0)) == 0:
            value -= 3.0
        return value

    diff = score(state.get("own") or {}) - score(state.get("opponent") or {})
    return 1.0 / (1.0 + math.exp(-0.6 * diff))


def opponent_fingerprint(repo: Path) -> str:
    digest = hashlib.sha256()
    for relative in ("main.py", "deck.csv"):
        path = repo / relative
        digest.update(relative.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def collect(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for split, phase in manifest["splits"].items():
        for opponent in manifest["opponents"]:
            repo = (ROOT / opponent["repo"]).resolve()
            fingerprint = opponent_fingerprint(repo)
            report = run(
                str(repo),
                opponent["id"],
                len(phase["seeds"]),
                phase["seeds"][0],
                public_telemetry_only=True,
            )
            for match in report["matches"]:
                outcome = (
                    1.0 if match["semantic_won"] else 0.5 if match["winner"] == "draw" else 0.0
                )
                unit = provenance_fingerprint(
                    match["agent_seed"], match["semantic_seat"], fingerprint
                )
                for index, event in enumerate(match["determinization_telemetry"]):
                    state = event["public_state"]
                    chosen = state.get("selected_option_types") or []
                    legal = sorted(set(chosen) | {-1})
                    records.append(
                        {
                            "schemaVersion": "2.0.0",
                            "split": split,
                            "features": list(public_feature_vector(state)),
                            "legalActions": legal,
                            "action": chosen[0] if chosen else -1,
                            "value": outcome,
                            "heuristicValue": heuristic_value(state),
                            "provenanceFingerprint": unit,
                            "seed": match["agent_seed"],
                            "seat": match["semantic_seat"],
                            "opponentFingerprint": fingerprint,
                            "decisionIndex": index,
                        }
                    )
    return records


def auc(rows: list[dict[str, Any]]) -> float | None:
    positive = [row for row in rows if row["value"] == 1.0]
    negative = [row for row in rows if row["value"] == 0.0]
    if not positive or not negative:
        return None
    wins = sum(
        (p["heuristicValue"] > n["heuristicValue"])
        + 0.5 * (p["heuristicValue"] == n["heuristicValue"])
        for p in positive
        for n in negative
    )
    return wins / (len(positive) * len(negative))


def diagnostics(records: list[dict[str, Any]], corpus_path: Path) -> dict[str, Any]:
    units: dict[str, set[str]] = defaultdict(set)
    for row in records:
        units[row["split"]].add(row["provenanceFingerprint"])
    overlap = {
        f"{left}:{right}": sorted(units[left] & units[right])
        for left in units
        for right in units
        if left < right
    }
    by_split: dict[str, Any] = {}
    for split in sorted(units):
        rows = [row for row in records if row["split"] == split]
        slices: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = f"{row.get('opponentFingerprint', 'unknown')[:12]}:seat{row.get('seat', '?')}"
            slices[key].append(row)
        by_split[split] = {
            "samples": len(rows),
            "match_units": len(units[split]),
            "brier_score": sum((row["heuristicValue"] - row["value"]) ** 2 for row in rows)
            / len(rows),
            "roc_auc": auc(rows),
            "matchupSeat": {
                key: {
                    "samples": len(slice_rows),
                    "brier_score": sum(
                        (row["heuristicValue"] - row["value"]) ** 2 for row in slice_rows
                    )
                    / len(slice_rows),
                    "roc_auc": auc(slice_rows),
                }
                for key, slice_rows in sorted(slices.items())
            },
        }
    try:
        corpus_label = str(corpus_path.relative_to(ROOT))
    except ValueError:
        corpus_label = str(corpus_path)
    return {
        "schemaVersion": "1.0.0",
        "corpus": corpus_label,
        "corpusSha256": file_sha256(corpus_path),
        "publicFeatureAllowlist": list(PUBLIC_FEATURE_ALLOWLIST),
        "forbiddenModelFeatures": ["hidden_cards", "world_fingerprint", "opponent_identity"],
        "splitOverlap": overlap,
        "splitLeakagePassed": all(not values for values in overlap.values()),
        "heuristicBaseline": by_split,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = collect(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8"
    )
    result = diagnostics(records, args.output.resolve())
    args.diagnostics.parent.mkdir(parents=True, exist_ok=True)
    args.diagnostics.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
