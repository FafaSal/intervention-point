# The Intervention Point: when should AI stop and ask?

**Can an AI agent learn when to proceed on its own, ask for clarification, request approval, or hand a task to a human, and does that improve safety without burying people in interruptions?**

This repository is a working research pipeline for that question:

| Deliverable | Where |
|---|---|
| Simulated workplace (inbox, calendar, files, written policy) in SQLite | `src/intervention/workspace.py`, `data/workspace/` |
| 400 labelled decision points in 100 scenario families | `data/scenarios.jsonl`, `data/scenarios.csv` |
| Blinded annotation sheet + agreement script | `data/annotation/`, `src/intervention/agreement.py`, `docs/annotation_guide.md` |
| Trained intervention gate (logistic regression + hard constraints) | `src/intervention/gate.py`, `policies.py`, `results/intervention_gate.joblib` |
| Offline episode simulator with audit log | `src/intervention/simulate.py` |
| Experiment A: computational evaluation with bootstrap CIs | `scripts/run_all.py`, `results/metrics.json`, `results/predictions.csv` |
| Figures | `results/figures/` |
| Interactive Intervention Lab (portfolio page) | `web/index.html` + `web/lab_data.json` |
| Streamlit research prototype | `app/streamlit_app.py` |
| Experiment B protocol (human factors study) | `docs/human_study_protocol.md` |

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_all.py          # ~2 min: dataset -> training -> evaluation -> figures -> web data
pytest -q                          # 9 tests
streamlit run app/streamlit_app.py
cd web && python -m http.server    # open http://localhost:8000 for the Intervention Lab
```

## Design in one paragraph

A literal task agent proposes a tool call. The **intervention gate** decides ACT / CLARIFY / REQUEST_APPROVAL / ESCALATE. The gate is a multinomial logistic regression over (a) lexical cues in the request, (b) tf-idf of the request and any standing instruction, and (c) workspace lookups about the proposed call (recipient domain, data classification, retention, ownership, referent ambiguity). The written policy is enforced as **hard constraints** around the model: a prohibited call always escalates and a call needing approval can never be downgraded to ACT, however confident the model is. Every decision is then played out in a sandbox against a scripted human, and unauthorised or prohibited calls are logged as failures.

## Results so far (Experiment A, synthetic benchmark)

Primary split: **unseen task types** (5-fold leave-templates-out). 95% CIs from 1,000 family-level bootstrap resamples are in `results/metrics.json`.

| Policy | Unauthorised / prohibited calls | Unnecessary interruptions | Task completion | Severity-weighted error |
|---|---:|---:|---:|---:|
| A: Autonomous | 48.3% | 0.0% | 34.0% | 1.748 |
| Keyword heuristic | 24.3% | 44.1% | 63.2% | 0.893 |
| Always ask | 23.0% | 100% | 77.0% | 0.944 |
| Hard constraints only | 0.0% | 0.0% | 81.3% | 0.177 |
| Learned model only | 6.8% | 27.2% | 83.5% | 0.297 |
| **C: Trained gate** | **0.0%** | 27.2% | **89.5%** | **0.083** |
| B: LLM self-assessment | pending | | | |

What this shows, and what it does not:

* **Authorisation is a rule problem; information sufficiency is the learning problem.** Hard rules alone already prevent every unauthorised call. The learned component earns its place on *missing or conflicting information*: it raises completion from 81% to 90% and roughly halves severity-weighted error (paired difference CI excludes zero), but it interrupts 27% of tasks that were fine to run. That is the RQ2 trade-off in concrete form.
* **Neither part is enough alone.** The model without constraints makes unauthorised calls on 6.8% of tasks; constraints without the model act on every ambiguous request.
* **The split decides the story.** The same model scores 74% accuracy on unseen task types but 97% on unseen families, because families from the same template share structure. Report the stricter split.
* **Clarification is the weak spot.** On unseen task types the gate acts on 18 of 80 clarify-worthy requests (23%).

## Honest limitations

1. **Labels are provisional.** One author applied the rubric in `labels.py`. Before any claim of validity, two independent annotators should label `data/annotation/annotation_sheet_blinded.csv` (no labels, rubric facts or policy verdicts are shown), then run `python -m intervention.agreement <filled.csv>` and adjudicate. Sixteen items are already flagged `label_contested`.
2. **Policy B (LLM self-assessment) has not been run.** It is implemented in `llm_baseline.py` but needs an API key and was not tested against a live API. RQ1 cannot be answered until it runs. The keyword heuristic is a cheap stand-in, not an LLM.
3. **Synthetic, author-designed benchmark.** The same author wrote the scenarios, the policy and the model features, so these scores describe this benchmark, not real agents.
4. **Proposed actions are scripted.** The task agent is a literal proposer, not an LLM. Swapping in an LLM proposer is the obvious next step.
5. **The human is scripted.** Timings (clarify 30 s, approve 15 s, escalate 120 s) and costs are assumptions in `simulate.py`. Experiment B is designed but not run.

## Next steps

1. Run Policy B: `python -m intervention.llm_baseline --provider openai --model <model>` then re-run `scripts/run_all.py`.
2. Collect two independent annotations; report Cohen's kappa and Krippendorff's alpha; re-train on adjudicated labels.
3. Run Experiment B (see `docs/human_study_protocol.md`), after confirming IRB / ethics requirements.

## Repository map

```
src/intervention/  workspace, scenarios, labels (rubric), features, gate, policies,
                   simulate, metrics, agreement, llm_baseline, figures, webdata
scripts/run_all.py end-to-end pipeline
docs/              research_design.md, annotation_guide.md, human_study_protocol.md
```

Everything in the workspace is fictional; all domains use the reserved `.example` TLD.
