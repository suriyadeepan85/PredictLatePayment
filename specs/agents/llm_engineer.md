# LLM Engineer Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** section 7.3 · **Status:** PROPOSED (D-079)

## 1. Objective and scope
Build the two LLM features and, for the hackathon, the Streamlit app that shows them.

| Feature | Spec | Priority |
|---|---|---|
| Note reader: notes → signals S1 to S7 | `specs/note_features.md` (signals APPROVED, D-074) | Must |
| Outreach draft: a polite pre-due reminder for a high-risk invoice | `specs/app.md` (to be written) | Should (D-030) |
| Streamlit app screens | `specs/app.md` | Must: control panel, risk dashboard, invoice detail, model evidence |

## 2. Inputs
Note text from Dataset C; risk scores and reasons from `src/model/predict.py`; masked customer labels only.

## 3. Rules
1. The AI drafts, a person approves, nothing is sent automatically, every draft is logged (D-031).
2. Prompts never contain real names, outcomes, or the Disputed flag.
3. Model: Claude Haiku 4.5 on Bedrock, temperature 0 for the note reader. Bedrock depends on Q-001 and Q-003; until they're answered, a rules-based reader and a template draft stand in, with the same interfaces.
4. Every LLM output is checked against a fixed JSON schema before use.
5. Prompts live in `src/features/prompts/` and `app/prompts/` as text files under version control.

## 4. Deliverables
`src/features/notes.py`, `app/outreach.py`, `app/streamlit_app.py`, prompts, tests, `notebooks/05_note_features.ipynb`.

## 5. Acceptance criteria
- Note reader: tests T1 to T5 in `specs/note_features.md` pass.
- Outreach: every draft names the invoice, amount and due date correctly, contains no threat or legal language, and is shown for approval before anything else happens.
- App: works on the demo replay set without errors; every customer is shown masked.

## 6. Handoff
As in the coordinator spec, section 9, plus sample outputs: 10 notes with their extracted signals, and 3 outreach drafts.
