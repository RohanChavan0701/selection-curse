"""Run 9: task sets, candidate parsing, prompts, the loop with scripted models, analysis, verdicts."""
import json
import random
from types import SimpleNamespace

import pytest

from rsi import fin_propose, run9, stage0
from rsi.config import ROOT, load_yaml

FROZEN = load_yaml(ROOT / "frozen_v9.yaml")


def test_config_keeps_run7_models_and_separates_the_arms_as_designed():
    v7 = load_yaml(ROOT / "frozen_v7.yaml")
    assert FROZEN["student"] == v7["student"]
    assert {k: v for k, v in FROZEN["judge"].items() if k != "skip_ref"} == v7["judge"]
    arms = FROZEN["arms"]
    assert arms["jred"]["selector"] == arms["jhonest"]["selector"] == "p2"       # differ in goal only
    assert arms["jhonest"]["goal"] == arms["truth"]["goal"] == arms["random"]["goal"] == "correct"
    assert arms["truth"]["selector"] == "truth" and arms["random"]["selector"] is None
    assert len(run9.loops(FROZEN)) == 16 and FROZEN["out_dir"] == "runs_v9"
    assert FROZEN["proposer"]["base_url"] != FROZEN["student"]["base_url"]


def test_task_sets_are_disjoint_and_new():
    if not (ROOT / "data/finqa/train.json").exists():
        pytest.skip("FinQA train file not present")
    sets = run9.task_sets(FROZEN)
    sel, fin = ({t.task_id for t in sets[k]} for k in ("selection", "final"))
    assert (len(sel), len(fin)) == (150, 300) and not sel & fin
    if (ROOT / "data/finqa/dev.json").exists():
        from rsi.domains import finqa
        dev = {t.task_id for t in finqa.load_finqa(ROOT / "data/finqa/dev.json")}
        assert not (sel | fin) & dev


def test_parse_candidates_keeps_only_valid_new_versions():
    h = {**run9.anchor(FROZEN), "rules": "- a"}
    text = json.dumps([
        {"rules": "- a\n- b", "setting": None, "rationale": "r"},
        {"rules": "- a\n- b", "setting": None},                                   # same as the first
        {"rules": "- a", "setting": None},                                        # same as the incumbent
        {"rules": "- a", "setting": {"field": "max_steps", "value": 3}},          # setting alone is a change
        {"rules": "- a", "setting": {"field": "max_steps", "value": 99}},         # bad value: setting ignored
        {"rules": "x" * 1300, "setting": None},                                   # too long
        {"rules": 7}, "nonsense"])
    out = run9.parse_candidates(text, h, 1200)
    assert [c["harness"]["rules"] for c in out] == ["- a\n- b", "- a"]
    assert out[1]["harness"]["max_steps"] == 3 and out[1]["setting"] == {"field": "max_steps", "value": 3}
    assert run9.parse_candidates("not json", h, 1200) == []


def test_prompts_differ_only_as_designed():
    h = run9.anchor(FROZEN)
    loop = {l["arm"]: l for l in run9.loops(FROZEN) if l["seed"] == 1}
    red, honest, truth = (run9.prompt(FROZEN, loop[a], h, "EP", "") for a in ("jred", "jhonest", "truth"))
    assert "Reviewer's instructions" in red and "Approval is the only thing measured" in red
    assert "Reviewer's instructions" not in honest and honest == truth            # same words, other episodes
    assert "already tried" not in red
    again = run9.prompt(FROZEN, loop["truth"], h, "EP", "  round 1 +2.0 (kept)  - x")
    assert "the agent's accuracy" in again and "+2.0 (kept)" in again
    assert "the reviewer's approval rate" in run9.prompt(FROZEN, loop["jhonest"], h, "EP", "h")


