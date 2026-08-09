"""semantic vs one sibling repo — subprocess-isolated submission battle
(SOT-1838, adapted from ptcg-agent-matsu SOT-1681).

Plays THIS repo's Kaggle submission agent (``main.agent`` + ``deck.csv``)
against another repo's, each in an isolated subprocess (``agent_server.py``
launched with cwd=its repo root — the top-level ``agents`` packages collide
across repos, so they cannot share one interpreter). The host process owns
only the engine (this repo's ``cg.game``, a process-global single battle)
and the orchestration.

Fairness (先後入替): on even matches semantic takes engine seat 0 (先手), on
odd matches the opponent does. Each agent plays its own repo's ``deck.csv``.

Robustness: an agent that raises, emits an illegal action (engine reject),
or whose subprocess dies is charged a **fault** and loses that match; the
faulting server is relaunched for the next match. Faults are reported — the
SOT-1838 acceptance gate is fault 0.

時間切れ evidence: per-seat cumulative think time is tracked host-side
(wall clock around each act() round-trip, subprocess overhead included) and
the per-match maximum is reported against the ~600s match allowance.

The engine has no seed API, so results are statistical, not bit-reproducible.
Shards: run several instances with distinct --tag values and pool the JSON
reports with --aggregate.

Usage (from this repo root):
    python3 eval/battle_vs.py --opponent ../ptcg-agent-matsu --n 30 \
        --json /tmp/semantic_vs_matsu_s1.json
    python3 eval/battle_vs.py --aggregate /tmp/semantic_vs_matsu_s*.json
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "eval", "agent_server.py")
MAX_DECISIONS = 100_000  # engine draws/decks-out long before this
MATCH_TIME_ALLOWANCE_S = 600.0


def public_decision_snapshot(observation: dict, seat: int, action: list | None = None) -> dict:
    """Return only state visible to both players plus the acting player's counts.

    Card identities from either hand/prize zone and the engine's opaque search
    input are deliberately excluded.  Active/bench card contents are public,
    but this diagnostic records only counts and attached-energy totals.
    """
    current = observation.get("current") or {}
    players = current.get("players") or []

    def player_counts(player: dict) -> dict:
        active = [card for card in (player.get("active") or []) if card]
        bench = [card for card in (player.get("bench") or []) if card]
        in_play = active + bench
        return {
            "hand_count": int(player.get("handCount") or 0),
            "bench_count": len(bench),
            "prize_count": len(player.get("prize") or []),
            "deck_count": int(player.get("deckCount") or 0),
            "discard_count": len(player.get("discard") or []),
            "active_energy_count": sum(len(card.get("energies") or []) for card in active),
            "board_energy_count": sum(len(card.get("energies") or []) for card in in_play),
            "pokemon_count": len(in_play),
            "hp_total": sum(int(card.get("hp") or 0) for card in in_play),
        }

    rows = [player_counts(player or {}) for player in players[:2]]
    while len(rows) < 2:
        rows.append(player_counts({}))
    own = rows[seat]
    opponent = rows[1 - seat]
    selection = observation.get("select") or {}
    options = selection.get("option") or []
    option_types = [int(option.get("type", -1)) for option in options if isinstance(option, dict)]
    chosen_types = [
        option_types[index] for index in (action or []) if 0 <= int(index) < len(option_types)
    ]
    return {
        "turn_index": int(current.get("turn") or 0),
        "turn_action_count": int(current.get("turnActionCount") or 0),
        "selection_context": selection.get("context"),
        "hand_count_delta": own["hand_count"] - opponent["hand_count"],
        "bench_count_delta": own["bench_count"] - opponent["bench_count"],
        "prize_count_delta": own["prize_count"] - opponent["prize_count"],
        "own": own,
        "opponent": opponent,
        "energy_already_attached_this_turn": bool(current.get("energyAttached")),
        "energy_attachment_available": 8 in option_types,
        "attack_ready": 13 in option_types,
        "end_turn_available": 14 in option_types,
        "selected_end_turn": 14 in chosen_types,
        "selected_attack": 13 in chosen_types,
        "selected_option_types": chosen_types,
        "legal_option_types": option_types,
        "option_count": len(option_types),
    }


def load_deck(repo: str) -> list:
    with open(os.path.join(repo, "deck.csv")) as f:
        return [int(x) for x in f.read().split("\n")[:60]]


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


class Contestant:
    """One repo's submission agent, driven over a subprocess."""

    def __init__(
        self,
        label: str,
        repo: str,
        seed: int,
        deck_path: str | None = None,
        capture_determinization: bool = False,
        public_telemetry_only: bool = False,
        env_overrides: dict[str, str] | None = None,
    ):
        self.label = label
        self.repo = os.path.abspath(repo)
        self.deck = (
            [int(value) for value in Path(deck_path).read_text().splitlines() if value]
            if deck_path
            else load_deck(self.repo)
        )
        if len(self.deck) != 60:
            raise ValueError(f"{deck_path or self.repo + '/deck.csv'} must contain 60 cards")
        self.proc = None
        self.seed = seed
        self.capture_determinization = capture_determinization
        self.public_telemetry_only = public_telemetry_only
        self.env_overrides = dict(env_overrides or {})
        self.last_telemetry = {}

    @property
    def python(self) -> str:
        venv = os.path.join(self.repo, "venv", "bin", "python")
        return venv if os.path.exists(venv) else sys.executable

    def start(self) -> None:
        env = dict(os.environ)
        env.update(self.env_overrides)
        env["PYTHONPATH"] = os.pathsep.join(
            value for value in (REPO, env.get("PYTHONPATH", "")) if value
        )
        env["AGENT_SEED"] = str(self.seed)
        if self.capture_determinization:
            env["PTCG_TELEMETRY_PROTOCOL"] = "1"
        self.proc = subprocess.Popen(
            [self.python, SERVER],
            cwd=self.repo,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        line = self.proc.stderr.readline()
        if not line.startswith("READY"):
            err = self.proc.stderr.read()
            raise RuntimeError(f"{self.label} agent failed to start: {line}{err}")

    def act(self, obs: dict) -> list:
        assert self.proc is not None
        self.proc.stdin.write(json.dumps(obs))
        self.proc.stdin.write("\n")
        self.proc.stdin.flush()
        reply = self.proc.stdout.readline()
        if reply == "":  # server died
            raise RuntimeError(f"{self.label} agent server exited")
        action = json.loads(reply)
        if isinstance(action, dict) and "__error__" in action:
            raise RuntimeError(f"{self.label} agent error: {action['__error__']}")
        if self.capture_determinization:
            self.last_telemetry = action.get("telemetry") or {}
            action = action["action"]
        return action

    def telemetry(self) -> dict:
        """Return planner trace, optionally removing hidden-world fingerprints."""
        telemetry = dict(self.last_telemetry)
        if self.public_telemetry_only:
            telemetry["world_roots"] = [
                {key: value for key, value in root.items() if key != "fingerprint"}
                for root in telemetry.get("world_roots", [])
            ]
        return telemetry

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 - best-effort teardown
            self.proc.kill()
        self.proc = None

    def restart(self) -> None:
        self.stop()
        self.start()


def play_match(game, seat0: Contestant, seat1: Contestant) -> dict:
    """One engine match. result: winner seat (0/1), 2=draw, -1=unfinished."""
    obs, start = game.battle_start(seat0.deck, seat1.deck)
    if obs is None:
        raise RuntimeError(
            f"battle_start failed: errorPlayer={start.errorPlayer} errorType={start.errorType}"
        )
    steps = 0
    think = [0.0, 0.0]  # per-seat cumulative act() wall clock
    contexts = [Counter(), Counter()]
    telemetry = [
        {
            "decisions": 0,
            "branching_decisions": 0,
            "max_options": 0,
            "min_deck_count": 60,
            "min_prize_count": 6,
        },
        {
            "decisions": 0,
            "branching_decisions": 0,
            "max_options": 0,
            "min_deck_count": 60,
            "min_prize_count": 6,
        },
    ]
    determinization = [[], []]

    def observe(current: dict, seat: int, observation: dict) -> None:
        players = current.get("players") or []
        if len(players) > seat:
            player = players[seat] or {}
            telemetry[seat]["min_deck_count"] = min(
                telemetry[seat]["min_deck_count"], int(player.get("deckCount") or 0)
            )
            telemetry[seat]["min_prize_count"] = min(
                telemetry[seat]["min_prize_count"], len(player.get("prize") or [])
            )
        selection = observation.get("select") or {}
        options = selection.get("option") or []
        option_count = len(options) if isinstance(options, list) else 0
        telemetry[seat]["decisions"] += 1
        telemetry[seat]["max_options"] = max(telemetry[seat]["max_options"], option_count)
        telemetry[seat]["branching_decisions"] += int(option_count > 6)

    def finish_payload(result: int, fault_seat: int | None = None) -> dict:
        current = obs.get("current") or {}
        players = current.get("players") or []
        final_players = []
        for player in players[:2]:
            player = player or {}
            final_players.append(
                {
                    "deck_count": int(player.get("deckCount") or 0),
                    "prize_count": len(player.get("prize") or []),
                    "hand_count": int(player.get("handCount") or 0),
                    "bench_count": len(player.get("bench") or []),
                }
            )
        return {
            "result": result,
            "steps": steps,
            "fault_seat": fault_seat,
            "think": think,
            "contexts": contexts,
            "telemetry": telemetry,
            "determinization": determinization,
            "final_players": final_players,
        }

    try:
        while steps < MAX_DECISIONS:
            cur = obs.get("current") or {}
            result = cur.get("result", -1)
            if result != -1:
                return finish_payload(result)
            seat = cur.get("yourIndex", 0)
            observe(cur, seat, obs)
            context = (obs.get("select") or {}).get("context")
            if isinstance(context, int):
                contexts[seat][context] += 1
            agent = seat0 if seat == 0 else seat1
            t0 = time.perf_counter()
            try:
                action = agent.act(obs)
                if agent.capture_determinization:
                    determinization[seat].append(
                        {
                            "step": steps,
                            "selection_context": (obs.get("select") or {}).get("context"),
                            "public_state": public_decision_snapshot(obs, seat, action),
                            **agent.telemetry(),
                        }
                    )
            except Exception:  # noqa: BLE001 - agent fault => that seat loses
                return finish_payload(1 - seat, seat)
            finally:
                think[seat] += time.perf_counter() - t0
            try:
                obs = game.battle_select(action)
            except Exception:  # noqa: BLE001 - engine reject => illegal move
                return finish_payload(1 - seat, seat)
            steps += 1
        return finish_payload(-1)
    finally:
        game.battle_finish()


def run(
    opponent_repo: str,
    opponent_label: str,
    seeds: int,
    base_seed: int,
    semantic_deck: str | None = None,
    opponent_deck: str | None = None,
    public_telemetry_only: bool = False,
    semantic_env: dict[str, str] | None = None,
) -> dict:
    sys.path.insert(0, REPO)
    os.chdir(REPO)  # libcg.so resolves relative to the repo root
    from cg import game

    semantic = Contestant(
        "semantic",
        REPO,
        base_seed,
        semantic_deck,
        capture_determinization=True,
        public_telemetry_only=public_telemetry_only,
        env_overrides=semantic_env,
    )
    opp = Contestant(opponent_label, opponent_repo, base_seed, opponent_deck)
    semantic.start()
    opp.start()
    stats = {
        "wins_semantic": 0,
        "wins_opp": 0,
        "draws": 0,
        "unfinished": 0,
        "faults_semantic": 0,
        "faults_opp": 0,
        "wins_semantic_as_first": 0,
        "n_semantic_as_first": 0,
    }
    max_think = {"semantic": 0.0, opponent_label: 0.0}
    match_times = []
    matches = []
    semantic_contexts = Counter()
    try:
        n = seeds * 2
        for i in range(n):
            if i and i % 2 == 0:
                seed = base_seed + i // 2
                semantic.seed = seed
                opp.seed = seed
                semantic.restart()
                opp.restart()
            semantic_seat = i % 2  # 先後入替
            seat0, seat1 = (semantic, opp) if semantic_seat == 0 else (opp, semantic)
            t0 = time.perf_counter()
            out = play_match(game, seat0, seat1)
            runtime_s = time.perf_counter() - t0
            semantic_contexts.update(out["contexts"][semantic_seat])
            match_times.append(runtime_s)
            for seat, contestant in ((0, seat0), (1, seat1)):
                max_think[contestant.label] = max(max_think[contestant.label], out["think"][seat])
            if out["fault_seat"] is not None:
                faulter = seat0 if out["fault_seat"] == 0 else seat1
                key = "faults_semantic" if faulter is semantic else "faults_opp"
                stats[key] += 1
                faulter.restart()
            result = out["result"]
            if result in (0, 1):
                semantic_won = result == semantic_seat
                stats["wins_semantic" if semantic_won else "wins_opp"] += 1
                if semantic_seat == 0:
                    stats["n_semantic_as_first"] += 1
                    stats["wins_semantic_as_first"] += int(semantic_won)
            elif result == 2:
                stats["draws"] += 1
            else:
                stats["unfinished"] += 1
            winner = (
                seat0.label
                if result == 0
                else seat1.label
                if result == 1
                else "draw"
                if result == 2
                else "unfinished"
            )
            matches.append(
                {
                    "match_index": i,
                    "agent_seed": base_seed + i // 2,
                    "semantic_seat": semantic_seat,
                    "semantic_first": semantic_seat == 0,
                    "winner": winner,
                    "semantic_won": winner == "semantic",
                    "result_seat": result,
                    "steps": out["steps"],
                    "fault": (
                        None
                        if out["fault_seat"] is None
                        else (seat0 if out["fault_seat"] == 0 else seat1).label
                    ),
                    "unfinished": result == -1,
                    "runtime_s": runtime_s,
                    "think_s": {
                        "semantic": out["think"][semantic_seat],
                        opponent_label: out["think"][1 - semantic_seat],
                    },
                    "semantic_telemetry": out["telemetry"][semantic_seat],
                    "determinization_telemetry": out["determinization"][semantic_seat],
                    "opponent_telemetry": out["telemetry"][1 - semantic_seat],
                    "semantic_contexts": {
                        str(context): count
                        for context, count in sorted(out["contexts"][semantic_seat].items())
                    },
                    "final": {
                        "semantic": out["final_players"][semantic_seat],
                        opponent_label: out["final_players"][1 - semantic_seat],
                    },
                }
            )
            print(
                f"  match {i + 1}/{n}: "
                f"semantic {stats['wins_semantic']} - {stats['wins_opp']} "
                f"{opponent_label} (draws {stats['draws']}, faults "
                f"F{stats['faults_semantic']}/O{stats['faults_opp']})",
                flush=True,
            )
    finally:
        semantic.stop()
        opp.stop()

    decided = stats["wins_semantic"] + stats["wins_opp"]
    lo, hi = wilson_ci(stats["wins_semantic"], decided)
    from agents.rule_policy import uses_generic_ordering

    generic_contexts = {
        str(context): count
        for context, count in sorted(
            semantic_contexts.items(), key=lambda item: (-item[1], item[0])
        )
        if uses_generic_ordering(context)
    }
    target_contexts = {
        str(context): {
            "decisions": semantic_contexts.get(context, 0),
            "generic_ordering_fallbacks": (
                semantic_contexts.get(context, 0) if uses_generic_ordering(context) else 0
            ),
            "explicit_rule": not uses_generic_ordering(context),
        }
        for context in (2, 38)
    }
    return {
        "semantic_repo": REPO,
        "opponent_repo": os.path.abspath(opponent_repo),
        "opponent": opponent_label,
        "n_matches": n,
        "seeds": seeds,
        "base_seed": base_seed,
        "semantic_deck": os.path.abspath(semantic_deck) if semantic_deck else "deck.csv",
        **stats,
        "winrate_semantic_excl_draws": (stats["wins_semantic"] / decided if decided else None),
        "wilson95_excl_draws": [lo, hi],
        "winrate_semantic_draws_half": (stats["wins_semantic"] + 0.5 * stats["draws"]) / n
        if n
        else None,
        "max_think_s": max_think,
        "match_time_allowance_s": MATCH_TIME_ALLOWANCE_S,
        "time_per_match_sec": {
            "mean": sum(match_times) / len(match_times) if match_times else 0,
            "max": max(match_times) if match_times else 0,
            "total": sum(match_times),
        },
        "context_decisions": {
            str(context): count
            for context, count in sorted(
                semantic_contexts.items(), key=lambda item: (-item[1], item[0])
            )
        },
        "generic_ordering_contexts": generic_contexts,
        "generic_ordering_decisions": sum(generic_contexts.values()),
        "draw_bench_contexts": target_contexts,
        "matches": matches,
    }


def promotion_decision(report: dict) -> dict:
    """Apply the SOT-1838 champion gate to a completed A/B report."""
    reasons = []
    if report.get("seeds", 0) < 20:
        reasons.append("fewer than 20 fixed agent seeds")
    if (report.get("winrate_semantic_excl_draws") or 0.0) < 0.60:
        reasons.append("win rate below 60%")
    if report.get("wilson95_excl_draws", [0.0])[0] <= 0.50:
        reasons.append("Wilson 95% lower bound does not exceed 50%")
    if report.get("faults_semantic", 0):
        reasons.append("semantic policy fault observed")
    if report.get("unfinished", 0):
        reasons.append("unfinished match observed")
    if report.get("max_think_s", {}).get("semantic", 601.0) >= MATCH_TIME_ALLOWANCE_S:
        reasons.append("600 second match budget exceeded")
    return {"promote": not reasons, "reasons": reasons}


def aggregate(paths: list) -> dict:
    shards = [json.loads(Path(p).read_text()) for p in paths]
    opponents = {s["opponent"] for s in shards}
    if len(opponents) != 1:
        raise SystemExit(f"shards disagree on opponent: {opponents}")
    out = {"opponent": shards[0]["opponent"], "shards": len(shards)}
    for key in (
        "n_matches",
        "wins_semantic",
        "wins_opp",
        "draws",
        "unfinished",
        "faults_semantic",
        "faults_opp",
        "wins_semantic_as_first",
        "n_semantic_as_first",
    ):
        out[key] = sum(s.get(key, 0) for s in shards)
    out["max_think_s"] = {
        label: max(s["max_think_s"].get(label, 0.0) for s in shards)
        for label in shards[0]["max_think_s"]
    }
    decided = out["wins_semantic"] + out["wins_opp"]
    lo, hi = wilson_ci(out["wins_semantic"], decided)
    out["winrate_semantic_excl_draws"] = out["wins_semantic"] / decided if decided else None
    out["wilson95_excl_draws"] = [lo, hi]
    n = out["n_matches"]
    out["winrate_semantic_draws_half"] = (
        (out["wins_semantic"] + 0.5 * out["draws"]) / n if n else None
    )
    return out


def summarize(report: dict) -> str:
    lo, hi = report["wilson95_excl_draws"]
    first = (
        f"{report['wins_semantic_as_first']}/{report['n_semantic_as_first']}"
        if report.get("n_semantic_as_first")
        else "n/a"
    )
    return (
        f"semantic vs {report['opponent']}: n={report['n_matches']}  "
        f"semantic {report['wins_semantic']} - {report['wins_opp']} "
        f"(draws {report['draws']}, unfinished {report['unfinished']})\n"
        f"  win rate (excl. draws): {report['winrate_semantic_excl_draws']:.4f}"
        f"  Wilson95 [{lo:.4f}, {hi:.4f}]  (先手 {first})\n"
        f"  faults: semantic {report['faults_semantic']}  "
        f"{report['opponent']} {report['faults_opp']}\n"
        f"  max think/match: {report['max_think_s']}\n"
        f"  promotion: {promotion_decision(report)}"
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--opponent",
        default="eval/hash_baseline",
        help="opponent repo path (default: frozen hash baseline)",
    )
    p.add_argument("--label", default=None, help="opponent label (default: repo basename)")
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--base-seed", type=int, default=20260722)
    p.add_argument(
        "--semantic-deck",
        default=None,
        help="candidate deck CSV for semantic (default: repository deck.csv)",
    )
    p.add_argument(
        "--opponent-deck",
        default=None,
        help="frozen opponent deck CSV (default: opponent repository deck.csv)",
    )
    p.add_argument(
        "--public-telemetry-only",
        action="store_true",
        help="omit hidden-world fingerprints while retaining root action/value telemetry",
    )
    p.add_argument(
        "--semantic-env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="evaluation-only environment override for the semantic contestant",
    )
    p.add_argument("--json", default=None)
    p.add_argument(
        "--aggregate",
        nargs="+",
        default=None,
        metavar="SHARD.json",
        help="pool shard reports and exit",
    )
    args = p.parse_args()

    if args.aggregate:
        report = aggregate(args.aggregate)
    else:
        label = args.label or os.path.basename(os.path.abspath(args.opponent)).replace(
            "ptcg-agent-", ""
        )
        report = run(
            args.opponent,
            label,
            args.seeds,
            args.base_seed,
            args.semantic_deck,
            args.opponent_deck,
            args.public_telemetry_only,
            dict(value.split("=", 1) for value in args.semantic_env),
        )
        report["promotion"] = promotion_decision(report)
    print(summarize(report))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
