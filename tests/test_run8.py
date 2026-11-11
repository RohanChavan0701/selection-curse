"""Run 8: source contrasts, ceiling, preference, config, and the full order with scripted models."""
import json
import random
from types import SimpleNamespace

import pytest

from rsi import fin_propose, run8, stage0
from rsi.config import ROOT, load_yaml


def _rows(n_edits, n_tasks, shift, rng, sd=0.5):
    """Per-task values for `n_edits` edits: noise around a common per-edit mean `shift`."""
    return [[shift + rng.gauss(0, sd) for _ in range(n_tasks)] for _ in range(n_edits)]


def test_contrasts_find_a_planted_bias_and_not_an_absent_one():
    rng = random.Random(0)
    vals = {"s2": _rows(12, 200, 0.0, rng), "s4a": _rows(6, 200, 0.05, rng), "s4b": _rows(6, 200, 0.09, rng)}
    c = run8.contrasts(vals, boots=300, seed=1)
    lo, hi = c["red_minus_control"]["interval95"]
    assert c["n"] == {"s2": 12, "s4a": 6, "s4b": 6}
    assert c["red_minus_control"]["point"] == pytest.approx(0.07, abs=0.03) and lo > 0
    assert c["s4b_minus_s4a"]["point"] == pytest.approx(0.04, abs=0.04)
    null = run8.contrasts({"s2": _rows(12, 200, 0.0, rng), "s4a": _rows(12, 200, 0.0, rng)}, boots=300, seed=1)
    lo, hi = null["red_minus_control"]["interval95"]
    assert lo < 0 < hi and null["s4b_minus_s4a"] is None       # a missing source gives no contrast


def test_ceiling_removes_selection_inflation():
    rng = random.Random(2)
    c = run8.ceiling(_rows(20, 100, 0.0, rng), splits=400, rng=random.Random(3))
    assert c["naive_max"] > 0.05                               # best of 20 noisy means looks biased
    assert abs(c["held_out_bias_of_max"]) < 0.04               # and is not, on tasks it was not picked on
    one = _rows(19, 100, 0.0, rng) + _rows(1, 100, 0.4, rng)
    c = run8.ceiling(one, splits=200, rng=random.Random(3))
    assert c["naive_argmax"] == 19 and c["held_out_bias_of_max"] > 0.25


def test_preference_follows_judge_bias():
    rng = random.Random(4)
    n_tasks, t0 = 120, [0.5] * 120
    t = [[float(rng.random() < 0.5) for _ in range(n_tasks)] for _ in range(20)]
    red = [i >= 10 for i in range(20)]
    fair = run8.preference(t, t, t0, t0, red, k=8, m=60, rounds=600, rng=random.Random(5))
    assert fair["judge_minus_truth"] == 0.0 and 0.2 < fair["truth"] < 0.8
    liked = [[1.0 if red[i] and rng.random() < 0.3 else x for x in row] for i, row in enumerate(t)]
    out = run8.preference(t, liked, t0, t0, red, k=8, m=60, rounds=600, rng=random.Random(5))
    assert out["judge"] > 0.9 and out["judge_minus_truth"] > 0.2


def test_verdicts_apply_the_registered_thresholds():
    pred = load_yaml(ROOT / "frozen_v8.yaml")["predictions"]
    out = {"bias": {"red_minus_control": {"point": 0.005, "interval95": [-0.01, 0.02]},
                    "s4b_minus_s4a": {"point": 0.03}},
           "preference": {"judge_minus_truth": 0.2}, "ceiling": {"red": {"held_out_bias_of_max": 0.01}},
           "new_pool": {"p2": {"multiplier": 1.4, "multiplier_theory": 1.35}}}
    v = run8.verdicts(out, pred)
    assert v == {"H1": "holds", "H2": "fails", "H4": "fails", "H6": "holds", "H7": "holds"}
    out["bias"]["red_minus_control"] = {"point": 0.03, "interval95": [0.01, 0.05]}
    assert run8.verdicts(out, pred)["H1"] == "fails"
    out["bias"]["red_minus_control"] = {"point": 0.015, "interval95": [-0.01, 0.04]}
    assert run8.verdicts(out, pred)["H1"] == "inconclusive"


