"""Intervention policies compared in Experiment A.

Every policy maps a scenario row to one of ACT / CLARIFY / REQUEST_APPROVAL /
ESCALATE. None of them sees ground-truth fields.

  autonomous         Policy A. Always proceeds; the sandbox still records any
                     unauthorised or prohibited call as a failure.
  heuristic          A transparent keyword rule set of the kind a developer
                     might write in an afternoon. Included as a cheap
                     non-learned baseline; it is NOT the LLM baseline.
  llm_self_assess    Policy B. The task LLM judges whether it needs help.
                     Implemented in llm_baseline.py; requires an API key and is
                     reported as pending when no cached predictions exist.
  constraints_only   The written policy as hard rules (needs_approval ->
                     approval, prohibited -> escalate), otherwise act.
  model_only         The learned classifier with no hard constraints (ablation).
  gate               Policy C. Learned classifier + hard constraints. A
                     confident prediction can never lower a policy floor.
  always_ask         Optional baseline: request approval for every action.
"""
from __future__ import annotations

import re

from .labels import ACT, APPROVE, CLARIFY, ESCALATE, LABELS
from .workspace import NEEDS_APPROVAL, PROHIBITED, policy_check


def autonomous(row):
    return ACT


def always_ask(row):
    return APPROVE


def constraints_only(row):
    verdict, _ = policy_check(row["proposed_action"])
    return {PROHIBITED: ESCALATE, NEEDS_APPROVAL: APPROVE}.get(verdict, ACT)


_H_VAGUE = re.compile(r"\b(appropriate|whatever|sometime|soon|later|stuff|important|needs it|fix up|deal with|handle|better)\b", re.I)
_H_RISKY = re.compile(r"\b(delete|send|email|share|forward|cancel|pay|reply)\b", re.I)
_H_DANGER = re.compile(r"\b(every|all|permanently|bank|contract|salary|review|board)\b", re.I)


def heuristic(row):
    req = row["request"]
    if _H_RISKY.search(req) and _H_DANGER.search(req):
        return ESCALATE
    if _H_VAGUE.search(req):
        return CLARIFY
    if _H_RISKY.search(req):
        return APPROVE
    return ACT


def combine(model_label: str, row: dict) -> str:
    """Merge a learned prediction with the policy floor for the proposed call."""
    verdict, _ = policy_check(row["proposed_action"])
    if verdict == PROHIBITED:
        return ESCALATE
    if model_label == CLARIFY:
        return CLARIFY  # resolve missing information before asking for authorisation
    if verdict == NEEDS_APPROVAL and model_label == ACT:
        return APPROVE
    return model_label


def decide_with_threshold(proba, row, t_act: float, constrained: bool = True):
    """Act only if P(ACT) >= t_act; otherwise take the most likely intervention."""
    p = dict(zip(LABELS, proba))
    if p[ACT] >= t_act:
        lab = ACT
    else:
        lab = max((l for l in LABELS if l != ACT), key=p.get)
    return combine(lab, row) if constrained else lab
