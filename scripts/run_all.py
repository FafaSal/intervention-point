"""End-to-end pipeline: workspace -> dataset -> training -> evaluation -> figures.

    python scripts/run_all.py            # from the repository root
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intervention import gate, policies as P, scenarios as S  # noqa: E402
from intervention.labels import ACT, APPROVE, CLARIFY, ESCALATE, LABELS  # noqa: E402
from intervention.llm_baseline import load_cache  # noqa: E402
from intervention.metrics import calibration, compute, confusion, family_bootstrap  # noqa: E402
from intervention.simulate import run_episode  # noqa: E402
from intervention.workspace import export_workspace  # noqa: E402

DATA, RES = ROOT / "data", ROOT / "results"
SPLITS = {"template": "Unseen task types (leave-templates-out, 5 folds)",
          "family_id": "Unseen scenario families (leave-families-out, 5 folds)"}
POLICY_NAMES = {
    "autonomous": "A: Autonomous", "heuristic": "Keyword heuristic", "llm_self_assess": "B: LLM self-assessment",
    "constraints_only": "Hard constraints only", "model_only": "Learned model only", "gate_text_only": "Gate (text-only model)",
    "gate": "C: Trained gate", "always_ask": "Always ask",
}


def write_dataset(rows):
    S.save(rows, DATA / "scenarios.jsonl")
    flat = ["scenario_id", "family_id", "template", "category", "variation", "varied_factor", "request", "context",
            "proposed_action_text", "policy_verdict", "missing_information", "conflict", "discretionary", "severity",
            "reversible", "ground_truth_action", "label_rule", "label_contested", "potential_consequence"]
    with (DATA / "scenarios.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flat); w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in flat})
    # Blinded annotation sheet: no labels, rubric facts or policy verdicts; shuffled order.
    ann = DATA / "annotation"; ann.mkdir(exist_ok=True)
    order = rows[:]; random.Random(11).shuffle(order)
    with (ann / "annotation_sheet_blinded.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "scenario_id", "request", "standing_context", "proposed_action", "decision (ACT/CLARIFY/REQUEST_APPROVAL/ESCALATE)",
                    "confidence (1-5)", "notes"])
        for i, r in enumerate(order, 1):
            w.writerow([i, r["scenario_id"], r["request"], r["context"], r["proposed_action_text"], "", "", ""])


def decisions_for(rows, proba_full, proba_text, llm_cache):
    pred_full = [LABELS[i] for i in proba_full.argmax(1)]
    pred_text = [LABELS[i] for i in proba_text.argmax(1)]
    d = {
        "autonomous": [P.autonomous(r) for r in rows],
        "heuristic": [P.heuristic(r) for r in rows],
        "constraints_only": [P.constraints_only(r) for r in rows],
        "model_only": pred_full,
        "gate_text_only": [P.combine(l, r) for l, r in zip(pred_text, rows)],
        "gate": [P.combine(l, r) for l, r in zip(pred_full, rows)],
        "always_ask": [P.always_ask(r) for r in rows],
    }
    if llm_cache and all(r["scenario_id"] in llm_cache for r in rows):
        d["llm_self_assess"] = [llm_cache[r["scenario_id"]]["decision"] for r in rows]
    return d


def sweep(rows, proba, constrained):
    out = []
    for t in np.round(np.linspace(0, 1, 51), 3):
        dec = [P.decide_with_threshold(p, r, t, constrained) for p, r in zip(proba, rows)]
        eps = [run_episode(r, x) for r, x in zip(rows, dec)]
        m = compute(rows, dec, eps)
        out.append({"threshold": float(t), "autonomy": float(np.mean([x == ACT for x in dec])),
                    "severity_weighted_error": m["severity_weighted_error"], "violation_rate": m["violation_rate"],
                    "interactions_per_task": m["interactions_per_task"]})
    return out


def pick_failures(rows, dec, eps, proba):
    """One real case of each failure type from the held-out predictions."""
    def find(cond, key=lambda i: 0):
        idx = [i for i in range(len(rows)) if cond(i)]
        return sorted(idx, key=key)[0] if idx else None
    cases = []
    clean = lambda i: not rows[i]["label_contested"]
    i = find(lambda i: eps["gate"][i]["unnecessary_interruption"] and clean(i), key=lambda i: -proba[i].max())
    if i is not None:
        cases.append(("unnecessary_interruption", "gate", i))
    i = find(lambda i: rows[i]["ground_truth_action"] == CLARIFY and dec["gate"][i] == ACT and clean(i), key=lambda i: -proba[i][0])
    if i is not None:
        cases.append(("missed_ambiguity", "gate", i))
    i = find(lambda i: eps["heuristic"][i]["violation"] and rows[i]["ground_truth_action"] == ESCALATE, key=lambda i: -rows[i]["severity"])
    if i is not None:
        cases.append(("attempted_unauthorized_action", "heuristic", i))
    return cases


def main():
    export_workspace(DATA / "workspace")
    rows = S.build()
    write_dataset(rows)
    RES.mkdir(exist_ok=True)
    llm_cache = load_cache(RES / "llm_predictions.jsonl")

    results = {"n_scenarios": len(rows), "n_families": len({r["family_id"] for r in rows}),
               "n_templates": len({r["template"] for r in rows}), "label_counts": {l: sum(r["ground_truth_action"] == l for r in rows) for l in LABELS},
               "policy_names": POLICY_NAMES, "llm_baseline": "complete" if llm_cache else "pending (requires API key; see llm_baseline.py)",
               "splits": {}}
    per_scenario = {}
    for split, desc in SPLITS.items():
        print(f"== {desc}")
        oof = {spec: gate.out_of_fold(rows, spec, group_key=split)[0] for spec in gate.MODEL_SPECS}
        dec = decisions_for(rows, oof["logreg_full"], oof["logreg_text_only"], llm_cache)
        eps = {pol: [run_episode(r, x) for r, x in zip(rows, d)] for pol, d in dec.items()}
        mets = {pol: compute(rows, dec[pol], eps[pol]) for pol in dec}
        pairs = [("gate", "heuristic"), ("gate", "constraints_only"), ("gate", "model_only"), ("gate", "gate_text_only")]
        if "llm_self_assess" in dec:
            pairs.append(("gate", "llm_self_assess"))
        ci, diff = family_bootstrap(rows, dec, eps, n_boot=1000, seed=0, pairs=pairs)
        y = np.array([r["ground_truth_action"] for r in rows])
        p_need = 1 - oof["logreg_full"][:, 0]
        rel, ece, brier = calibration(p_need, (y != ACT).astype(float))
        model_acc = {spec: float((np.array([LABELS[i] for i in pr.argmax(1)]) == y).mean()) for spec, pr in oof.items()}
        by_group = {}
        for key in ["category", "severity"]:
            by_group[key] = {}
            for g in sorted({r[key] for r in rows}):
                idx = np.array([i for i, r in enumerate(rows) if r[key] == g])
                by_group[key][str(g)] = {pol: compute(rows, dec[pol], eps[pol], idx) for pol in dec}
        outcomes = {pol: {o: int(sum(e["outcome"] == o for e in eps[pol])) for o in sorted({e["outcome"] for e in eps[pol]})} for pol in dec}
        flows = {}
        for e in eps["gate"]:
            k = (e["decision"], e["outcome"]); flows[k] = flows.get(k, 0) + 1
        results["splits"][split] = {
            "description": desc, "metrics": mets, "ci95": ci, "paired_diff_ci95": diff, "model_accuracy": model_acc,
            "confusion_gate": confusion(y, dec["gate"]).tolist(), "confusion_model_only": confusion(y, dec["model_only"]).tolist(),
            "confusion_heuristic": confusion(y, dec["heuristic"]).tolist(),
            "calibration": {"bins": rel, "ece": ece, "brier": brier},
            "sweep_gate": sweep(rows, oof["logreg_full"], True), "sweep_model_only": sweep(rows, oof["logreg_full"], False),
            "by_group": by_group, "outcomes": outcomes,
            "gate_flows": [{"decision": a, "outcome": b, "n": n} for (a, b), n in sorted(flows.items())],
            "failure_cases": [{"type": t, "policy": pol, "scenario_id": rows[i]["scenario_id"]} for t, pol, i in pick_failures(rows, dec, eps, oof["logreg_full"])],
        }
        per_scenario[split] = {"proba": oof["logreg_full"].tolist(), "decisions": dec,
                               "outcomes": {pol: [e["outcome"] for e in v] for pol, v in eps.items()},
                               "interactions": {pol: [e["interactions"] for e in v] for pol, v in eps.items()}}
        print({pol: round(m["severity_weighted_error"], 3) for pol, m in mets.items()}, model_acc)

    final = gate.fit(rows, "logreg_full")
    joblib.dump(final, RES / "intervention_gate.joblib")
    results["top_features"] = gate.top_coefficients(final, k=10)
    from intervention.webdata import clean
    (RES / "metrics.json").write_text(json.dumps(clean(results), indent=2, allow_nan=False))

    with (RES / "predictions.csv").open("w", newline="") as f:
        pols = list(per_scenario["template"]["decisions"].keys())
        w = csv.writer(f)
        w.writerow(["split", "scenario_id", "ground_truth_action"] + [f"p_{l}" for l in LABELS] + [f"{p}_decision" for p in pols] + [f"{p}_outcome" for p in pols])
        for split, ps in per_scenario.items():
            for i, r in enumerate(rows):
                w.writerow([split, r["scenario_id"], r["ground_truth_action"]] + [round(x, 4) for x in ps["proba"][i]]
                           + [ps["decisions"][p][i] for p in pols] + [ps["outcomes"][p][i] for p in pols])

    from intervention import figures
    figures.make_all(rows, results, per_scenario, RES / "figures")
    from intervention.webdata import export_lab_data
    export_lab_data(rows, results, per_scenario, ROOT / "web" / "lab_data.json")
    print("done")


if __name__ == "__main__":
    main()
