"""Write figures/architecture.excalidraw, the repository's architecture as an Excalidraw scene.
Standard library only.

  python figures/make_architecture.py

Open the file at excalidraw.com (or the VS Code Excalidraw extension) to view or edit it.
figures/architecture.svg is an export of the same scene.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = random.Random(20261112)
ELS: list[dict] = []
FONT = 1            # Virgil, the classic hand-drawn font
CHAR_W = 0.56       # rough glyph width as a share of font size, for centering


def _base(kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
    el = {"id": f"{kind[:2]}{len(ELS)}", "type": kind, "x": x, "y": y, "width": w, "height": h,
          "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
          "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
          "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
          "seed": R.randrange(1, 2**31), "version": 1, "versionNonce": R.randrange(1, 2**31),
          "isDeleted": False, "boundElements": [], "updated": 1, "link": None, "locked": False}
    el.update(kw)
    ELS.append(el)
    return el


def text(x: float, y: float, s: str, size: int = 18, color: str = "#1e1e1e", align: str = "left",
         container: dict | None = None, width: float | None = None) -> dict:
    lines = s.split("\n")
    if len(lines) > 1:   # one element per line: renders the same in every Excalidraw version
        first = None
        for i, line in enumerate(lines):
            el = text(x, y + i * size * 1.25, line or " ", size, color, align, container, width)
            first = first or el
        return first
    w = max(len(l) for l in lines) * size * CHAR_W
    h = len(lines) * size * 1.25
    if align == "center" and width is not None:
        x = x + (width - w) / 2
    el = _base("text", x, y, w, h, strokeColor=color, text=s, originalText=s, fontSize=size,
               fontFamily=FONT, textAlign=align, verticalAlign="top", lineHeight=1.25,
               baseline=round(size * 0.92), containerId=container["id"] if container else None, autoResize=True)
    if container:
        container["boundElements"].append({"type": "text", "id": el["id"]})
    return el


def box(x, y, w, h, title, body="", stroke="#1e1e1e", fill="transparent", style="solid",
        title_size=20, body_size=15, dashed=False) -> dict:
    r = _base("rectangle", x, y, w, h, strokeColor=stroke, backgroundColor=fill, fillStyle=style,
              roundness={"type": 3}, strokeStyle="dashed" if dashed else "solid")
    text(x + 16, y + 12, title, title_size, stroke)
    if body:
        text(x + 16, y + 16 + title_size * 1.3, body, body_size, "#343a40")
    return r


def arrow(x1, y1, x2, y2, label="", color="#495057", dashed=False, start=None, end=None,
          label_dx=8, label_dy=-22, size=14, both=False) -> dict:
    a = _base("arrow", x1, y1, abs(x2 - x1), abs(y2 - y1), strokeColor=color,
              points=[[0, 0], [x2 - x1, y2 - y1]], lastCommittedPoint=None,
              startBinding={"elementId": start["id"], "focus": 0, "gap": 6} if start else None,
              endBinding={"elementId": end["id"], "focus": 0, "gap": 6} if end else None,
              startArrowhead="arrow" if both else None, endArrowhead="arrow",
              roundness={"type": 2}, strokeStyle="dashed" if dashed else "solid", elbowed=False)
    for b in (start, end):
        if b:
            b["boundElements"].append({"type": "arrow", "id": a["id"]})
    if label:
        text((x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy, label, size, color)
    return a


def zone(x, y, w, h, label, color) -> dict:
    z = _base("rectangle", x, y, w, h, strokeColor=color, backgroundColor="transparent",
              roundness={"type": 3}, strokeStyle="dashed", strokeWidth=1, roughness=0)
    if label:
        text(x + 14, y - 30, label, 22, color)
    return z


def build() -> dict:
    # title
    text(40, 24, "selection-curse  /  architecture", 40)
    text(42, 78, "How much of a self-improvement loop's reported gain is real, and can it learn to game its judge?",
         19, "#495057")

    # 1. inputs
    zone(40, 160, 1180, 130, "1  frozen before every run", "#1971c2")
    blue, bluef = "#1971c2", "#e7f5ff"
    data = box(820, 180, 380, 92, "FinQA tasks", "dev 883  /  train 6,251, SHA-256 pinned\nselection and final sets disjoint",
               blue, bluef)
    cfg = box(440, 180, 360, 92, "frozen_v*.yaml", "models, seeds, sampling, task counts,\nthe thresholds verdicts are computed from",
              blue, bluef)
    pred = box(60, 180, 360, 92, "PREDICTION_run*.md", "hypotheses committed before any data;\ndeviations logged after",
               blue, bluef)

    # findings sticky
    st = _base("rectangle", 1280, 150, 580, 180, strokeColor="#f08c00", backgroundColor="#ffec99",
               fillStyle="solid", roundness={"type": 3}, angle=0.015)
    text(1300, 166, "what it found", 22, "#e67700")
    text(1300, 202, "- the loop reports ~2x its real gain, even with true labels\n"
                    "- judge noise multiplies the curse: 1.36x, formula said 1.37x\n"
                    "- red team vs judge: run 8  -0.5 pts,  run 9  +2.3 (inconclusive)\n"
                    "- a noisy judge can freeze a loop on a lucky first winner\n"
                    "- 3 pre-registered primaries: inconclusive, held, inconclusive",
         16, "#5c3d00")

    # 2. the loop
    zone(40, 360, 1180, 470, "", "#6741d9")
    text(660, 330, "2  the loop (one round)", 22, "#6741d9")
    edits = box(60, 390, 320, 200, "edit sources",
                "hand catalog: 40 edits\n  (fin_edits.py, runs 6 to 7)\n\n32B proposer, qwen2.5:32b\n  (fin_propose.py, run9.py)\n  arms: red team / honest /\n        truth-picked / random",
                "#f08c00", "#fff4e6")
    harness = box(440, 390, 320, 200, "harness",
                  "system prompt + tool guide\nrules block (<= 1,200 chars)\ntable format: rows | markdown\nmax_steps, verify_before_submit\n\none edit = new rules + <= 1 setting",
                  "#6741d9", "#f3f0ff")
    student = box(820, 390, 380, 150, "student agent",
                  "qwen2.5:7b-instruct via Ollama\ntools: calc(arithmetic) -> submit(answer)\n(domains/finqa.py, student.py)",
                  "#2f9e44", "#ebfbee")
    graders = box(820, 570, 380, 240, "graders",
                  "truth: programmatic answer match\n\nLLM judges, llama3.1:8b (proxies.py)\n  p1  sees the reference answer\n  p2  no reference, recomputes   <- selector\n  p3  verdict only (approves 88%)",
                  "#e03131", "#fff5f5")
    cache = box(440, 640, 320, 170, "episode + grade cache",
                "ep_*.json, gr_*.json\nkeyed by hash of harness, tasks,\nrepeat, student, judge\n(bank.py, stage0.py)",
                "#495057", "#f8f9fa")
    select = box(60, 640, 320, 170, "selector",
                 "best of k on selection tasks\nscored by truth OR judge\ntie keeps the incumbent\n(replay.py offline, run9.py live)",
                 "#e67700", "#fff9db")
    arrow(386, 490, 434, 490, start=edits, end=harness)
    arrow(766, 465, 814, 465, start=harness, end=student)
    arrow(1010, 546, 1010, 564, start=student, end=graders)
    arrow(814, 725, 766, 725, start=graders, end=cache)
    arrow(434, 725, 386, 725, start=cache, end=select)
    arrow(220, 634, 220, 596, "incumbent + history (run 9)", "#e67700", start=select, end=edits,
          label_dx=12, label_dy=-10)

    # inputs into the loop
    arrow(1010, 278, 1010, 384, "", blue, start=data, end=student)
    arrow(620, 278, 620, 384, "", blue, start=cfg, end=harness)

    # 3. measurement
    teal, tealf = "#0c8599", "#e6fcf5"
    zone(1260, 420, 620, 410, "3  measurement", teal)
    m1 = box(1280, 440, 580, 70, "re-score the winner on tasks it was not picked on",
             "", teal, tealf, title_size=18)
    m2 = box(1280, 524, 580, 84, "Goodhart split (goodhart.py)",
             "reported = real gain + winner's curse + judge bias", teal, tealf, title_size=18)
    m3 = box(1280, 622, 580, 84, "curse multiplier  ~  sqrt( r_pp / r_tt )",
             "judge's residual variance over truth's: predicts 1.37, saw 1.36", teal, tealf, title_size=18)
    m4 = box(1280, 720, 580, 92, "bootstrap CIs -> verdicts vs frozen thresholds",
             "run7.py, run8.py, run9.py; then post hoc and offline replays\n(run9_posthoc.py, replay9.py), always labelled",
             teal, tealf, title_size=18)
    arrow(1206, 690, 1274, 480, "", teal, start=graders, end=m1)
    for a_, b_ in ((m1, m2), (m2, m3), (m3, m4)):
        arrow(1570, a_["y"] + a_["height"] + 2, 1570, b_["y"] - 2, start=a_, end=b_)

    # 4. compute
    gray, grayf = "#343a40", "#f1f3f5"
    zone(40, 900, 1180, 260, "4  compute (one GPU at a time, author-approved, capped)", gray)
    laptop = box(60, 930, 400, 210, "laptop",
                 "cloud/lambda_api.py\n  launch, cap, status, terminate\n  refuses ids it did not launch\ncloud/ledger.jsonl  (every launch,\n  check, terminate, committed)\ncloud/wait_job.sh  (SSH retry)",
                 gray, grayf)
    gpu = box(560, 930, 640, 210, "GPU instance  (A10 / H100 / A100, tmux)",
              "Ollama :11435  student + judge, 8 request slots\nOllama :11436  32B proposer, loaded once per round\ncloud/run9_remote.sh: baseline -> (propose -> build) x5 -> final\ncloud/watchdog.sh: self-terminate at the $ cap, even if the\n  laptop sleeps.  API key only in env / mode-600 header",
              gray, grayf)
    arrow(466, 990, 554, 990, "launch", gray, start=laptop, end=gpu, label_dx=-26, label_dy=-26)
    arrow(554, 1080, 466, 1080, "scp runs_v*/", gray, start=gpu, end=laptop, label_dx=-40, label_dy=18)
    arrow(880, 924, 880, 836, "runs the loop", gray, dashed=True, start=gpu, label_dx=12, label_dy=-10)

    # 5. outputs
    zone(1260, 900, 620, 260, "5  outputs (public repo)", blue)
    out = box(1280, 930, 580, 210, "what gets committed",
              "runs_v*/  summaries, proposals, logs\n  (per-task caches stay local)\nREADME tables + figures/*.svg\nPREDICTION_run*.md  Outcome sections\ndocs/BLOG_DRAFT.md",
              blue, bluef)
    arrow(1570, 818, 1570, 924, "", teal, start=m4, end=out)

    # footer
    text(40, 1186, "7B student, 8B judge, 32B proposer, FinQA (public; may be in pretraining).  "
                   "Runs 1 to 5: text-to-SQL loop on Spider/BIRD (harness/, scripts/).", 15, "#868e96")

    return {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": ELS,
            "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}, "files": {}}


if __name__ == "__main__":
    scene = build()
    (ROOT / "figures" / "architecture.excalidraw").write_text(json.dumps(scene, indent=1), encoding="utf-8",
                                                             newline="\n")
    print(len(scene["elements"]), "elements")
