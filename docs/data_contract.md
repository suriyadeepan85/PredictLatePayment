# Data Contract v1: Customer Invoices (Stage 1)

**Status:** draft for gate G1 review · **Date:** November 26, 2026 · **Owner:** Suriyadeepan Narayanasamy

This contract defines what one row means, what each column may be used for, what "late" means, and the quality rules the data must pass before any model trains. Every later step (features, model, fairness check, app) reads the data through this contract.

## 1. Source

| Item | Value |
|---|---|
| Dataset | Customer Invoices (Kaggle: `pradumn203/payment-date-prediction-for-invoices-dataset`) |
| Licence | CC BY-NC 4.0 (non-commercial use; internal demo only) |
| File | `dataset.csv`, 50,000 rows, 19 columns |
| SHA-256 | `3409441a8ecc48438a0fd42421ce3230d95305f7afcefb732bf232a948b6cf88` |
| Storage | Local `data/raw/` only. Never committed to git |

## 2. Grain

One row = one invoice, identified by `doc_id`. After the quality rules in section 5, `doc_id` is unique.

## 3. Label

- **Late** = `clear_date` is more than **3 days** after the due date (`grace_days: 3`, set in config).
- The label exists only for paid invoices (`isOpen = 0`).
- 3 days is a business assumption, not a fact from the data (the dataset has no grace or reminder field). Results will also be reported at 0, 5 and 7 days.

## 4. Column roles

Roles: **input** (model feature), **history key** (builds features from earlier invoices only), **outcome** (label and history only, never an input for its own invoice), **split** (paid vs open only), **ID** (join and display), **masked** (display only, replaced by a neutral label), **dropped**.

| Column | Type | Role | Rule |
|---|---|---|---|
| doc_id | integer | ID | Unique after cleaning; join and display only |
| cust_number | string | History key | Builds history as of the invoice date; never a raw input |
| name_customer | string | Masked | Shown as "Customer 0001" and so on, mapped from `cust_number`; never an input, never displayed raw |
| posting_date | date | Input (as-of date) | Invoice date; all history uses only invoices paid before this date |
| due_in_date | date (YYYYMMDD) | Input | Due date; used for terms and for computing lateness |
| baseline_create_date | date (YYYYMMDD) | Input | Start of payment terms; terms_days = due date minus baseline date |
| total_open_amount | float | Input | Must be above 0 |
| cust_payment_terms | category | Input | Codes with fewer than 20 rows grouped into OTHER |
| business_code | category | Input and fairness group | Codes with fewer than 20 rows grouped into OTHER; fairness reported by this column |
| invoice_currency | category | Input | Nearly identical to business_code (2 rows differ); kept as input, not used as a separate fairness group |
| clear_date | date | Outcome | Label and history only; never an input for its own invoice |
| isOpen | 0/1 | Split | 0 = paid (train and test), 1 = open (demo replay) |
| invoice_id | integer | Dropped | Duplicate of doc_id |
| document type | category | Dropped (after row filter) | Only RV rows kept |
| buisness_year | integer | Dropped | Already in posting_date |
| document_create_date | date | Dropped | Same as posting_date |
| document_create_date.1 | date | Dropped | Same as posting_date |
| posting_id | integer | Dropped | Constant |
| area_business | float | Dropped | 100% empty |

## 5. Quality rules

Applied in this order. Each run logs how many rows each rule removed. Any failure on the checks marked "fail" stops the pipeline.

| # | Rule | Action | Rows affected (this file) |
|---|---|---|---|
| Q1 | Exact duplicate rows | Drop | 1,161 |
| Q2 | Same doc_id with different values | Fail | 0 |
| Q3 | Document type other than RV | Drop | 6 |
| Q4 | Required field missing (doc_id, cust_number, posting_date, due date, baseline date, amount) | Fail | 0 |
| Q5 | Date fails to parse | Fail | 0 |
| Q6 | Due date before invoice date | Drop and log | 131 |
| Q7 | Clear date before invoice date | Fail | 0 |
| Q8 | Paid invoice without a clear date, or open invoice with one | Fail | 0 |
| Q9 | Amount at or below 0 | Fail | 0 |
| Q10 | Payment terms outside 0 to 120 days | Fail | 0 |
| Q11 | Column more than 95% missing, or 99.9% one value | Drop column | area_business, posting_id |
| Q12 | Category with fewer than 20 rows | Group into OTHER | 40 payment-term codes; business units U005, U007 |
| Q13 | History averages of days late | Cap at ±90 days | Applied at feature time |

## 6. Result after cleaning

| Set | Rows | Late rate (3-day grace) | Use |
|---|---|---|---|
| All clean invoices | 48,702 | | |
| Paid | 39,048 | 14.7% (5,757 late) | |
| Train: paid, posted before Oct 1, 2019 | 26,522 | 15.3% | Model training |
| Test: paid, posted Oct 1, 2019 onward | 12,526 | 13.5% | All accuracy and fairness numbers |
| Replay: open | 9,654 | none (no outcome) | Demo only, never for accuracy |

Customers: 1,423.

## 7. Leakage rules

1. No outcome column (`clear_date`, days late, label) is ever an input for its own invoice.
2. History features for an invoice use only invoices **paid before that invoice's posting date**.
3. The split is by time, never random.
4. Open invoices never contribute to accuracy.
5. Tests enforce rules 1 to 3 on every run.

## 8. Confidentiality rules

- Customer names never appear in the app, the deck, notebook outputs or logs.
- No raw data in git.

## 9. Decisions for G1

- [ ] Grace period of 3 days (decided November 26)
- [ ] Column roles in section 4
- [ ] Quality rules in section 5, including dropping 131 invoices due before their invoice date
- [ ] Time split at October 1, 2019

## Change log

| Date | Change |
|---|---|
| Nov 26, 2026 | v1 draft for G1 |