def test_run8_reuses_run7_setting_and_new_cache_keys():
    v7, v8 = load_yaml(ROOT / "frozen_v7.yaml"), load_yaml(ROOT / "frozen_v8.yaml")
    for key in ("seed", "data", "student", "judge", "judge_verdict"):
        assert v8[key] == v7[key]
    assert not set(v8["session_repeats"]) & set(range(v7["baseline_repeats"]))
    assert v8["check_repeat"] != 0 and v8["out_dir"] != v7["out_dir"]
    assert v8["proposer"]["base_url"] != v8["student"]["base_url"]
    edits = v8["proposer"]["edits"]
    assert edits["s2"] == edits["s4a"] + edits["s4b"] and "s3" not in edits
    jobs = run8.jobs(v8)                                       # no proposals on disk: baselines and checks
    assert [j[0] for j in jobs[:7]] == ["baseline"] * 3 + ["check"] * 4


def test_trace_tasks_are_disjoint_from_every_earlier_sample():
    if not (ROOT / "data/finqa/dev.json").exists():
        pytest.skip("FinQA dev file not present")
    cfg = load_yaml(ROOT / "frozen_v8.yaml")
    ids = lambda f: {t.task_id for t in stage0.sample_tasks(load_yaml(ROOT / f))}
    traces = {t.task_id for t in run8.trace_tasks(cfg)}
    assert len(traces) == 60
    assert ids("frozen_v8.yaml") == ids("frozen_v7.yaml")
    for f in ("frozen_v7.yaml", "frozen_v6_stage0.yaml", "frozen_v6_stage1.yaml"):
        assert not traces & ids(f)


def test_prompts_differ_only_as_designed():
    anchor = {"rules": "", "max_steps": 2}
    s2 = fin_propose.prompt(anchor, "T", "s2", 5, "recompute")
    s4a = fin_propose.prompt(anchor, "T", "s4a", 5, "recompute")
    s4b = fin_propose.prompt(anchor, "T", "s4b", 5, "recompute", feedback="  +3.0  rule: - x")
    assert "Reviewer's instructions" not in s2 and "Reviewer's instructions" in s4a
    assert "Approval is the only thing measured" in s4a and "correct more often" in s2
    assert s4b.startswith(s4a.split("Propose 5")[0]) and "+3.0  rule: - x" in s4b and "Edits already tried" not in s4a


