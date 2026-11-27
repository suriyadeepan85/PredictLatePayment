# Status

**Last checkpoint:** November 26, 2026 · **Due:** November 30, 2026 (finish by November 29)

## Current gate
**G1 closed** (data contract v1.4, D-075). **G2 (feature list) drafted, waiting for approval** (`specs/features.md`, D-080).

## Done
- Spec v2 created; spec v1 restored and unchanged
- Repo connected; push works
- Customer Invoices data profiled (`notebooks/01_profile_data.ipynb`, charts in `docs/img/`)
- Data contract v1.3: Stage 2 inputs, notes data rules and IBM split approved (D-064 to D-068)
- IBM split notebook with scikit-learn TimeSeriesSplit (`notebooks/03_ibm_split.ipynb`, chart `docs/img/ibm_split.png`)
- History profile (`notebooks/02_history_profile.ipynb`)
- G2 feature spec, shared code (`src/data/load.py`, `src/features/history.py`), tests (4 pass), `notebooks/04_features.ipynb`
- Coordinator and role specs v0.1 in `specs/agents/` (D-079); index in `specs/README.md`
- Note features spec v0.1 (`specs/note_features.md`); seven signals approved (D-074)
- Comparison models approved: Model A without notes (D-071), ceiling model (D-073)
- Methodology set up: `CLAUDE.md`, `DECISIONS.md`, `OPEN_ITEMS.md`, `STATUS.md`, `specs/methodology.md`

## Waiting for the owner
1. G2: approve `specs/features.md` (D-080)
2. Approve the coordinator spec (human-owned, `specs/agents/coordinator.md` section 3)
3. Q-014: copy the system spec into the repo (recommended)
2. Confirm or change the seeded records in `DECISIONS.md` (all PROPOSED except D-007)
3. Answer Q-001 and Q-002 in `OPEN_ITEMS.md`

## Next
2. Train the baseline and XGBoost; evaluation and fairness check; reviewer pass (G3)
3. Streamlit app (Day 2), then demo and deck (Day 3)

## Plan
| Day | Focus | State |
|---|---|---|
| 1 | Data and model | In progress: G1 |
| 2 | Application | Not started |
| 3 | Demo and deck | Not started |
