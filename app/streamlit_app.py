"""Research prototype of the Intervention Lab (Streamlit).

    pip install -r requirements.txt
    python scripts/run_all.py          # builds data/ and results/
    streamlit run app/streamlit_app.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intervention.labels import LABELS, SHORT  # noqa: E402
from intervention.scenarios import load  # noqa: E402
from intervention.webdata import evidence  # noqa: E402

st.set_page_config(page_title="Intervention Lab", layout="wide")


@st.cache_data
def data():
    rows = load(ROOT / "data" / "scenarios.jsonl")
    res = json.loads((ROOT / "results" / "metrics.json").read_text())
    pred = pd.read_csv(ROOT / "results" / "predictions.csv")
    return rows, res, pred


rows, res, pred = data()
names = res["policy_names"]

st.title("When should AI stop and ask?")
split = st.radio("Evaluation split", ["template", "family_id"], horizontal=True,
                 format_func=lambda s: res["splits"][s]["description"])
sp = res["splits"][split]
P = pred[pred.split == split].set_index("scenario_id")

c1, c2, c3 = st.columns([1, 2, 1])
cat = c1.selectbox("Category", ["all"] + sorted({r["category"] for r in rows}))
pool = [r for r in rows if cat == "all" or r["category"] == cat]
row = c2.selectbox("Scenario", pool, format_func=lambda r: f"{r['scenario_id']} · {r['request'][:80]}")
pols = [p for p in names if f"{p}_decision" in P.columns]
policy = c3.selectbox("Policy", pols, index=pols.index("gate"), format_func=names.get)
style = st.toggle("Contextual approval message", value=True)

p = P.loc[row["scenario_id"]]
decision = p[f"{policy}_decision"]
a, b, c, d = st.columns(4)
with a:
    st.subheader("1 · Task")
    st.markdown(f"**“{row['request']}”**")
    if row["context"]:
        st.info(row["context"])
    st.caption(f"{row['category']} · severity {row['severity']}/4 · {'reversible' if row['reversible'] else 'irreversible'}")
with b:
    st.subheader("2 · Gate summary")
    st.write(f"Proposes: **{row['proposed_action_text']}**")
    for e in evidence(row):
        st.write(("⚠️ " if e["flag"] else "") + f"{e['k']}: {e['v']}")
    st.caption(f"Policy check: {row['policy_verdict']} · {row['policy_reason']}")
    st.bar_chart(pd.Series({SHORT[l]: p[f"p_{l}"] for l in LABELS}))
    st.markdown(f"**{names[policy]} → {SHORT[decision]}**")
with c:
    st.subheader("3 · Human")
    if decision == "CLARIFY":
        st.write(row["clarify_question"] or f"Before I go ahead: {row['proposed_action_text']}. Is that right?")
        st.caption(f"Scripted answer: {row['simulated_human']['clarify_answer'] or 'Yes, go ahead.'}")
    elif decision == "REQUEST_APPROVAL":
        st.write(f"{row['proposed_action_text']}. {row['potential_consequence']}" if style else "I need your approval to proceed.")
        st.caption("Scripted human " + ("approves" if row["simulated_human"]["approves"] else "rejects"))
    elif decision == "ESCALATE":
        st.write("Handed to a human owner.")
    else:
        st.write("No interruption.")
with d:
    st.subheader("4 · Outcome")
    st.markdown(f"**{p[f'{policy}_outcome'].replace('_', ' ')}**")
    st.write(f"Correct decision: {SHORT[row['ground_truth_action']]} ({row['label_rule']})")

st.divider()
st.subheader("Policy comparison")
m = pd.DataFrame(sp["metrics"]).T.rename(index=names)
st.dataframe(m.style.format("{:.3f}"), width="stretch")
st.caption(f"LLM self-assessment baseline: {res['llm_baseline']}")
fig_dir = ROOT / "results" / "figures"
tag = "unseen_task_types" if split == "template" else "unseen_families"
cols = st.columns(2)
for i, f in enumerate([f"fig3_autonomy_vs_risk_{tag}.png", f"fig2_confusion_gate_{tag}.png",
                       f"fig5_reliability_{tag}.png", f"fig6_outcomes_{tag}.png"]):
    cols[i % 2].image(str(fig_dir / f))