def test_run8_end_to_end_with_scripted_models(tmp_path):
    from rsi.domains import finqa
    from rsi.student import Completion

    RAW = [{"id": "ACME/2020/page_1.pdf-1", "pre_text": ["acme reported results ."],
            "table": [["", "2020", "2019"], ["revenue", "120.0", "100.0"], ["costs", "80.0", "70.0"]],
            "post_text": ["amounts in millions ."],
            "qa": {"question": "what was the percentage change in revenue?", "exe_ans": 0.2}},
           {"id": "ACME/2020/page_1.pdf-2", "pre_text": [], "table": [], "post_text": ["revenue rose ."],
            "qa": {"question": "did revenue rise?", "exe_ans": "yes"}}]
    f = tmp_path / "dev.json"
    f.write_text(json.dumps(RAW), encoding="utf-8")
    tasks = finqa.load_finqa(f) * 4                  # 8 evaluation tasks, ids repeat; enough for plumbing
    traces = finqa.load_finqa(f)                     # the proposer's own tasks
    frozen = load_yaml(ROOT / "frozen_v8.yaml")
    cfg = {"out_dir": str(tmp_path / "out"), "seed": 1, "session_repeats": [3, 4], "check_repeat": 1,
           "check_edits": ["style/confident"], "run7_analysis": str(tmp_path / "none.json"),
           "student": {"model": "fake"}, "judge": {"model": "fake", "style": "recompute", "num_predict": 700},
           "judge_verdict": {"style": "verdict", "num_predict": 256},
           "proposer": {"edits": {"s2": 4, "s4a": 2, "s4b": 2}, "max_calls": 3},
           "analysis": {"k": 4, "m": 4, "rounds": 40, "boots": 30, "splits": 30, "curse_boots": 25,
                        "boot_rounds": 10, "pref_boots": 25, "min_edits_per_group": 12},
           "predictions": frozen["predictions"]}
    calls = {"s": 0, "j": 0, "p": []}

    def student(messages):
        calls["s"] += 1
        return Completion('{"tool": "submit", "arg": "%s"}' % ("20%" if calls["s"] % 3 else "yes"), 1, 1, 0.0)

    def judge(system, user, max_tokens=256):
        calls["j"] += 1
        return SimpleNamespace(text=json.dumps({"correct": calls["j"] % 3 == 0, "score": 5}))

    def proposer(system, user, max_tokens=2000):     # two new rules per call, plus one it already gave
        calls["p"].append(user)
        n = len(calls["p"])
        return SimpleNamespace(text=json.dumps([{"type": "rule", "text": f"Rule {n} {i}."} for i in (0, 1)]
                                               + [{"type": "rule", "text": "Rule 1 0."}]))

    with pytest.raises(SystemExit):                  # no traces graded yet
        run8.propose(cfg, tasks, proposer, 1, traces)
    stage0.evaluate(cfg, run8.anchor(cfg)[1], traces, student, judge, 0, 1)
    r1 = run8.propose(cfg, tasks, proposer, 1, traces)
    assert {s: r["edits"] for s, r in r1.items()} == {"s2": 4, "s4a": 2} and len(r1["s2"]["sha256"]) == 64
    assert len(calls["p"]) == 3 and "Edits already tried" not in calls["p"][-1]
    assert [j[0] for j in run8.jobs(cfg)] == ["baseline"] * 2 + ["check", "s4a", "s4a"] + ["s2"] * 4
    with pytest.raises(SystemExit):                  # round 2 before s4a is graded
        run8.propose(cfg, tasks, proposer, 2, traces)
    first = run8.build(cfg, tasks, student, judge, 1, groups={"baseline", "check", "s4a"})
    assert first["evaluated"] == 5
    r2 = run8.propose(cfg, tasks, proposer, 2, traces)
    assert r2["s4b"]["edits"] == 2 and "Edits already tried" in calls["p"][-1] and "rule: - Rule" in calls["p"][-1]
    ids = {fin_propose.harness_key(e["harness"]): e["id"] for e in run8.proposals(cfg) if e["source"] != "s2"}
    assert len(ids) == 4                             # s4b repeated nothing from s4a
    assert run8.build(cfg, tasks, student, judge, 1)["evaluated"] == 11
    assert run8.build(cfg, tasks, student, judge, 1)["seconds_per_harness"] is None     # all cached
    assert "p2v" not in run8.rows(cfg, tasks)["selectors"]
    before = calls["j"]
    assert run8.regrade(cfg, tasks, judge, 1) == {"graded": 11, "skipped_for_deadline": 0, "not_in_bank": 0,
                                                  "seconds_per_harness": pytest.approx(0, abs=5)}
    assert calls["j"] - before == 11 * len(tasks)
    out = run8.analyze(cfg, tasks)
    assert out["selectors"] == ["truth", "p1", "p2", "p2v"] and out["n_edits"] == {"s2": 4, "s4a": 2, "s4b": 2}
    assert out["underpowered"] and len(out["edits"]) == 8 and out["edits"]["s4b/00"]["text"].startswith("rule: - Rule")
    assert set(out["checks"]) == {"style/confident"} and out["checks"]["style/confident"]["run7"]["truth"] is None
    assert out["bias"]["n"] == {"s2": 4, "s4a": 2, "s4b": 2} and out["red_pool"]["n_edits"] == 4
    assert out["new_pool"]["n_edits"] == 8 and out["preference"]["red_share_of_pool"] == 0.5
    assert out["ceiling"]["red"]["edit"].startswith("s4") and "bias_verdict_judge" in out
    assert set(out["verdicts"]) <= {"H1", "H2", "H3", "H4", "H5", "H6", "H7"} and "H1" in out["verdicts"]
    json.dumps(out)                                  # serialisable
