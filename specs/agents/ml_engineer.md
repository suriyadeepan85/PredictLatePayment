# ML Engineer Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** section 7.1 (11 sections) · **Status:** PROPOSED (D-079). Items marked APPROVED cite the owner's record.

## 1. Objective and scope
Build, train and evaluate the models that predict whether an invoice will be paid more than 3 calendar days late, and give each prediction plain-word reasons.

| Model | Data | Scoring time | Inputs | Use |
|---|---|---|---|---|
| Baseline | A and B | Same as its model | "Late last time" rule | Yardstick |
| Stage 1 | A (50k) | Invoice date | Invoice fields, history as of the invoice date | App (APPROVED, D-059) |
| Model A | B (IBM) | Due date minus 10 days | Stage 1 inputs only | Evaluation only (APPROVED, D-071) |
| Model B, Stage 2 | B (IBM) | Due date minus 10 days | Stage 1 inputs, history frozen at the invoice date, plus note signals S1 to S7 | App (APPROVED, D-064) |
| Ceiling | B (IBM) | Due date minus 10 days | Stage 1 inputs plus the Disputed flag | Evaluation only (APPROVED, D-073) |

The ML Engineer may not change labels, splits, scoring times, column roles or fairness rules. Those belong to the data contract.

## 2. Data contract and input datasets
`docs/data_contract.md` v1.4 (APPROVED). Cleaned tables from the Data Engineer; note signals from the LLM Engineer (`specs/note_features.md`).

## 3. Feature engineering
Defined in `specs/features.md` (gate G2). Fixed limits from the contract: history only from invoices paid before the cut-off; the history count is always a feature; history group none / limited / enough (0 / 1-4 / 5+, APPROVED, D-061); average days late capped at ±90; customer IDs and names are never features.

## 4. Target and labeling
Late = paid more than 3 calendar days after the due date (APPROVED, D-012, D-056). Labels only for paid invoices. Open invoices are never in any metric.

## 5. Model development strategy
Logistic regression first, as a simple, explainable reference; then XGBoost (D-020, D-084). The better one on validation goes forward. No class weighting or resampling, so predicted probabilities stay calibrated for cash at risk (review R-03); calibration is reported (mean predicted vs actual, Brier score). Hyperparameters tuned only inside the training period, using `TimeSeriesSplit`. Fixed random seed. Same code for all four IBM-side models, changing only the input list.

### Settings (for a rebuild)
- Logistic regression: median imputation with missing-value indicators, standard scaling, one-hot encoding (codes with fewer than 20 rows grouped), C = 1.0, no class weighting.
- XGBoost: 400 trees, learning rate 0.05, depth 5, subsample 0.8, column sample 0.8, min child weight 20, L2 regularisation 5, `hist` tree method, native categorical handling, seed 42, no class weighting.
- Rolling validation: `TimeSeriesSplit` on date-sorted training invoices, 5 folds (Dataset A) or 4 (Dataset B); each fold trains only on invoices paid before the fold's first validation date (D-089).

## 6. Training and evaluation strategy
- Splits: A train before October 1, 2019, test after (APPROVED, D-063); B train before July 1, 2013, test after (APPROVED, D-068).
- The test set is touched once, by the Evaluator, at the end.
- Metrics: AUC, PR-AUC, and the share of late invoices caught in the top 20% of flags (D-021). Never plain accuracy.
- Report each metric overall, by history group and by fairness group (business unit for A, country code for B).

## 7. Model acceptance criteria (PROPOSED; thresholds need owner approval at G3)
| # | Criterion |
|---|---|
| M1 | Stage 1 beats the baseline on test-set AUC and top-20% capture |
| M2 | Model B beats Model A on the same IBM test invoices; the gap is reported with a bootstrap 95% interval |
| M3 | Model B is not near-perfect (leakage alarm, contract section 6 rule 7) |
| M4 | Fairness: no group's false-alarm rate above 1.25 times the overall rate, unless that group's real late rate is also higher (D-022, D-072) |
| M5 | Reruns with the same seed give the same metrics |

## 8. Model interface
`src/model/predict.py`: `score(invoices_df, stage) -> DataFrame[invoice_id, risk, risk_band, reason_1, reason_2, reason_3]`. Risk bands: default high = top 20% of training scores, medium = next 30%, low = the rest; the user can move both cut-offs in the app, and cash at risk (probability × amount) updates live (D-085). Reasons are the top 3 SHAP contributions, translated by a fixed lookup table in `src/model/reasons.py` (for example "paid late on 4 of the last 5 invoices").

## 9. Integration requirements
Every training run, from a notebook or the pipeline, is logged to open-source MLflow (parameters, metrics, model file), tagged `source=notebook` or `source=pipeline` (D-084). Saved models also get a JSON card: training dates, rows, inputs, metrics, data SHA-256. The SageMaker Pipeline registers a model only if it passes section 7; the endpoint serves only Approved registry versions. The app loads models only through `predict.py`, which calls the endpoint and falls back to the packaged model (D-083).

## 10. Testing and monitoring
Unit tests for feature cut-offs, no outcome columns in inputs, reason lookup coverage. Monitoring is out of scope for the hackathon; the full build adds drift checks on late rate and score distribution (the IBM test set already shows a lower late rate: 21.5% against 30.3% in training).

## 11. Execution environment and infrastructure
Python 3.11, pandas, scikit-learn, xgboost, shap, mlflow. Notebooks run on a laptop or in SageMaker; the pipeline runs on small SageMaker instances (`specs/infrastructure.md`). Training takes minutes; no GPU needed. Notebooks: `06_stage1_model.ipynb`, `07_stage2_models.ipynb`, importing from `src/`.
