"""Draw figures/run7_selection.svg from runs_v7/analyze.json. Standard library only.

  python figures/make_run7_figure.py

One pair of bars per selector: the gain the loop reports for its chosen edit (on the tasks it
selected on) and that edit's real gain (true labels, fresh tasks). Greedy best of 8 edits on
150 tasks, 3000 replay rounds.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = [("truth", "True labels", "agrees 100%"), ("p1", "Judge with", "reference (90%)"),
          ("p2", "Recompute judge,", "no reference (74%)"), ("p2v", "Verdict judge,", "no reference (62%)")]
REPORTED, REAL, INK, GRID = "#c9a227", "#2f5d8a", "#1f2933", "#d5dbe1"


def main() -> None:
    point = json.loads((ROOT / "runs_v7" / "analyze.json").read_text(encoding="utf-8"))["point"]
    w, h, left, top, plot_h = 760, 430, 70, 70, 250
    top_val = 7.0
    y = lambda v: top + plot_h * (1 - v / top_val)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="{left}" y="30" font-size="17" font-weight="bold" fill="{INK}">'
           'Run 7: what the loop reports and what is real</text>',
           f'<text x="{left}" y="50" font-size="12.5" fill="{INK}">Best of 8 harness edits chosen on 150 FinQA '
           'tasks, by selector. Gain over baseline in accuracy points.</text>']
    for tick in range(0, 8):
        out.append(f'<line x1="{left}" x2="{w - 30}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" stroke="{GRID}" '
                   f'stroke-width="{1.4 if tick == 0 else 0.7}"/>')
        out.append(f'<text x="{left - 8}" y="{y(tick) + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}">+{tick}</text>')
    group, bar = (w - 30 - left) / len(LABELS), 52
    for i, (key, line1, line2) in enumerate(LABELS):
        rep, real = point[key]["reported"] * 100, point[key]["real"] * 100
        x0 = left + i * group + (group - 2 * bar - 8) / 2
        for j, (val, color) in enumerate(((rep, REPORTED), (real, REAL))):
            x = x0 + j * (bar + 8)
            out.append(f'<rect x="{x:.1f}" y="{y(val):.1f}" width="{bar}" height="{y(0) - y(val):.1f}" fill="{color}"/>')
            out.append(f'<text x="{x + bar / 2:.1f}" y="{y(val) - 6:.1f}" font-size="12" text-anchor="middle" '
                       f'fill="{INK}">+{val:.1f}</text>')
        mid = x0 + bar + 4
        out.append(f'<text x="{mid:.1f}" y="{y(0) + 20:.1f}" font-size="12" text-anchor="middle" fill="{INK}">{line1}</text>')
        out.append(f'<text x="{mid:.1f}" y="{y(0) + 36:.1f}" font-size="12" text-anchor="middle" fill="{INK}">{line2}</text>')
        out.append(f'<text x="{mid:.1f}" y="{y(0) + 56:.1f}" font-size="11.5" text-anchor="middle" fill="{INK}">'
                   f'inflation +{rep - real:.1f}</text>')
    ly = h - 22
    out.append(f'<rect x="{left}" y="{ly - 11}" width="14" height="14" fill="{REPORTED}"/>')
    out.append(f'<text x="{left + 20}" y="{ly}" font-size="12" fill="{INK}">reported (selection tasks, selector\'s score)</text>')
    out.append(f'<rect x="{left + 290}" y="{ly - 11}" width="14" height="14" fill="{REAL}"/>')
    out.append(f'<text x="{left + 310}" y="{ly}" font-size="12" fill="{INK}">real (fresh tasks, true labels)</text>')
    out.append("</svg>")
    (ROOT / "figures" / "run7_selection.svg").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
