"""Export everything the Intervention Lab page needs into one JSON file."""
from __future__ import annotations

import json
from pathlib import Path

from .features import cue_features
from .labels import LABELS
from .scenarios import lookup_features

def clean(o):
    """Replace NaN (e.g. precision when a policy never intervenes) with None so the JSON is valid."""
    if isinstance(o, float) and o != o:
        return None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


CLS = ["public", "internal", "confidential", "restricted"]


def evidence(row):
    lk, cue = lookup_features(row), cue_features(row)
    ev = []
    if lk["n_recipients"]:
        who = ("outside the company, no partner agreement" if lk["any_unauthorized_external"] else
               "outside the company, authorised partner" if lk["any_external"] else
               "company-wide list" if lk["company_wide"] else "colleagues only")
        ev.append(("Recipients", who, lk["any_external"] or lk["company_wide"]))
    ev.append(("Most sensitive content", CLS[lk["max_classification"]], lk["max_classification"] >= 2))
    if lk["retention_or_hold"]:
        ev.append(("Records", "under retention or legal hold", True))
    if lk["others_file"] or lk["event_others"]:
        ev.append(("Owner", "someone else", True))
    if lk["event_protected"]:
        ev.append(("Event", "protected (board meeting)", True))
    if lk["event_external"]:
        ev.append(("Event", "has an external attendee", True))
    if lk["permanent"]:
        ev.append(("Reversibility", "permanent", True))
    if lk["commitment_or_payment"]:
        ev.append(("Commitment", "binding or financial", True))
    if lk["ambiguous_person"]:
        ev.append(("Referent", "name matches more than one person", True))
    if lk["ambiguous_file"]:
        ev.append(("Referent", "more than one matching file", True))
    if lk["no_destination_match"]:
        ev.append(("Destination", "no folder can be inferred", True))
    if cue["cue_vague"]:
        ev.append(("Wording", "contains vague terms", True))
    if cue["cue_conflict"]:
        ev.append(("Wording", "contains a constraint that may conflict", True))
    if cue["has_standing_instruction"]:
        ev.append(("Standing instruction", "in force", True))
    return [{"k": k, "v": v, "flag": bool(f)} for k, v, f in ev]


def export_lab_data(rows, results, per_scenario, path: Path):
    scen = []
    for r in rows:
        scen.append({
            "id": r["scenario_id"], "fam": r["family_id"], "tpl": r["template"], "cat": r["category"], "var": r["variation"],
            "factor": r["varied_factor"], "req": r["request"], "ctx": r["context"], "act": r["proposed_action_text"],
            "verdict": r["policy_verdict"], "reason": r["policy_reason"], "sev": r["severity"], "rev": r["reversible"],
            "truth": r["ground_truth_action"], "rule": r["label_rule"], "contested": r["label_contested"],
            "cq": r["clarify_question"], "ca": r["simulated_human"]["clarify_answer"], "approves": r["simulated_human"]["approves"],
            "cons": r["potential_consequence"], "ev": evidence(r),
        })
    splits = {}
    for split, ps in per_scenario.items():
        sr = results["splits"][split]
        splits[split] = {
            "description": sr["description"],
            "proba": [[round(x, 3) for x in p] for p in ps["proba"]],
            "decisions": ps["decisions"], "outcomes": ps["outcomes"], "interactions": ps["interactions"],
            "metrics": sr["metrics"], "ci95": sr["ci95"], "diff": sr["paired_diff_ci95"], "model_accuracy": sr["model_accuracy"],
            "confusion_gate": sr["confusion_gate"], "calibration": sr["calibration"],
            "sweep_gate": sr["sweep_gate"], "sweep_model_only": sr["sweep_model_only"],
            "flows": sr["gate_flows"], "failures": sr["failure_cases"], "by_category": sr["by_group"]["category"],
        }
    out = {"labels": LABELS, "policy_names": results["policy_names"], "llm_baseline": results["llm_baseline"],
           "label_counts": results["label_counts"], "scenarios": scen, "splits": splits, "top_features": results["top_features"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(out), separators=(",", ":"), allow_nan=False))
