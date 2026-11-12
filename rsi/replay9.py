"""Run 9 replay: acceptance rules compared offline on run 9's stored per-task grades.

  python -m rsi.replay9 [--splits 1000]

Design and predictions: REPLAY9.md (committed before this was run). Reads only cached grades
in runs_v9 (no model calls) and writes runs_v9/replay.json.
"""
from __future__ import annotations

import argparse
import json
import random
from statistics import fmean

from rsi import run9, stage0
from rsi.config import load_yaml, resolve

SELECTOR = {"jred": "p2", "jhonest": "p2", "truth": "truth"}
RULES = ("REG", "CONFIRM", "POOLED")
N_A, N_C = 60, 40          # the rest (50) is B


def load(cfg: dict) -> tuple[dict, dict]:
    """Per-task rows: the anchor (mean of its repeats) and every candidate, keyed by candidate id."""
    tasks = run9.task_sets(cfg)["selection"]
    anchor = run9.anchor_rows(cfg, tasks, cfg["baseline_repeats"])
    loops = {}
    for lp in run9.loops(cfg):
        if lp["arm"] not in SELECTOR:
            continue
        rounds = []
        for r in run9.state(cfg, lp)["rounds"]:
            cands = []
            for c in r["candidates"]:
                recs = run9.graded(cfg, c["harness"], tasks)
                cands.append({"id": c["id"], "truth": stage0.rate(recs, "truth"), "p2": stage0.rate(recs, "p2")})
            rounds.append(cands)
        loops[lp["id"]] = {"arm": lp["arm"], "rounds": rounds}
    return anchor, loops


def mean_on(row: list[float], idx: list[int]) -> float:
    return fmean(row[i] for i in idx)


def replay(loop: dict, anchor: dict, a: list[int], c: list[int], b: list[int]) -> dict:
    sel = SELECTOR[loop["arm"]]
    ac = a + c
    out = {}
    for rule in RULES:
        inc = {"id": "anchor", "truth": anchor["truth"], "p2": anchor["p2"]}
        reported, later = 0.0, 0
        for rnd, cands in enumerate(loop["rounds"], start=1):
            pick_on = ac if rule == "POOLED" else a
            best = max(cands, key=lambda x: mean_on(x[sel], pick_on))   # first of equals, by id order
            judge_on = {"REG": a, "CONFIRM": c, "POOLED": ac}[rule]
            if mean_on(best[sel], judge_on) > mean_on(inc[sel], judge_on):
                inc = best
                reported = mean_on(best[sel], judge_on) - mean_on(anchor[sel], judge_on)
                later += rnd >= 2
        held = mean_on(inc["truth"], b) - mean_on(anchor["truth"], b)
        out[rule] = {"held_out": held, "reported": reported, "inflation": reported - held,
                     "later_replacements": later}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frozen", default="frozen_v9.yaml")
    ap.add_argument("--splits", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261112)
    args = ap.parse_args()
    cfg = load_yaml(resolve(args.frozen))
    anchor, loops = load(cfg)
    n = len(anchor["truth"])
    rng = random.Random(args.seed)
    acc = {lid: {r: {k: [] for k in ("held_out", "reported", "inflation", "later_replacements")} for r in RULES}
           for lid in loops}
    for _ in range(args.splits):
        order = rng.sample(range(n), n)
        a, c, b = order[:N_A], order[N_A:N_A + N_C], order[N_A + N_C:]
        for lid, lp in loops.items():
            for rule, v in replay(lp, anchor, a, c, b).items():
                for k, x in v.items():
                    acc[lid][rule][k].append(x)
    per_loop = {lid: {r: {k: fmean(v) for k, v in d.items()} for r, d in rules.items()} for lid, rules in acc.items()}
    groups = {"jred": ["jred"], "jhonest": ["jhonest"], "truth": ["truth"], "judge_selected": ["jred", "jhonest"]}
    summary = {}
    for g, arms in groups.items():
        ids = [lid for lid, lp in loops.items() if lp["arm"] in arms]
        summary[g] = {r: {k: fmean(per_loop[lid][r][k] for lid in ids) for k in per_loop[ids[0]][r]} for r in RULES}
    result = {"splits": args.splits, "sizes": {"A": N_A, "C": N_C, "B": n - N_A - N_C},
              "summary": summary, "per_loop": per_loop}
    (resolve(cfg["out_dir"]) / "replay.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    for g, rules in summary.items():
        for r, v in rules.items():
            print(f"{g:15s} {r:8s} held-out {v['held_out']*100:+5.2f}  reported {v['reported']*100:+5.2f}  "
                  f"inflation {v['inflation']*100:+5.2f}  later replacements {v['later_replacements']:.2f}")


if __name__ == "__main__":
    main()
