# Experiment B: human factors of AI interruptions (protocol)

**Status: designed, not run.** Confirm the applicable IRB / ethics requirements before recruiting if results may be published.

## Aim

RQ3: Does explaining *why* an agent needs human input improve decision quality, perceived control and appropriate reliance, without increasing workload?

## Conditions (within-subjects)

| Condition | Approval request shown |
|---|---|
| Basic | "I need your approval to proceed." |
| Contextual | The proposed action, its consequence and the policy reason, e.g. "Send email to Ana Ruiz with customer_list.csv. This would send confidential material outside the company to an organisation without a partner agreement. Sent messages can't be recalled." |

Both conditions are already built into the Intervention Lab (Basic / Contextual toggle) and the Streamlit app.

## Design

* **Participants:** 24-40 adults with office-software experience, depending on recruitment feasibility.
* **Within-subjects**, counterbalanced condition order (AB / BA), with **matched but different task sets** per condition to avoid practice and memory effects. Build the two sets from different scenario families with equal mixes of: correct-to-approve, correct-to-reject (risky), and unnecessary-interruption items.
* **Per condition:** 12 interventions (4 approve-worthy, 4 reject-worthy, 4 that should not have interrupted), in randomised order inside a short workplace task narrative.

## Measures

| Construct | Measure |
|---|---|
| Decision quality | Correct approve/reject rate; split into accepting correct requests and rejecting incorrect ones (appropriate reliance) |
| Understanding | One comprehension item per intervention ("What would this action do?") |
| Effort | Response time per intervention; NASA-TLX (raw) per condition |
| Perceived control | Short perceived-control scale per condition |
| Trust | Short trust-in-automation scale per condition, reported separately from appropriate reliance |
| Interruption cost | Self-rated annoyance for unnecessary interruptions |

## Analysis plan

* Mixed-effects logistic regression for correctness: condition × item type, random intercepts for participant and item.
* Mixed-effects linear model for log response time.
* Paired comparisons for TLX, control and trust with estimation plots (Fig. 7) and 95% CIs.
* Pre-specified exploratory question: do contextual messages increase rubber-stamping on *unnecessary* interruptions (approval without reading)?

## Pilot first

Run 3-5 pilot participants to check task length (target < 30 min), comprehension-item difficulty, and that the risky items are recognisable without being trivially obvious. Revise, then freeze the protocol before the main study.