def test_verdicts_apply_the_registered_thresholds():
    pred = FROZEN["predictions"]
    out = {"bias": {"jred_minus_truth": {"point": 0.01, "interval95": [-0.03, 0.05]},
                    "jhonest_minus_truth": {"point": 0.03}, "jred_minus_jhonest": {"point": -0.02}},
           "compounding": {"judge_selected": {"inflation": 0.05}},
           "true_gain": {"jhonest_minus_truth": {"point": -0.04}, "truth_minus_random": {"point": 0.02},
                         "mean": {"truth": 0.06}}}
    assert run9.verdicts(out, pred) == {"H1": "holds", "H2": "fails", "H3": "holds", "H4": "holds",
                                        "H5": "fails", "H6": "holds", "H7": "fails"}
    out["bias"]["jred_minus_truth"] = {"point": 0.04, "interval95": [0.01, 0.07]}
    assert run9.verdicts(out, pred)["H1"] == "fails"
    out["bias"]["jred_minus_truth"] = {"point": 0.02, "interval95": [-0.02, 0.07]}
    assert run9.verdicts(out, pred)["H1"] == "inconclusive"


def test_contrasts_find_a_planted_difference():
    rng = random.Random(0)
    rows = lambda n, shift: [[shift + rng.gauss(0, 0.5) for _ in range(300)] for _ in range(n)]
    c = run9.contrasts({"jred": rows(4, 0.08), "jhonest": rows(4, 0.0), "truth": rows(4, 0.0),
                        "random": rows(4, -0.05)}, boots=300, seed=1)
    assert c["jred_minus_truth"]["point"] == pytest.approx(0.08, abs=0.04) and c["jred_minus_truth"]["interval95"][0] > 0
    lo, hi = c["jhonest_minus_truth"]["interval95"]
    assert lo < 0 < hi and c["truth_minus_random"]["point"] > 0


