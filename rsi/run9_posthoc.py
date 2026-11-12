"""Run 9, post hoc: why did the red-team loops stop after round 1?

  python -m rsi.run9_posthoc

Not registered. Written after the outcome was known. Reads only files in runs_v9 and writes
runs_v9/posthoc_stall.json. Scores are on the 150 selection tasks, in each arm's own selector
(judge approval for jred and jhonest, accuracy for truth).

For each selected arm it reports:
- bar: the score a candidate had to beat after round 1 (the round 1 winner's single run);
- later_mean: the mean score of all candidates in rounds 2 to 5;
- anchor: the anchor's score on the same selector (mean of its three repeats);
- ties: rounds 2 to 5 in which the best candidate exactly equalled the incumbent;
- repeat_sd: the standard deviation of the anchor's three repeats under that selector,
  a rough noise floor for one harness on 150 tasks.
"""
import json
import statistics as st
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs_v9"
ARMS = {"jred": "p2", "jhonest": "p2", "truth": "truth"}


def loop(arm: str, seed: int) -> dict:
    return json.loads((RUNS / f"loop_{arm}-{seed}.json").read_text(encoding="utf-8"))


def main() -> None:
    base = json.loads((RUNS / "baseline.json").read_text(encoding="utf-8"))["runs"]
    out = {}
    for arm, sel in ARMS.items():
        bars, later, ties, replaced_later = [], [], 0, 0
        paths = {}
        for seed in range(1, 5):
            rounds = loop(arm, seed)["rounds"]
            bars.append(rounds[1]["incumbent_score"])
            path = [r["incumbent_score"] for r in rounds]
            last = rounds[-1]
            best_last = max(c["score"] for c in last["candidates"])
            path.append(best_last if last["replaced"] else last["incumbent_score"])
            paths[f"{arm}-{seed}"] = path
            for r in rounds[1:]:
                scores = [c["score"] for c in r["candidates"]]
                later += scores
                if r["replaced"]:
                    replaced_later += 1
                elif abs(max(scores) - r["incumbent_score"]) < 1e-9:
                    ties += 1
        anchor = [r[sel] for r in base]
        out[arm] = {
            "selector": sel,
            "anchor": st.mean(anchor),
            "repeat_sd": st.stdev(anchor),
            "bar_mean": st.mean(bars),
            "later_mean": st.mean(later),
            "later_minus_bar": st.mean(later) - st.mean(bars),
            "later_minus_anchor": st.mean(later) - st.mean(anchor),
            "later_rounds": 16,
            "later_rounds_replaced": replaced_later,
            "later_rounds_tied": ties,
            "paths": paths,
        }
    (RUNS / "posthoc_stall.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    for arm, v in out.items():
        print(f"{arm:8s} anchor {v['anchor']*100:5.1f}  bar {v['bar_mean']*100:5.1f}  "
              f"later {v['later_mean']*100:5.1f}  later-anchor {v['later_minus_anchor']*100:+5.1f}  "
              f"replaced {v['later_rounds_replaced']}/16  tied {v['later_rounds_tied']}  "
              f"repeat sd {v['repeat_sd']*100:.1f}")


if __name__ == "__main__":
    main()
