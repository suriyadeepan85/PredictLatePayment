# Data Contract v1.5: Late Payment Prediction (Stage 1 and Stage 2)

**Status:** APPROVED, gate G1 closed (D-075) · **Date:** November 27, 2026 · **Owner:** Suriyadeepan Narayanasamy
**Based on:** the owner's v1.1 (feature eligibility, history coverage, prediction-time rules), extended for the approved scope changes: note features and a second prediction 10 days before the due date (D-050, D-051, D-057, D-059). v1.3 adds the owner's November 26 voice-session decisions on Stage 2 inputs, notes and the IBM split (D-064 to D-068).

This contract defines the data, the targets, the quality requirements and the rules for what may be used at prediction time. It does not select the final models or define application behaviour.

## 1. Datasets and permitted use

| Item | Dataset A: Customer Invoices | Dataset B: IBM Late Payment Histories |
|---|---|---|
| Used for | Stage 1 model (train and test), demo replay | Stage 2 model (train and test), reusability demo |
| Source | Kaggle `pradumn203/payment-date-prediction-for-invoices-dataset` | IBM sample `WA_Fn-UseC_-Accounts-Receivable.csv` |
| Licence | CC BY-NC 4.0; internal demo only | None stated; internal demo only, pending organizer confirmation (Q-001) |
| Size | 50,000 rows, 19 columns | 2,466 rows, 12 columns, 100 customers |
| SHA-256 | `3409441a8ecc48438a0fd42421ce3230d95305f7afcefb732bf232a948b6cf88` | `f5d488eaa4c1cc843b478b6f1068c553c5394aab4b64d587e4b9ad811d845c19` |
| Storage | `data/raw/` only; never in git | `data/raw/` only; never in git |
| Dataset C: synthetic notes | Generated from Dataset B (section 6); stored in `data/generated/`; never in git | |

Licence limits apply to development, demonstration and any distribution.

## 2. Grain and keys

- Dataset A: one row = one invoice, key `doc_id`, unique after cleaning.
- Dataset B: one row = one invoice, key `invoiceNumber`, unique.
- Dataset C: one row = one note, key `note_id`, linked to Dataset B by `customerID` (required); `invoiceNumber` only when the note is about a specific invoice (D-065).

## 3. Targets and labels

- **Late = 1:** paid more than **3 calendar days** after the due date (D-012, D-056). **Not late = 0:** paid on time or within 3 calendar days.
- Labels exist only for paid invoices.
- The 3-day grace period is a business assumption; the data has no grace or reminder field. Sensitivity at 0, 5 and 7 days is reported as supporting analysis only, not as extra labels.
- Changing the grace period changes the target and requires relabelling, retraining and re-evaluation.
- Both stages predict the same target. They differ in scoring time and inputs (section 4).

## 4. Scoring times and feature cut-offs

| Stage | Dataset | Scoring time | Information allowed |
|---|---|---|---|
| Stage 1 | A | The invoice's posting date | Invoice fields; history from the customer's invoices **paid before the posting date** |
| Stage 2 | B | **Due date minus 10 calendar days** | The same inputs as Stage 1, with history **frozen at the invoice date** (invoices paid before the invoice date), plus signals from notes dated **on or before** the Stage 2 scoring date. The notes are the only new information (D-064) |

- No feature may use information unavailable at its stage's scoring time.
- Stage 2 deliberately does not refresh history between the invoice date and the Stage 2 date, so any gain over Stage 1 comes from the notes alone (D-064).
- Stage 2 applies only where the scoring date is on or after the invoice date. All Dataset B invoices have 30-day terms, so it always applies there.

## 5. Column roles

Roles: **input**, **history key** (finds eligible prior invoices; never a raw feature), **outcome** (label and history only; never an input for its own invoice), **event source** (used only to generate notes; never a model input), **split**, **ID**, **masked**, **dropped**.

### Dataset A: Customer Invoices

