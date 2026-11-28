# Status

**Last checkpoint:** November 27, 2026 · **Due:** November 30, 2026 (finish by November 29)

## Current gate
**G1 closed** (data contract v1.4, D-075). **G2 approved** (D-080). **G3 (model and fairness) in progress.** Review decisions made (D-102 to D-105). Stage 1 and the three IBM models validated; waiting for owner calls Q-015, Q-016; then the Evaluator scores the test sets.

## Done
- Spec v2 created; spec v1 restored and unchanged
- Repo connected; push works
- Customer Invoices data profiled (`notebooks/01_profile_data.ipynb`, charts in `docs/img/`)
- Data contract v1.3: Stage 2 inputs, notes data rules and IBM split approved (D-064 to D-068)
- IBM split notebook with scikit-learn TimeSeriesSplit (`notebooks/03_ibm_split.ipynb`, chart `docs/img/ibm_split.png`)
- History profile (`notebooks/02_history_profile.ipynb`)
- Independent review done (`reports/review_2026-11-27.md`); technical fixes applied (D-099): calibrated probabilities, hardened masking, 32 tests
- Notes generated with fake personal details, masked by rules (N6 = 0), read into signals (`notebooks/05_note_features.ipynb`)
- IBM Model A, Model B, ceiling built (`notebooks/07_stage2_models.ipynb`); the headline result is invalid until Q-017 and Q-018 are decided (D-101)
- Stage 1 trained and validated (`notebooks/06_stage1_model.ipynb`, MLflow); infrastructure and security spec (`specs/infrastructure.md`); contract v1.5 (masking)
- G2 feature spec, shared code (`src/data/load.py`, `src/features/history.py`), tests (4 pass), `notebooks/04_features.ipynb`
- Coordinator and role specs v0.1 in `specs/agents/` (D-079); index in `specs/README.md`
- Note features spec v0.1 (`specs/note_features.md`); seven signals approved (D-074)
- Comparison models approved: Model A without notes (D-071), ceiling model (D-073)
- Methodology set up: `CLAUDE.md`, `DECISIONS.md`, `OPEN_ITEMS.md`, `STATUS.md`, `specs/methodology.md`

## Waiting for the owner
1b. Approve `specs/infrastructure.md` and do owner steps 2, 3, 5 to 9
2. Approve the coordinator spec (human-owned, `specs/agents/coordinator.md` section 3)
3. Q-014: copy the system spec into the repo (recommended)
4. Answer Q-001 (organizer approval) and Q-002 (hosted or laptop)
5. Confirm the older PROPOSED records; D-001 and D-004 are out of date (superseded in practice by D-050, D-051)

## Next
1. Streamlit app (judge-facing: walkthrough, per-session clock, adjustable bands, SHAP reasons, outreach draft)
2. Evaluator pass on the test sets (G3), in a separate session
3. Terraform, SageMaker Pipeline, deploy (after owner approval of `specs/infrastructure.md`); then demo and deck

## Plan
| Day | Focus | State |
|---|---|---|
| 1 | Data and model | In progress: G1, G2 closed; Stage 1 validated |
| 2 | Application | Not started |
| 3 | Demo and deck | Not started |
