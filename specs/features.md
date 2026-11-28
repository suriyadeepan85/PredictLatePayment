# Component Spec: Features (gate G2)

**Version:** 0.1 · **Date:** November 26, 2026 · **Owner:** Suriyadeepan Narayanasamy · **Builder role:** ML Engineer, with the Data Engineer for history tables
**Status:** G2 APPROVED (D-080) for v0.1. The v0.2 change (rare codes counted on training rows only) is in the code and waits for the owner's approval with D-099; the encodings table documents the existing code. The fixed limits in section 6 come from the APPROVED data contract v1.4.

## 1. Objective and scope
Define every model input: how it is calculated, as of when, and what it is when there is no value. Covers Stage 1 (Dataset A) and Model A, Model B and the ceiling model (Dataset B). The note signals are defined in `specs/note_features.md`; this spec only says where they plug in.

## 2. Inputs and dependencies
Clean tables from `src/data/load.py` (`load_a`, `load_b`), which apply contract sections 3, 8 and 9 and reproduce its row counts exactly. Depends on: data contract v1.4 (APPROVED).

## 3. Feature list
### Invoice features
| Feature | Dataset | Calculation |
|---|---|---|
| `log_amount` | A, B | log(1 + amount) |
| `terms_days` | A | Due date minus baseline date. Dropped for B (all invoices have 30-day terms) |
| `payment_terms` | A | Payment-term code; fewer than 20 **training** invoices → OTHER (counted on training rows only) |
| `business_code` | A | Business unit; fewer than 20 **training** invoices → OTHER |
| `country_code` | B | As given |
| `paperless` | B | 1 if PaperlessBill = Electronic |

### Customer history features
Calculated from the same customer's invoices **paid strictly before the invoice date**. For Dataset B the cut-off is also the invoice date, not the Stage 2 date: history is frozen (D-064).

| # | Feature | Calculation | No value |
|---|---|---|---|
| H1 | `hist_n_paid` | Count of eligible invoices | 0 |
| H2 | `hist_late_share` | Late ÷ count | Missing |
| H3 | `hist_avg_days_late` | Mean of days late, each capped at ±90 | Missing |
| H4 | `hist_days_since_last_late` | Invoice date minus clear date of the last eligible late invoice | Missing (no history, or never late) |
| H5 | `hist_std_days_late` | Sample standard deviation of capped days late | Missing if fewer than 2 |
| H6 | `hist_group` | none = 0, limited = 1-4, enough = 5+ (D-061) | none |
| H7 | `hist_last_late` | 1 if the most recently paid eligible invoice was late | Missing |

"Missing" stays missing; it is never filled with 0. XGBoost handles missing values natively.

### Inputs per model
| Model | Inputs | Use |
|---|---|---|
| Stage 1 | `log_amount`, `terms_days`, `payment_terms`, `business_code`, H1 to H7 | App |
| Model A | `log_amount`, `paperless`, `country_code`, H1 to H7 | Yardstick (D-071) |
| Model B | Model A inputs plus note signals S1 to S7 | App (D-064) |
| Ceiling | Model A inputs plus `disputed` | Evaluation only (D-073) |
| Baseline | H7 alone: flag if late last time | Yardstick (D-021) |

### Note signal encodings (Model B; values from `src/features/notes.py` `aggregate`)
| Column | Values | No note |
|---|---|---|
| `has_invoice_note` | 1 if the invoice has a linked note dated on or before its Stage 2 date, else 0 | 0 |
| `s1_open_dispute` | 1 open, 0 none or resolved by the latest dispute note | NaN |
| `s1_reason` | First stated reason: wrong amount, duplicate charge, pricing, goods or service issue, other, none | `no_note` |
| `s2_po_or_contact` | 1 if an invoice note says missing PO, or a customer note since the invoice date says the contact changed | NaN if neither kind of note exists |
| `s3_promise` | 1 if any invoice note promises payment | NaN |
| `s3_days_promise_vs_due` | Latest promised date minus due date, in days | NaN |
| `s4_escalation` | 1 if any invoice note asks to escalate | NaN |
| `s5_contacts_30d` | Customer notes in the 30 days up to the Stage 2 date | 0 |
| `s6_tone` | Tone of the customer's latest note: −1 negative, 0 neutral, 1 positive | NaN |
| `s7_open_claim` | 1 if any customer note in the 90 days up to the Stage 2 date mentions a claim | NaN if the customer has no notes |

Never inputs: customer ID, customer name or label, invoice ID, any date as a raw value, clear date, days late, the label, and (except for the ceiling) `disputed`.

## 4. Technical requirements
1. One function, `src/features/history.py: build_history(df, asof_col)`, builds H1 to H7 for both datasets.
2. Eligibility uses `clear_date < asof` (strictly before), so an invoice never counts towards its own history.
3. Categories are encoded inside the model pipeline, with OTHER for codes unseen in training.

## 5. Interface
`build_history(df, asof_col="invoice_date") -> DataFrame` with columns `hist_n_paid` … `hist_last_late`, indexed like `df`. `df` needs `customer_id`, `clear_date`, `days_late`, `late` and the as-of column.

## 6. Constraints (from the APPROVED contract)
History only from invoices paid before the cut-off (section 7, rule 1); the history count is always a feature (rule 3); no history is explicit, never 0 (rule 4); days late capped at ±90 (rule 7); no outcome columns as inputs (section 10).

## 7. Testing requirements
| Test | Where | Pass condition |
|---|---|---|
| F1 Cut-off | `tests/test_history.py` | Only invoices paid strictly before the cut-off count, including the same-day edge case |
| F2 Values | `tests/test_history.py` | Share, mean with the cap, recency and group match hand-worked values |
| F3 No history | `tests/test_history.py` | Missing, not 0; group none |
| F4 Brute force | test file and notebook 04 section 6 | Counts match a direct recount on random samples |
| F5 No outcomes | Notebook 04 section 6 | No outcome column in any model's inputs |
| F6 Row counts | `load_a`, `load_b` | Match contract section 9 exactly |

## 8. Acceptance criteria
F1 to F6 pass, and the notebook runs end to end. Status on November 27, 2026: all pass (`pytest`: 32 passed, including F5 and F6 in `tests/test_contract_and_leakage.py`; notebook 04 runs clean).

## 9. Deliverables
`src/data/load.py`, `src/features/history.py`, `tests/test_history.py`, `notebooks/04_features.ipynb` (built by `notebooks/build_features_notebook.py`), `docs/img/features_history.png`.

## 10. Evidence and open issues
Training set only (test kept for the Evaluator), Dataset A:
- Each measure on its own (AUC): average days late 0.74, share late 0.68, invoices paid 0.64, terms 0.62, late last time 0.61, days since last late 0.52, spread 0.52, amount 0.50.
- Late rate falls from 27% with no history to 13% with 5 or more paid invoices; customers whose share late is above 50% are late 74% of the time.
- Only about 1% of test invoices have no history, against 11% of training invoices.

Open: none. Amount, days since last late, and spread look weak on their own but stay in, because they can still help in combination; the Evaluator's results at G3 decide whether anything is dropped.

## Change log
| Date | Change |
|---|---|
| Nov 26, 2026 | v0.1: first draft with notebook evidence |
| Nov 27, 2026 | v0.2 after the independent review: note signal encodings written out (R-06); rare-code grouping on training rows only (R-10); ties in history ordered by clear date, then invoice date |
