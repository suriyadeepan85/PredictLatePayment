# Evaluator Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Status:** PROPOSED (D-079). Not in the methodology document; added because model results must be judged by someone who didn't build the model.

## 1. Objective and scope
Score every model once on its held-out test set and give the G3 verdict: does it beat its baseline, and is it fair?

## 2. Rules
1. The Evaluator does not train or tune. It receives saved models and the test sets, and nothing else.
2. Each test set is used once per model version. A re-run after changes is logged as a new version.
3. In the hackathon, the evaluation runs in a separate fresh session (a subagent) that sees only the specs, the saved models and the test data, not the build conversation.

## 3. What it reports
- AUC, PR-AUC and top-20% capture for: baseline, Stage 1 (A); baseline, Model A, Model B, ceiling (B).
- The Model B minus Model A gap with a bootstrap 95% interval; how much of the ceiling's gain Model B recovers.
- By history group and by fairness group: flag rate, false-alarm rate, miss rate, real late rate.
- Pass or fail against ML criteria M1 to M5 (`ml_engineer.md` section 7).

## 4. Deliverables
`reports/evaluation_<date>.md` and `notebooks/07_evaluation.ipynb`, which the owner can rerun.

## 5. Acceptance criteria
Every number in the deck and on the model evidence screen comes from this report.
