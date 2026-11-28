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
| Notes | Dataset C, masked file `data/generated/notes_masked.csv` | Contract section 6; quality rules N1 to N6 must pass first. The reader never sees the raw file (D-088) |
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
1. Note reader: Claude Haiku 4.5 on Bedrock, temperature 0, one call per note. It runs once, as a step in the SageMaker Pipeline (D-084); its output is saved and reused, and nothing calls it when a judge uses the app. Notes are cached by `note_id`, so reruns cost nothing and give the same output.
2. The output is JSON checked against a fixed schema (the section 3 fields). If the output is invalid, retry once; if it is still invalid, log the note and set its signals to unknown.
3. The reader sees only the masked `note_text`, `note_date` and `author_role`. It never sees the topic label, the Disputed flag or any outcome.
4. How invoice notes and customer notes combine: an invoice's S1 to S4 come from notes linked to that invoice. S5 to S7 come from all of the customer's notes up to the cut-off. If a later note says a dispute is resolved, S1 becomes no.
5. How the promised date is turned into a model input (for example days between the promised date and the due date) is set in the G2 feature spec.
6. For offline development, a rules-based reader with the same output format can stand in for the LLM.

## 4b. Note generator settings (for a rebuild)
`src/data/notes_generate.py`, `generate_notes(invoices, seed=42, generic_share=0.33, dispute_like_share=0.2, late_noted_share=0.3, reason_stated_share=0.7)`:
- 1 to 3 fake contacts per customer.
- Dispute thread (every disputed invoice): an opener from six varied wordings; the reason stated in natural words in 70% of threads; then 0 to 2 more notes (thread length 1, 2 or 3 with probabilities 0.5, 0.3, 0.2), each a follow-up (0.6), escalation (0.2) or resolution (0.2, ends the thread). In 30% of threads all notes fall after the Stage 2 date, up to the due date (D-104).
- Routine notes (any invoice, disputed or not, D-109): with probability 0.33, a burst of 1, 2 or 3 notes (same probabilities); each is dispute-like but resolved with probability 0.2, otherwise a claim, missing PO, contact change, payment promise or general query (equally likely). Two general-query wordings look like disputes ("on hold", "pushed back") to test the reader.
- Personal details appended with probabilities 0.7 (name), 0.3 (email), 0.2 (phone), 0.3 (case reference).

## 5. Interface (PROPOSED)
- `src/features/notes.py`: `extract(notes_df, reader="rules"|"llm") -> signals_df` (one row per note) and `aggregate(notes_df, signals_df, invoices_df) -> features_df` (one row per invoice; columns and encodings in `specs/features.md`, "Note signal encodings").
- Output files: `data/generated/note_signals.csv` and `note_features.csv`, never committed.
- Notebook: `notebooks/05_note_features.ipynb` runs extraction on a sample, shows the signal distributions, and runs the section 7 checks.

## 6. Constraints
- No real names in prompts, outputs or logs.
- Signals from notes dated after an invoice's Stage 2 scoring date are never used.
- Bedrock use depends on Q-003 (credits) and Q-001 (account approval). Until those are answered, the rules-based reader is used.

## 7. Testing requirements (PROPOSED)
| Test | Pass condition |
|---|---|
| T1 Schema | 100% of outputs parse into the section 3 fields |
| T2 Topic check | At invoice level: at least 90% of invoices with a generated dispute thread get a dispute signal, and at most 10% of invoices without one get an open-dispute signal. Measured at invoice level because follow-up notes in a thread often don't repeat the word "dispute" (note level reported for information) |
| T3 Cut-off | No signal uses a note dated after the invoice's Stage 2 scoring date |
| T4 No leak | The reader's inputs contain no outcome column, no Disputed flag and no topic label (`tests/test_contract_and_leakage.py`) |
| T5 Repeatability | Rerunning on the same notes gives identical signals (`tests/test_contract_and_leakage.py`) |

## 8. Acceptance criteria
- T1 to T5 pass.
- On the IBM test set, Model B is evaluated alongside Model A (D-071) and the ceiling model (D-073), all on the same invoices.
- A near-perfect Model B triggers the leakage check in contract section 6, rule 7.

## 9. Deliverables
`src/features/notes.py`, `tests/test_notes.py`, `notebooks/05_note_features.ipynb`, the extraction prompt in `src/features/prompts/note_reader.txt`, and a short test report in `reports/`.

## 10. Open issues and assumptions
- A-006: disputes are raised before the Stage 2 day.
- Q-003: Bedrock credits.
- The dispute reasons in S1 must match the reasons the note generator uses. To be confirmed when the generator is built.

## Change log
| Date | Change |
|---|---|
| Nov 26, 2026 | v0.1: seven signals approved (D-074); other sections proposed |
| Nov 27, 2026 | v0.2: reader works on the masked notes; runs as a pipeline step |
| Nov 27, 2026 | Built: rules-based reader, Haiku reader code (untested until Bedrock access), aggregation, tests T1, T3, T5 in `tests/test_notes.py`; notebook 05 |
| Nov 27, 2026 | v0.3 after the independent review: interface and outputs match the code (R-13); generator settings written out (R-06); T2 measured at invoice level; T4 and T5 automated (R-07) |
| Nov 28, 2026 | v0.4 after the Stage 2 review: generator settings updated (late-noted disputes, varied wording, thread and routine counts); diagnostic column `dx_any_dispute_read` (not a model input) |