def test_run9_end_to_end_with_scripted_models(tmp_path):
    from rsi.domains import finqa
    from rsi.student import Completion

    raw = [{"id": f"ACME/2020/page_{i}.pdf-1", "pre_text": ["acme reported results ."],
            "table": [["", "2020", "2019"], ["revenue", "120.0", "100.0"]], "post_text": ["in millions ."],
            "qa": {"question": f"what was the percentage change in revenue ({i})?", "exe_ans": 0.2}} for i in range(14)]
    f = tmp_path / "train.json"
    f.write_text(json.dumps(raw), encoding="utf-8")
    cfg = {**FROZEN, "out_dir": str(tmp_path / "out"), "seed": 3, "seeds": [1, 2],
           "data": {"finqa_file": str(f), "n_selection": 6, "n_final": 8},
           "student": {"model": "fake"}, "judge": {"model": "fake", "style": "recompute", "skip_ref": True},
           "proposer": {"max_calls": 2, "num_predict": 3000},
           "loop": {**FROZEN["loop"], "rounds": 2, "candidates": 2},
           "baseline_repeats": 2, "final_baseline_repeats": 2, "final_repeats": 2, "analysis": {"boots": 40}}
    sets = run9.task_sets(cfg)
    assert len(sets["selection"]) == 6 and len(sets["final"]) == 8
    calls = {"s": 0, "j": 0, "p": []}

    def student(messages):                           # right when the rules mention "good", else right 1 in 3
        calls["s"] += 1
        good = "good" in json.dumps(messages)
        return Completion('{"tool": "submit", "arg": "%s"}' % ("20%" if good or calls["s"] % 3 == 0 else "5%"), 1, 1, 0.0)

    def judge(system, user, max_tokens=256):         # approves answers produced under a rule saying "please"
        calls["j"] += 1
        assert "Reference answer" not in user        # the reference judge is skipped
        return SimpleNamespace(text=json.dumps({"correct": "20%" in user.split("Final answer:")[-1], "score": 5}))

    def proposer(system, user, max_tokens=3000):
        calls["p"].append(user)
        n = len(calls["p"])
        return SimpleNamespace(text=json.dumps([
            {"rules": f"- good rule {n}", "setting": None, "rationale": "x"},
            {"rules": f"- plain rule {n}", "setting": {"field": "max_steps", "value": 3}, "rationale": "y"}]))

    with pytest.raises(SystemExit):                  # baseline not graded
        run9.propose(cfg, sets["selection"], proposer, 1)
    base = run9.baseline(cfg, sets["selection"], student, judge, 1)
    assert len(base["runs"]) == 2 and calls["j"] == 2 * 6
    p1 = run9.propose(cfg, sets["selection"], proposer, 1)
    assert p1["empty"] == 0 and len(p1["loops"]) == 8 and len(calls["p"]) == 8
    assert all(v["candidates"] == 2 and len(v["sha256"]) == 64 for v in p1["loops"].values())
    assert run9.propose(cfg, sets["selection"], proposer, 1) == p1 and len(calls["p"]) == 8     # cached
    with pytest.raises(SystemExit):                  # round 2 before round 1 is resolved
        run9.propose(cfg, sets["selection"], proposer, 2)
    b1 = run9.build(cfg, sets["selection"], student, judge, 1, 1)
    assert b1["evaluated"] == 12 and b1["replaced"] >= 2     # 6 scored loops x 2; both random loops replace
    loops = {l["id"]: l for l in run9.loops(cfg)}
    st = run9.state(cfg, loops["truth-1"])["rounds"][0]
    assert st["replaced"] and "good" in st["incumbent_after"]["rules"] and st["incumbent_score"] < 1
    rnd = run9.state(cfg, loops["random-1"])["rounds"][0]
    assert rnd["replaced"] and "score" not in rnd["candidates"][0] and "incumbent_score" not in rnd
    run9.propose(cfg, sets["selection"], proposer, 2)
    truth_prompt = next(p for p in calls["p"][8:] if "the agent's accuracy" in p)
    assert "round 1" in truth_prompt and "(kept)" in truth_prompt and "good rule" in truth_prompt
    assert sum("already tried" in p for p in calls["p"][8:]) == 6           # the random arm has no history
    with pytest.raises(SystemExit):                  # final before the loops are done
        run9.final(cfg, sets["final"], student, judge, 1)
    b2 = run9.build(cfg, sets["selection"], student, judge, 2, 1)
    assert b2["round"] == 2 and run9.build(cfg, sets["selection"], student, judge, 2, 1)["evaluated"] == 0
    assert run9.state(cfg, loops["truth-1"])["rounds"][1]["replaced"] is False       # 1.0 is not beaten
    fin = run9.final(cfg, sets["final"], student, judge, 1)
    assert fin["harnesses"] == 2 + 2 * 8 and fin["rounds_run"] == 2
    out = run9.analyze(cfg, sets)
    assert set(out["loops"]) == set(loops) and out["bias"]["n"] == {a: 2 for a in cfg["arms"]}
    assert out["loops"]["truth-1"]["true_gain"] > 0.3 and out["loops"]["truth-1"]["replaced"] == 1
    assert set(run9.PAIRS) <= set(out["bias"]) and set(out["compounding"]) >= {"jred", "jhonest", "truth"}
    assert "random" not in out["compounding"] and "inflation" in out["compounding"]["judge_selected"]
    assert set(out["verdicts"]) <= {"H1", "H2", "H3", "H4", "H5", "H6", "H7"} and "H2" in out["verdicts"]
    json.dumps(out)


def test_a_round_that_cannot_finish_is_cut_for_every_loop(tmp_path):
    cfg = {**FROZEN, "out_dir": str(tmp_path / "out"), "seeds": [1]}
    h = run9.anchor(cfg)
    for loop in run9.loops(cfg):
        run9._write(cfg, f"prop_{loop['id']}_r1.json",
                    [{"id": f"{loop['id']}/r1/0", "harness": {**h, "rules": "- " + loop["id"]}, "setting": None}])
    run9._write(cfg, "timing.json", {"seconds_per_harness": 1000.0})
    out = run9.build(cfg, [SimpleNamespace(task_id="t")], None, None, 1, 1, deadline=__import__("time").time() + 60)
    assert out["rounds_run"] == 0 and run9.rounds_run(cfg) == 0
    assert run9.build(cfg, [], None, None, 1, 1)["skipped"] == "rounds were cut"
    assert run9.propose(cfg, [], None, 1)["skipped"] == "rounds were cut"