| Column | Type | Role | Rule |
|---|---|---|---|
| doc_id | integer | ID | Unique after cleaning; join and display only |
| cust_number | string | History key | Never a raw feature |
| name_customer | string | Masked | Replaced with "Customer 0001" and so on; never a feature, never displayed raw |
| posting_date | date | Input / as-of date | Stage 1 scoring time |
| due_in_date | date | Input | Terms and target construction |
| baseline_create_date | date | Input | terms_days = due date minus baseline date |
| total_open_amount | numeric | Input | Must be above 0 |
| cust_payment_terms | category | Input | Fewer than 20 rows → OTHER |
| business_code | category | Input / fairness group | Fewer than 20 rows → OTHER; group-level evaluation reported here |
| invoice_currency | category | Input | Nearly identical to business_code; not a separate fairness group |
| clear_date | date | Outcome | Label and eligible history only |
| isOpen | 0/1 | Split | 0 = paid (train/test), 1 = open (demo replay only) |
| invoice_id, document type, buisness_year, document_create_date, document_create_date.1, posting_id, area_business | various | Dropped | Duplicate, constant, empty, or row filter only (keep RV) |

### Dataset B: IBM Late Payment Histories

| Column | Type | Role | Rule |
|---|---|---|---|
| invoiceNumber | string | ID | Unique; optional link for invoice-specific notes |
| customerID | string | History key | Never a raw feature; required link for notes |
| countryCode | category | Input / fairness group | Group-level evaluation reported here (D-072) |
| InvoiceDate | date | Input | Invoice date |
| DueDate | date | Input | Stage 2 scoring time = DueDate minus 10 days; target construction |
| InvoiceAmount | numeric | Input | Must be above 0 |
| PaperlessBill | category | Input | Known at invoice time |
| Disputed | Yes/No | Event source | Used only to decide which invoices get dispute notes. Never a model input, because the date the dispute was raised is unknown |
| SettledDate, DaysToSettle, DaysLate | date / integer | Outcome | Label and eligible history only |
| PaperlessDate | date | Dropped | Captured by PaperlessBill |

## 6. Notes data rules (Dataset C, synthetic)

Approved by the owner, November 26 (D-065, D-066, D-067). The notes simulate the free-text notes a receivables or service team keeps on a customer account. They are not automatic messages sent to the customer.

| Column | Type | Rule |
|---|---|---|
| note_id | string | Unique |
| customerID | string | Required; must exist in Dataset B |
| invoiceNumber | string | Optional; filled only when the note is about a specific invoice, and must then exist in Dataset B for that customer |
| topic | category | Invoice dispute, claim, missing PO, contact change, payment promise or general query. Set at generation; used to check the note reader, never a model input |
| note_date | date | For an invoice note: between that invoice's date and its Stage 2 scoring date |
| author_role | category | Customer service or receivables analyst |
| channel | category | Call, email or portal |
| note_text | string | Synthetic; no real names. The raw file contains obviously fake personal details (D-088); the masked file does not |

**Which invoices get notes (D-066):**
- Disputed = Yes: always a dispute thread linked to the invoice.
- Disputed = No: 67% get no notes; 33% get a generic note (claim, missing PO, contact change, payment promise or general query).
- One in five generic notes reads like a dispute (a query that was raised and resolved), so a dispute-sounding note does not always mean a flagged dispute.

**Generation rules (blind generation):**
1. Notes never create or change an outcome. Late or on time always comes from Dataset B.
2. The generator sees only: invoiceNumber, customerID, InvoiceDate, DueDate, InvoiceAmount, PaperlessBill and Disputed. Outcome columns are removed in code before generation.
3. Notes describe real events only, using the mix above.
4. Realistic contradictions are added: resolved disputes, frustrated customers who pay on time, routine notes on invoices that end up late.
5. The note reader (LLM extraction) is checked against the topic labels set at generation, and also on Bitext's labelled requests.
6. When scoring an invoice, only that customer's notes dated on or before the invoice's Stage 2 scoring date are used.
7. Leakage alarm: if Stage 2 looks near-perfect, generation is checked for leaks. A modest gain over Stage 1 is expected.
8. Every reported Stage 2 result is labelled as using synthetic notes anchored to real dispute events.

