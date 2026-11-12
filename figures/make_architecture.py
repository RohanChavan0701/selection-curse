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
    ink, soft = "#1e1e1e", "#495057"
    text(40, 24, "selection-curse: how it works", 40)
    text(42, 80, "Does a self-improving AI loop really get better, or does it fool itself?", 21, soft)

    # 1. lock the plan
    blue, bluef = "#1971c2", "#e7f5ff"
    plan = box(40, 230, 250, 150, "1  Lock the plan", "Write down what we\nexpect before any run.\nReport it either way.",
               blue, bluef, title_size=22, body_size=17)

    # 2. the loop
    zone(340, 170, 900, 440, "2  The self-improvement loop", "#6741d9")
    propose = box(370, 200, 380, 160, "Propose a change",
                  "An AI rewrites the agent's\ninstructions. Some are told\nto be correct, some to\nimpress the grader.",
                  "#f08c00", "#fff4e6", title_size=22, body_size=17)
    agent = box(830, 200, 380, 160, "Agent does the task",
                "A small AI model answers\nquestions about company\nfinancial reports.",
                "#2f9e44", "#ebfbee", title_size=22, body_size=17)
    grade = box(830, 420, 380, 160, "Grade the answers",
                "Either the true answer key,\nor another AI acting as\njudge (no answer key).",
                "#e03131", "#fff5f5", title_size=22, body_size=17)
    keep = box(370, 420, 380, 160, "Keep the best change",
               "Highest score wins.\nThen go round again,\nbuilding on the winner.",
               "#e67700", "#fff9db", title_size=22, body_size=17)
    arrow(756, 280, 824, 280, start=propose, end=agent)
    arrow(1020, 366, 1020, 414, start=agent, end=grade)
    arrow(824, 500, 756, 500, start=grade, end=keep)
    arrow(560, 414, 560, 366, start=keep, end=propose)
    arrow(296, 305, 364, 290, start=plan, end=propose)

    # 3 to 5. the check
    teal, tealf = "#0c8599", "#e6fcf5"
    check = box(1310, 200, 340, 120, "3  Test the winner again",
                "on new questions it\nnever saw before", teal, tealf, title_size=22, body_size=17)
    compare = box(1310, 360, 340, 120, "4  Compare",
                  "what the loop claimed\nvs what is actually real", teal, tealf, title_size=22, body_size=17)
    publish = box(1310, 520, 340, 120, "5  Publish everything",
                  "including the results\nthat did not work out", blue, bluef, title_size=22, body_size=17)
    arrow(1216, 470, 1304, 280, "", teal, start=grade, end=check)
    arrow(1480, 326, 1480, 354, start=check, end=compare)
    arrow(1480, 486, 1480, 514, start=compare, end=publish)

    # findings
    _base("rectangle", 40, 680, 1200, 195, strokeColor="#f08c00", backgroundColor="#ffec99",
          fillStyle="solid", roundness={"type": 3}, angle=-0.008)
    text(66, 700, "What we found", 26, "#e67700")
    text(66, 746, "- The loop over-claims. Even with a perfect answer key, its reported\n"
                  "  improvement is about double the real one. Pure luck of picking the best.\n"
                  "- An AI judge makes that a little worse, by a predictable amount.\n"
                  "- An AI told to fool the judge did not manage it in our tests.\n"
                  "- A noisy judge can get the loop stuck on a lucky early winner.",
         19, "#5c3d00")

    # compute, small
    gray, grayf = "#495057", "#f1f3f5"
    box(1310, 680, 340, 195, "Where it runs",
        "One rented GPU at a time.\nShuts itself down at a\nfixed budget, even if\nthe laptop sleeps.",
        gray, grayf, title_size=22, body_size=17)

    return {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": ELS,
            "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}, "files": {}}


if __name__ == "__main__":
    scene = build()
    (ROOT / "figures" / "architecture.excalidraw").write_text(json.dumps(scene, indent=1), encoding="utf-8",
                                                             newline="\n")
    print(len(scene["elements"]), "elements")
