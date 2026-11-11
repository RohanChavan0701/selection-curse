"""Draw figures/run8_red_team.svg from runs_v8/analyze.json. Standard library only.

  python figures/make_run8_figure.py

One dot per proposed edit: its judge bias (recompute-judge gain minus true gain, all 300
tasks, against the session baselines), grouped by what the proposer was told. The bar is the
group mean. A single edit's bias has a standard error of about 2 points.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = [("s2", "Control", "told: be correct", "#2f5d8a"),
          ("s4a", "Red team, blind", "told: raise approval", "#c9a227"),
          ("s4b", "Red team, with feedback", "told: raise approval", "#b5651d")]
INK, GRID = "#1f2933", "#d5dbe1"


def main() -> None:
    a = json.loads((ROOT / "runs_v8" / "analyze.json").read_text(encoding="utf-8"))
    w, h, left, top, plot_h = 760, 430, 70, 70, 270
    lo, hi = -3.0, 7.0
    y = lambda v: top + plot_h * (1 - (v - lo) / (hi - lo))
    c = a["bias"]["red_minus_control"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="{left}" y="30" font-size="17" font-weight="bold" fill="{INK}">'
           'Run 8: edits written to please the judge carry no more judge bias</text>',
           f'<text x="{left}" y="50" font-size="12.5" fill="{INK}">Judge bias per edit: judge gain minus true gain, '
           'accuracy points, 300 FinQA tasks. Bar: group mean.</text>']
    for tick in range(int(lo), int(hi) + 1):
        out.append(f'<line x1="{left}" x2="{w - 30}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" stroke="{GRID}" '
                   f'stroke-width="{1.4 if tick == 0 else 0.7}"/>')
        out.append(f'<text x="{left - 8}" y="{y(tick) + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}">{tick:+d}</text>')
    group = (w - 30 - left) / len(GROUPS)
    for i, (key, line1, line2, color) in enumerate(GROUPS):
        vals = sorted(e["bias"] * 100 for k, e in a["edits"].items() if k.split("/")[0] == key)
        mid, mean = left + (i + 0.5) * group, a["bias"]["mean"][key] * 100
        for j, v in enumerate(vals):
            x = mid + (j - (len(vals) - 1) / 2) * (150 / max(len(vals), 1))
            out.append(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="5" fill="{color}" fill-opacity="0.8"/>')
        out.append(f'<line x1="{mid - 90:.1f}" x2="{mid + 90:.1f}" y1="{y(mean):.1f}" y2="{y(mean):.1f}" '
                   f'stroke="{INK}" stroke-width="2.2"/>')
        out.append(f'<text x="{mid + 96:.1f}" y="{y(mean) + 4:.1f}" font-size="12" fill="{INK}">{mean:+.1f}</text>')
        out.append(f'<text x="{mid:.1f}" y="{y(lo) + 20:.1f}" font-size="12" text-anchor="middle" fill="{INK}">'
                   f'{line1} ({len(vals)} edits)</text>')
        out.append(f'<text x="{mid:.1f}" y="{y(lo) + 36:.1f}" font-size="12" text-anchor="middle" fill="{INK}">{line2}</text>')
    out.append(f'<text x="{left}" y="{h - 30}" font-size="12" fill="{INK}">Red team minus control: '
               f'{c["point"] * 100:+.1f} points, 95% interval {c["interval95"][0] * 100:+.1f} to '
               f'{c["interval95"][1] * 100:+.1f}.</text>')
    out.append(f'<text x="{left}" y="{h - 14}" font-size="12" fill="{INK}">Three blind red-team edits are the same '
               'edit as three control edits and share their grades.</text>')
    out.append("</svg>")
    (ROOT / "figures" / "run8_red_team.svg").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
