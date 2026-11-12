"""Draw figures/run9_loops.svg from runs_v9/analyze.json and runs_v9/posthoc_stall.json.
Standard library only.

  python -m rsi.run9_posthoc
  python figures/make_run9_figure.py

Left panel: each loop's final harness on the 300 fresh tasks, true gain and judge bias,
by arm. Right panel: the score each selected loop had to beat, round by round, on the 150
selection tasks, in its own selector's units, against the mean score of the candidates it
was offered in rounds 2 to 5 (post hoc).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARMS = [("jred", "Red team", "#b5651d"), ("jhonest", "Honest, judge-picked", "#c9a227"),
        ("truth", "Truth-picked", "#2f5d8a"), ("random", "Random", "#7b8794")]
INK, GRID = "#1f2933", "#d5dbe1"


def main() -> None:
    a = json.loads((ROOT / "runs_v9" / "analyze.json").read_text(encoding="utf-8"))
    p = json.loads((ROOT / "runs_v9" / "posthoc_stall.json").read_text(encoding="utf-8"))
    w, h = 980, 470
    top, plot_h = 80, 280
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="40" y="30" font-size="17" font-weight="bold" fill="{INK}">'
           'Run 9: five rounds against the judge, and the red team stopped after one</text>',
           f'<text x="40" y="50" font-size="12.5" fill="{INK}">4 loops per arm. Accuracy points. '
           'FinQA, 7B student, 8B judge, 32B proposer.</text>']

    # left panel: true gain and bias per loop on fresh tasks
    left, pw = 70, 400
    lo, hi = -9.0, 9.0
    y = lambda v: top + plot_h * (1 - (v - lo) / (hi - lo))
    out.append(f'<text x="{left}" y="{top - 12}" font-size="13" font-weight="bold" fill="{INK}">'
               'Final harnesses, 300 fresh tasks</text>')
    for t in range(-8, 9, 2):
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" '
                   f'stroke-width="{1.4 if t == 0 else 0.7}"/>')
        out.append(f'<text x="{left - 8}" y="{y(t) + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}">{t:+d}</text>')
    gw = pw / len(ARMS)
    for i, (arm, name, color) in enumerate(ARMS):
        mid = left + (i + 0.5) * gw
        loops = [v for v in a["loops"].values() if v["arm"] == arm]
        for k, metric, shape in ((0, "true_gain", "circle"), (1, "bias", "square")):
            xs = mid + (-14 if k == 0 else 14)
            for j, v in enumerate(sorted(l[metric] * 100 for l in loops)):
                x = xs + (j - 1.5) * 5
                if shape == "circle":
                    out.append(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="4.5" fill="{color}" fill-opacity="0.85"/>')
                else:
                    out.append(f'<rect x="{x - 4:.1f}" y="{y(v) - 4:.1f}" width="8" height="8" fill="none" '
                               f'stroke="{color}" stroke-width="1.8"/>')
            m = (a["true_gain"] if metric == "true_gain" else a["bias"])["mean"][arm] * 100
            out.append(f'<line x1="{xs - 14:.1f}" x2="{xs + 14:.1f}" y1="{y(m):.1f}" y2="{y(m):.1f}" '
                       f'stroke="{INK}" stroke-width="2"/>')
        out.append(f'<text x="{mid:.1f}" y="{y(lo) + 18:.1f}" font-size="11.5" text-anchor="middle" fill="{INK}">{name}</text>')
    out.append(f'<circle cx="{left + 6}" cy="{y(lo) + 40:.1f}" r="4.5" fill="{INK}"/>'
               f'<text x="{left + 16}" y="{y(lo) + 44:.1f}" font-size="11.5" fill="{INK}">true gain</text>'
               f'<rect x="{left + 92}" y="{y(lo) + 36:.1f}" width="8" height="8" fill="none" stroke="{INK}" stroke-width="1.8"/>'
               f'<text x="{left + 106}" y="{y(lo) + 44:.1f}" font-size="11.5" fill="{INK}">judge bias (judge gain minus true gain)</text>')

    # right panel: selection-task bar by round
    left2, pw2 = 560, 380
    lo2, hi2 = 50.0, 64.0
    y2 = lambda v: top + plot_h * (1 - (v - lo2) / (hi2 - lo2))
    x2 = lambda r: left2 + pw2 * r / 5
    out.append(f'<text x="{left2}" y="{top - 12}" font-size="13" font-weight="bold" fill="{INK}">'
               'Score to beat, 150 selection tasks</text>')
    for t in range(50, 65, 2):
        out.append(f'<line x1="{left2}" x2="{left2 + pw2}" y1="{y2(t):.1f}" y2="{y2(t):.1f}" stroke="{GRID}" stroke-width="0.7"/>')
        out.append(f'<text x="{left2 - 8}" y="{y2(t) + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}">{t}%</text>')
    for r in range(6):
        lab = "start" if r == 0 else f"after {r}"
        out.append(f'<text x="{x2(r):.1f}" y="{y2(lo2) + 18:.1f}" font-size="11" text-anchor="middle" fill="{INK}">{lab}</text>')
    for arm, name, color in ARMS[:3]:
        v = p[arm]
        for path in v["paths"].values():
            pts = " ".join(f"{x2(r):.1f},{y2(s * 100):.1f}" for r, s in enumerate(path))
            out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8" stroke-opacity="0.75"/>')
        lm = v["later_mean"] * 100
        out.append(f'<line x1="{x2(1):.1f}" x2="{x2(5):.1f}" y1="{y2(lm):.1f}" y2="{y2(lm):.1f}" stroke="{color}" '
                   f'stroke-width="2" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{left2}" y="{y2(lo2) + 44:.1f}" font-size="11.5" fill="{INK}">Colors as on the left. Solid: incumbent score. '
               'Dashed: mean candidate, rounds 2 to 5.</text>')
    out.append(f'<text x="{left2}" y="{y2(lo2) + 60:.1f}" font-size="11.5" fill="{INK}">Judge-picked arms in approval, '
               'truth-picked in accuracy.</text>')

    c = a["bias"]["jred_minus_truth"]
    out.append(f'<text x="40" y="{h - 14}" font-size="12" fill="{INK}">Primary, red team minus truth-picked bias: '
               f'{c["point"] * 100:+.1f} points, 95% interval {c["interval95"][0] * 100:+.1f} to '
               f'{c["interval95"][1] * 100:+.1f} (inconclusive). Right panel is post hoc.</text>')
    out.append("</svg>")
    (ROOT / "figures" / "run9_loops.svg").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
