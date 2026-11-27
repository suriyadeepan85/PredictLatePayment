# Data Engineer Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** section 7.2 · **Status:** PROPOSED (D-079)

## 1. Objective and scope
Turn the raw files into clean, checked tables exactly as the data contract says, and generate the synthetic notes.

## 2. Inputs
`data/raw/customer_invoices.csv` and `data/raw/ibm_ar.csv`, verified by the SHA-256 values in contract section 1. If a hash doesn't match, the pipeline stops.

## 3. Work
| Step | Rule source | Output |
|---|---|---|
| Load and verify A and B | Contract sections 1, 2 | |
| Quality rules Q1 to Q13 (A) and the B checks, with logged row counts | Contract section 8 | `data/clean/a.parquet`, `data/clean/b.parquet` |
| Labels at 3 calendar days | Contract section 3 | `late` column |
| Splits | Contract section 9 (A: Oct 1, 2019; B: Jul 1, 2013) | `set` column: train / test / replay |
| Customer name masking | Contract section 11 | "Customer 0001" labels; raw names dropped |
| History tables as of each cut-off | Contract section 7 | Input to the feature step |
| Note generation (blind) | Contract section 6, mix in D-066 | `data/generated/notes.csv`; checks N1 to N5 |

## 4. Rules
Never change a rule from the contract; raise a question in `OPEN_ITEMS.md` instead. Raw, clean and generated data never go into git. The note generator receives only the columns listed in contract section 6 rule 2; the code drops everything else before the call.

## 5. Deliverables
`src/data/load.py`, `src/data/clean.py`, `src/data/notes_generate.py`, tests, and the notebooks `01` to `03` importing these modules.

## 6. Acceptance criteria
- Row counts match contract section 9 exactly (A: 48,702 clean, train 26,522, test 12,526, replay 9,654; B: train 1,930, test 536).
- Every quality rule logs its count; any Fail rule stops the pipeline.
- No raw customer name appears in any output.
- N1 to N5 pass on the generated notes.