**Personal details and masking (D-088):**
1. Generated notes include obviously fake personal details: contact names from a fixed fake list, `@example.com` emails, `555` phone numbers, and reference numbers.
2. A rules-based masking step (regular expressions plus the customer's fake contact list, no LLM) writes a second file. Names become one-way stand-ins such as "Contact 017", made from a salted hash, so the same person always gets the same label. Emails, phones and references become `[EMAIL]`, `[PHONE]` and `[REF]`. No lookup table is kept.
3. `customerID`, `invoiceNumber` and `note_id` are never masked: they are the join keys.
4. Two files: `notes_raw` (restricted; never read by the note reader or the app) and `notes_masked` (used by everything downstream).
5. The masking rules live in `config/masking.yaml`, so a client can add its own patterns without changing code.
6. Rule N6 stops the pipeline if anything that looks like personal data survives masking.

The extracted signals (D-074) and the extraction prompt are defined in `specs/note_features.md`, not here.

## 7. Customer history

Applies to both datasets, using each stage's cut-off from section 4.

1. Use only the same customer's invoices paid before the stage's scoring time.
2. Never use the current invoice's clear date, label, days late, or any future outcome.
3. Keep the count of eligible prior paid invoices as a feature.
4. A customer with no eligible history must not get an average lateness of 0; history availability is explicit.
5. **History groups (D-061):** none = 0 prior paid invoices, limited = 1 to 4, enough = 5 or more. Evidence: `notebooks/02_history_profile.ipynb`.
6. Candidate measures: prior late share, average days late, prior late count, recency, variability. Exact definitions and lookback windows go in the feature spec (gate G2).
7. Average days late is capped at ±90 days at feature time.
8. Model performance is reported separately for each history group.

## 8. Quality rules

Applied in this order. Row counts affected by each rule are logged. Any rule marked Fail stops the pipeline.

### Dataset A

| # | Rule | Action | Rows affected |
|---|---|---|---|
| Q1 | Exact duplicate rows | Drop | 1,161 |
| Q2 | Same doc_id with different values | Fail | 0 |
| Q3 | Document type other than RV | Drop | 6 |
| Q4 | Required field missing (doc_id, cust_number, posting_date, due date, baseline date, amount) | Fail | 0 |
| Q5 | Date fails to parse | Fail | 0 |
| Q6 | Due date before invoice date | Drop and log | 131 |
| Q7 | Clear date before invoice date | Fail | 0 |
| Q8 | Paid without clear date, or open with one | Fail | 0 |
| Q9 | Amount at or below 0 | Fail | 0 |
| Q10 | Payment terms outside 0 to 120 days | Fail | 0 |
| Q11 | Column more than 95% missing, or 99.9% one value | Drop column | area_business, posting_id |
| Q12 | Category with fewer than 20 rows | Group into OTHER | 40 payment-term codes; U005, U007 |
| Q13 | History average days late | Cap at ±90 days | At feature time |

### Dataset B

The same rules apply where the columns exist (Q2, Q4, Q5, Q7, Q9). Checked in `notebooks/03_ibm_split.ipynb`: 2,466 unique invoices, no missing values, no settled date before the invoice date, no amount at or below 0. Nothing is dropped.

### Dataset C

| # | Rule | Action |
|---|---|---|
| N1 | Note's customerID doesn't exist, or its invoiceNumber doesn't exist for that customer | Fail |
| N2 | Invoice note dated after that invoice's Stage 2 scoring date or before its invoice date | Fail |
| N3 | Generator input contains an outcome column | Fail |
| N4 | Note text contains a real company or person name | Fail |
| N5 | Generated mix differs from section 6 (every disputed invoice has a dispute thread; about 33% of undisputed invoices have a note) | Fail |
| N6 | The masked file still contains an email, a phone number, a reference pattern or a name from the contact list | Fail |

## 9. Dataset splits

| Set | Rows | Late rate (3-day grace) | Permitted use |
|---|---|---|---|
| A: all clean invoices | 48,702 | | Profiling |
| A: paid | 39,048 | 14.7% (5,757 late) | Labelled population |
| A: train (posted before Oct 1, 2019) | 26,522 | 15.3% | Stage 1 training |
| A: test (posted Oct 1, 2019 onward) | 12,526 | 13.5% | Stage 1 evaluation |
| A: replay (open) | 9,654 | No outcome | Demo only; never in any metric |
| B: all invoices | 2,466 | 28.4% | Labelled population |
| B: train (invoice date before Jul 1, 2013) | 1,930 | 30.3% (585 late) | Stage 2 training |
| B: test (invoice date Jul 1, 2013 onward) | 536 | 21.5% (115 late; 122 disputed) | Stage 2 evaluation |

Splits are chronological, never random, and change only through an approved decision (D-063, D-068). For Dataset B, scikit-learn `TimeSeriesSplit` (5 folds) is a second check that patterns hold over time: disputed invoices are late 44% to 66% of the time in every fold, undisputed 15% to 21% (`notebooks/03_ibm_split.ipynb`).

## 10. Leakage and prediction-time rules

1. Clear date, days late and the label are never features for the same invoice.
2. History uses only invoices paid before the stage's scoring time.
3. No feature uses information unavailable at the stage's scoring time.
4. The Disputed flag is never an input to a deployed model; its only input use is the evaluation-only ceiling model (D-073).
5. Primary evaluation uses a time-based split, never random.
6. Open invoices are never in accuracy, precision, recall, PR-AUC or calibration calculations.
7. Automated tests enforce rules 1 to 6 on every pipeline run.

## 11. Confidentiality

- Raw customer names never appear in the application, deck, notebook outputs or logs.
- No raw or generated data in git.
- Masked labels in every user-facing view.
- Customer identifiers and invoice-level data are not shared beyond the approved demo audience and purpose.

## 12. G1 decisions

- [x] Grace period of 3 calendar days (D-012, D-056)
- [x] History groups 0 / 1-4 / 5+ (D-061)
- [x] Two models: Stage 1 on Dataset A, Stage 2 on Dataset B (D-059)
- [x] Dataset A column roles, quality rules Q1 to Q13 and the October 1, 2019 split (D-063)
- [x] Stage 2 inputs: Stage 1 inputs with history frozen at the invoice date, plus note signals only (D-064)
- [x] Notes data rules in section 6: customer-level link, topic, generation mix (D-065, D-066, D-067)
- [x] Dataset B split at July 1, 2013 (D-068)
- [x] Dataset B column roles, including Disputed as event source only (D-062, D-070)
- [x] Scoring times in section 4: posting date (Stage 1) and due date minus 10 calendar days (Stage 2) (D-062)
- [x] IBM fairness group = countryCode (D-072)
- [x] Comparison models on Dataset B, evaluation only: Model A without notes (D-071) and a ceiling model with the Disputed flag as a direct input (D-073). The ceiling model is the only permitted use of Disputed as an input, it is never deployed, and it is always labelled as a ceiling

## Change log

| Date | Change |
|---|---|
| Nov 26, 2026 | v1: first draft |
| Nov 26, 2026 | v1.1 (owner): feature eligibility, history coverage, prediction-time rules |
| Nov 26, 2026 | v1.2: Stage 2 and notes added; Dataset B and C contracts; scoring times; history groups; calendar days |
| Nov 26, 2026 | v1.3 (owner-approved changes from the voice session): Stage 2 history frozen at invoice date; notes linked by customer with topic and generation mix; section 6 renamed Notes data rules; N5 added; IBM SHA, quality check results and split counts |
| Nov 26, 2026 | v1.4: G1 closed. Dataset B roles, scoring times, countryCode fairness group approved; Model A and ceiling model added as evaluation-only comparisons; leakage rule 4 clarified |
| Nov 27, 2026 | v1.5: fake personal details in generated notes, rules-based one-way masking, raw and masked files, rule N6 (D-088) |
