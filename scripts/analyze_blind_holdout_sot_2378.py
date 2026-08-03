"""Validate and summarize the preregistered SOT-2378 blind terminal audit."""
from __future__ import annotations
import argparse, hashlib, json, math, statistics, subprocess
from pathlib import Path

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def wilson(w: int, n: int) -> list[float]:
    z=1.96; p=w/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; m=z/d*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return [max(0,c-m),min(1,c+m)]
def summarize(reports: list[dict]) -> dict:
    matches=[m for r in reports for m in r["matches"]]; wins=sum(bool(m["semantic_won"]) for m in matches); runtimes=[float(m["runtime_s"]) for m in matches]
    opponents={r["opponent"]:{"matches":r["n_matches"],"wins":r["wins_semantic"],"win_rate":r["winrate_semantic_excl_draws"],"faults":r["faults_semantic"],"unfinished":r["unfinished"]} for r in reports}
    seats={str(s):[m for m in matches if m["semantic_seat"]==s] for s in (0,1)}
    return {"matches":len(matches),"wins":wins,"losses":len(matches)-wins,"win_rate":wins/len(matches),"wilson95":wilson(wins,len(matches)),"worst_matchup":min(opponents,key=lambda x:opponents[x]["win_rate"]),"worst_matchup_win_rate":min(x["win_rate"] for x in opponents.values()),"seat_win_rate":{s:sum(bool(m["semantic_won"]) for m in rows)/len(rows) for s,rows in seats.items()},"faults":sum(r["faults_semantic"] for r in reports),"unfinished":sum(r["unfinished"] for r in reports),"illegal_actions":sum(1 for m in matches if m.get("fault") and "illegal" in str(m["fault"]).lower()),"runtime_s":{"mean":statistics.fmean(runtimes),"p50":statistics.median(runtimes),"p95":sorted(runtimes)[math.ceil(.95*len(runtimes))-1],"max":max(runtimes)},"opponents":opponents}
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--output",required=True,type=Path); a=p.parse_args(); manifest=json.loads(a.manifest.read_text()); root=a.manifest.parents[2]; report_dir=root/"artifacts/sot-2378/holdout"
    reports={o["label"]:json.loads((report_dir/f'{o["label"]}.json').read_text()) for o in manifest["opponents"]}; expected=[s for s in manifest["isolation"]["holdout_seeds"] for _ in range(2)]
    for o in manifest["opponents"]:
        r=reports[o["label"]]
        if [m["agent_seed"] for m in r["matches"]]!=expected or [m["semantic_seat"] for m in r["matches"]]!=[0,1]*5 or r["opponent_repo"]!=o["repo"]: raise ValueError(f'{o["label"]}: holdout contract mismatch')
        if subprocess.check_output(["git","rev-parse","HEAD"],cwd=o["repo"],text=True).strip()!=o["commit"] or sha(Path(o["repo"])/"deck.csv")!=o["deck_sha256"]: raise ValueError(f'{o["label"]}: opponent provenance drift')
    prov=manifest["provenance"]; paths={"main_sha256":root/"main.py","deck_sha256":root/"deck.csv","candidate_artifact_sha256":root/"artifacts/sot-2377-action-ranking/public_action_ranker.json","decision_sha256":root/"artifacts/sot-2377-action-ranking/screen-decision.json","source_manifest_sha256":root/"eval/manifests/sot-2377-action-ranking.json"}; actual={k:sha(v) for k,v in paths.items()}
    for k,v in actual.items():
        if v!=prov[("terminal_"+k) if k in {"main_sha256","deck_sha256"} else k]: raise ValueError(f'frozen provenance drift: {k}')
    subprocess.run(["git","merge-base","--is-ancestor",prov["sot_2377_terminal_commit"],"HEAD"],cwd=root,check=True)
    pool=summarize(list(reports.values())); gate=manifest["gate"]; passed=pool["faults"]==gate["faults"] and pool["unfinished"]==gate["unfinished"] and pool["illegal_actions"]==gate["illegal_actions"] and pool["runtime_s"]["max"]<gate["match_runtime_seconds_max"]
    out={"schema_version":1,"issue":"SOT-2378","manifest_sha256":sha(a.manifest),"report_sha256":{k:sha(report_dir/f"{k}.json") for k in reports},"terminal":{**actual,"identity":"champion","candidate":None,"source_decision":"champion_retained","validated":True},"fixed":summarize([reports[x] for x in manifest["pools"]["fixed"]]),"diversified":summarize([reports[x] for x in manifest["pools"]["diversified"]]),"pool":pool,"decision":{"terminal_identity":"champion","promotion_outcome":"champion_retained","promoted_candidate":None,"candidate_behavior_reverted":True,"operational_audit_passed":passed,"kaggle_submitted":False}}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); return 0
if __name__=="__main__": raise SystemExit(main())
