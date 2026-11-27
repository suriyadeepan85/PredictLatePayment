# Component Spec: Note Features (Stage 2)

**Version:** 0.1 · **Date:** November 26, 2026 · **Owner:** Suriyadeepan Narayanasamy · **Builder role:** LLM Engineer (Claude in the hackathon build)
**Status:** Signal list APPROVED (D-074). Every other section is PROPOSED until the owner approves it.

## 1. Objective and scope
Turn the free-text account notes in Dataset C into a small set of structured signals that Model B (Stage 2) uses as inputs, alongside the Stage 1 inputs.

In scope: the signal definitions, the extraction prompt and output format, aggregation to invoice level, validation of the note reader.
Out of scope: generating the notes (`docs/data_contract.md` section 6), model training (ML spec), outreach drafting (app spec).

## 2. Inputs and dependencies
| Input | Source | Rule |
|---|---|---|
| Notes | Dataset C, `data/generated/notes.csv` | Contract section 6; quality rules N1 to N5 must pass first |
| Invoices | Dataset B | `invoiceNumber`, `customerID`, `DueDate` only |
| Stage 2 scoring date | Contract section 4 | DueDate minus 10 calendar days |

Depends on: data contract v1.4 (APPROVED), note generation (built from contract section 6).

## 3. Signals (APPROVED, D-074)
Extracted per note by the LLM, then combined for each invoice using only that customer's notes dated on or before the invoice's Stage 2 scoring date.

| # | Signal | Level | Values | If there is no note |
|---|---|---|---|---|
| S1 | Open dispute, and its reason | Invoice | yes / no; reason: wrong amount, duplicate charge, pricing, goods or service issue, other | no_note |
| S2 | Missing PO or wrong contact | Invoice | yes / no | no_note |
| S3 | Promise to pay, and the promised date | Invoice | yes / no; date | no_note |
| S4 | Escalation requested | Invoice | yes / no | no_note |
| S5 | Contacts in the last 30 days | Customer | count, 0 or more | 0 |
| S6 | Tone of the latest note | Customer | positive / neutral / negative | no_note |
| S7 | Open claim on the account | Customer | yes / no | no_note |

"No note" stays a separate value and is never treated as "no". A customer with no notes is not the same as a customer whose notes say there is no problem.

## 4. Technical requirements (PROPOSED)
1. Note reader: Claude Haiku 4.5 on Bedrock, temperature 0, one call per note. Notes are cached by `note_id`, so reruns cost nothing and give the same output.
2. The output is JSON checked against a fixed schema (the section 3 fields). If the output is invalid, retry once; if it is still invalid, log the note and set its signals to unknown.
3. The reader sees only `note_text`, `note_date` and `author_role`. It never sees the topic label, the Disputed flag or any outcome.
4. How invoice notes and customer notes combine: an invoice's S1 to S4 come from notes linked to that invoice. S5 to S7 come from all of the customer's notes up to the cut-off. If a later note says a dispute is resolved, S1 becomes no.
5. How the promised date is turned into a model input (for example days between the promised date and the due date) is set in the G2 feature spec.
6. For offline development, a rules-based reader with the same output format can stand in for the LLM.

## 5. Interface (PROPOSED)
- `src/features/notes.py`: `extract(notes_df) -> signals_df` (one row per note) and `aggregate(signals_df, invoices_df) -> features_df` (one row per invoice, columns `s1_open_dispute` … `s7_open_claim`).
- Output file: `data/generated/note_signals.parquet`, never committed.
- Notebook: `notebooks/04_note_features.ipynb` runs extraction on a sample, shows the signal distributions, and runs the section 7 checks.

## 6. Constraints
- No real names in prompts, outputs or logs.
- Signals from notes dated after an invoice's Stage 2 scoring date are never used.
- Bedrock use depends on Q-003 (credits) and Q-001 (account approval). Until those are answered, the rules-based reader is used.

## 7. Testing requirements (PROPOSED)
| Test | Pass condition |
|---|---|
| T1 Schema | 100% of outputs parse into the section 3 fields |
| T2 Topic check | S1 agrees with the generator's topic label on at least 90% of dispute-topic notes; at most 10% false "yes" on non-dispute notes. The dispute-like generic notes are reported separately |
| T3 Cut-off | No signal uses a note dated after the invoice's Stage 2 scoring date |
| T4 No leak | The reader's inputs contain no outcome column, no Disputed flag and no topic label |
| T5 Repeatability | Rerunning on the same notes gives identical signals |

## 8. Acceptance criteria
- T1 to T5 pass.
- On the IBM test set, Model B is evaluated alongside Model A (D-071) and the ceiling model (D-073), all on the same invoices.
- A near-perfect Model B triggers the leakage check in contract section 6, rule 7.

## 9. Deliverables
`src/features/notes.py`, `tests/test_notes.py`, `notebooks/04_note_features.ipynb`, the extraction prompt in `src/features/prompts/note_reader.txt`, and a short test report in `reports/`.

## 10. Open issues and assumptions
- A-006: disputes are raised before the Stage 2 day.
- Q-003: Bedrock credits.
- The dispute reasons in S1 must match the reasons the note generator uses. To be confirmed when the generator is built.

## Change log
| Date | Change |
|---|---|
| Nov 26, 2026 | v0.1: seven signals approved (D-074); other sections proposed |
