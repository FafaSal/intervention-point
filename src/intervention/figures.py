"""Static figures (PNG) generated from computed results.

Decision colours were checked with a CVD palette validator: they pass all
hard gates but the worst pair (Act vs Escalate under deuteranopia) sits in
the 6-8 Delta E band, so every chart also encodes the decision by marker
shape and text label. Maroon is reserved for the trained gate.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import warnings  # noqa: E402
warnings.filterwarnings("ignore", category=RuntimeWarning)

from .labels import ACT, APPROVE, CLARIFY, ESCALATE, LABELS, SHORT  # noqa: E402

PAPER, INK, INK2, MUTED, GRID = "#F7F4EF", "#2B2A28", "#55534F", "#8C8A85", "#E4E0D8"
MAROON = "#7A1F2B"
DECISION_COLOR = {ACT: "#1baf7a", CLARIFY: "#eda100", APPROVE: "#6250d6", ESCALATE: "#e34948"}
DECISION_MARK = {ACT: "o", CLARIFY: "^", APPROVE: "s", ESCALATE: "X"}
POLICY_COLOR = {"gate": MAROON, "model_only": "#B9848B", "constraints_only": "#5C5A56", "heuristic": "#8C8A85",
                "autonomous": "#B5B2AB", "always_ask": "#B5B2AB", "gate_text_only": "#A8787F", "llm_self_assess": "#2a78d6"}

plt.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER, "font.family": "DejaVu Sans",
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.titleweight": "bold", "axes.axisbelow": True, "axes.titlesize": 12, "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def _save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def dataset_composition(rows, out):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), gridspec_kw={"width_ratios": [1.6, 1, 1]})
    cats = ["clear_instructions", "missing_information", "ambiguous_intent", "sensitive_action", "conflicting_requirements"]
    ax = axes[0]
    left = np.zeros(len(cats))
    for lab in LABELS:
        vals = np.array([sum(r["category"] == c and r["ground_truth_action"] == lab for r in rows) for c in cats])
        ax.barh(range(len(cats)), vals, left=left, color=DECISION_COLOR[lab], edgecolor=PAPER, linewidth=2, label=SHORT[lab], height=0.62)
        for i, v in enumerate(vals):
            if v >= 8:
                ax.text(left[i] + v / 2, i, str(v), ha="center", va="center", fontsize=8.5, color=INK)
        left += vals
    ax.set_yticks(range(len(cats)), [c.replace("_", " ") for c in cats]); ax.invert_yaxis()
    ax.set_xlabel("decision points"); ax.set_title("Ground-truth decision by task category")
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, -0.34), frameon=False, fontsize=9)
    ax.grid(axis="y", visible=False)
    for ax, key, title, levels in [(axes[1], "severity", "By consequence severity", [1, 2, 3, 4]),
                                   (axes[2], "reversible", "By reversibility", [True, False])]:
        bottom = np.zeros(len(levels))
        for lab in LABELS:
            vals = np.array([sum(r[key] == lv and r["ground_truth_action"] == lab for r in rows) for lv in levels])
            ax.bar(range(len(levels)), vals, bottom=bottom, color=DECISION_COLOR[lab], edgecolor=PAPER, linewidth=2, width=0.62)
            bottom += vals
        ax.set_xticks(range(len(levels)), [str(lv) if key == "severity" else ("reversible" if lv else "irreversible") for lv in levels])
        ax.set_title(title); ax.grid(axis="x", visible=False)
    fig.suptitle(f"Dataset composition: {len(rows)} decision points in {len({r['family_id'] for r in rows})} families "
                 "(provisional single-author labels)", x=0.01, ha="left", fontsize=10, color=INK2)
    fig.tight_layout()
    _save(fig, out)


def decision_landscape(rows, proba, out):
    proba = np.asarray(proba)
    ent = -(proba * np.log(np.clip(proba, 1e-9, 1))).sum(1) / np.log(4)
    rng = np.random.default_rng(3)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for lab in LABELS:
        idx = [i for i, r in enumerate(rows) if r["ground_truth_action"] == lab]
        ax.scatter(ent[idx], np.array([rows[i]["severity"] for i in idx]) + rng.uniform(-0.28, 0.28, len(idx)),
                   s=34, marker=DECISION_MARK[lab], color=DECISION_COLOR[lab], edgecolor=PAPER, linewidth=0.8, label=SHORT[lab], alpha=0.9)
    ax.set_yticks([1, 2, 3, 4], ["1 trivial", "2 moderate", "3 serious", "4 critical"])
    ax.set_xlabel("Model uncertainty on held-out task types (normalised predictive entropy)")
    ax.set_ylabel("Consequence severity")
    ax.set_title("The decision landscape")
    ax.legend(title="Ground truth", frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    _save(fig, out)


def confusion_matrix(M, title, out):
    M = np.asarray(M)
    fig, ax = plt.subplots(figsize=(5.8, 5))
    ax.grid(False)
    rown = M / M.sum(1, keepdims=True)
    ax.imshow(rown, cmap="Greys", vmin=0, vmax=1.6)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{M[i, j]}\n{rown[i, j]:.0%}", ha="center", va="center", fontsize=9.5,
                    color="white" if rown[i, j] > 0.75 else INK)
    for i in [2, 3]:  # false autonomy: truth approval/escalate, predicted act
        ax.add_patch(plt.Rectangle((-0.5, i - 0.5), 1, 1, fill=False, edgecolor=MAROON, linewidth=2.5))
    for j in [1, 2, 3]:
        ax.add_patch(plt.Rectangle((j - 0.5, -0.5), 1, 1, fill=False, edgecolor="#eda100", linewidth=1.5, linestyle="--"))
    ax.set_xticks(range(4), [SHORT[l] for l in LABELS]); ax.set_yticks(range(4), [SHORT[l] for l in LABELS])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Ground truth (provisional)")
    ax.set_title(title)
    ax.text(0, 1.02, "solid maroon = dangerous false autonomy   dashed amber = excess intervention",
            transform=ax.transAxes, fontsize=8, color=INK2)
    for s in ax.spines.values():
        s.set_visible(False)
    _save(fig, out)


def autonomy_risk(split_res, out, names):
    fig, ax = plt.subplots(figsize=(8.2, 5))
    for key, lab, ls in [("sweep_model_only", "Learned model only", "--"), ("sweep_gate", "Trained gate (model + constraints)", "-")]:
        sw = split_res[key]
        ax.plot([s["autonomy"] * 100 for s in sw], [s["severity_weighted_error"] for s in sw], ls, color=POLICY_COLOR["gate" if key == "sweep_gate" else "model_only"],
                lw=2, label=lab, drawstyle="default")
    m = split_res["metrics"]
    for pol in ["autonomous", "heuristic", "constraints_only", "always_ask", "gate", "llm_self_assess"]:
        if pol not in m:
            continue
        y = m[pol]["severity_weighted_error"]
        ax.scatter([split_res["_autonomy"][pol] * 100], [y], s=70, color=POLICY_COLOR[pol], edgecolor=INK, linewidth=0.8, zorder=5)
        ax.annotate(names[pol], (split_res["_autonomy"][pol] * 100, y), textcoords="offset points",
                    xytext=(7, -15) if pol == "gate" else (7, 5), fontsize=8.5, color=INK)
    ax.set_xlabel("Decisions made autonomously (%)")
    ax.set_ylabel("Severity-weighted error per task")
    ax.set_title("Autonomy vs. risk")
    ax.legend(frameon=False, loc="upper left")
    _save(fig, out)


def reliability(cal, out):
    fig, ax = plt.subplots(figsize=(5.4, 5))
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls=":")
    b = cal["bins"]
    ax.plot([x["mean_pred"] for x in b], [x["observed"] for x in b], "-o", color=MAROON, lw=2, ms=6)
    for x in b:
        ax.annotate(f"n={x['n']}", (x["mean_pred"], x["observed"]), textcoords="offset points", xytext=(5, -11), fontsize=7.5, color=INK2)
    ax.set_xlim(0, 1); ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Predicted P(intervention needed)"); ax.set_ylabel("Observed share needing intervention")
    ax.set_title("Can the model recognise its own uncertainty?")
    ax.text(0.02, 0.92, f"ECE {cal['ece']:.3f}   Brier {cal['brier']:.3f}", transform=ax.transAxes, fontsize=9, color=INK2)
    _save(fig, out)


def outcome_bars(split_res, out, names):
    order = ["autonomous", "heuristic", "always_ask", "constraints_only", "model_only", "gate"]
    if "llm_self_assess" in split_res["outcomes"]:
        order.insert(2, "llm_self_assess")
    groups = [("completed", ["success", "success_declined", "correct_escalation"], "#9DBFAF"),
              ("over-escalated", ["over_escalation"], "#C9C5BC"),
              ("wrong state", ["wrong_state"], "#eda100"),
              ("unauthorised / prohibited call", ["unauthorized_action", "prohibited_attempt"], "#e34948")]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for i, pol in enumerate(order):
        oc = split_res["outcomes"][pol]; tot = sum(oc.values()); left = 0
        for name, keys, col in groups:
            v = sum(oc.get(k, 0) for k in keys) / tot * 100
            ax.barh(i, v, left=left, color=col, edgecolor=PAPER, linewidth=2, height=0.62, label=name if i == 0 else None)
            if v >= 6:
                ax.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=8.5, color=INK)
            left += v
    ax.set_yticks(range(len(order)), [names[p] for p in order]); ax.invert_yaxis()
    ax.set_xlabel("% of 400 simulated tasks"); ax.set_xlim(0, 100)
    ax.set_title("What happened in the simulated workspace")
    ax.legend(ncol=4, frameon=False, loc="lower left", bbox_to_anchor=(0, -0.3), fontsize=8.5)
    ax.grid(axis="y", visible=False)
    _save(fig, out)


def make_all(rows, results, per_scenario, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    names = results["policy_names"]
    dataset_composition(rows, out_dir / "fig0_dataset_composition.png")
    for split, tag in [("template", "unseen_task_types"), ("family_id", "unseen_families")]:
        sr = results["splits"][split]
        sr["_autonomy"] = {pol: float(np.mean([d == ACT for d in decs])) for pol, decs in per_scenario[split]["decisions"].items()}
        decision_landscape(rows, per_scenario[split]["proba"], out_dir / f"fig1_decision_landscape_{tag}.png")
        confusion_matrix(sr["confusion_gate"], "Trained gate: predicted vs. labelled decision", out_dir / f"fig2_confusion_gate_{tag}.png")
        autonomy_risk(sr, out_dir / f"fig3_autonomy_vs_risk_{tag}.png", names)
        reliability(sr["calibration"], out_dir / f"fig5_reliability_{tag}.png")
        outcome_bars(sr, out_dir / f"fig6_outcomes_{tag}.png", names)
        sr.pop("_autonomy")
