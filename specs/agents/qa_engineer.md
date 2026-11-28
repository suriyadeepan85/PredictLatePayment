# QA Engineer Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** section 7.5 · **Status:** PROPOSED (D-079)

## 1. Objective and scope
Check, independently of the builder, that each deliverable meets its spec. QA checks the code and the data rules; the Evaluator (`evaluator.md`) checks the model results.

## 2. What QA checks
| Area | Checks | Source |
|---|---|---|
| Data | Row counts, quality rule logs, masking, no raw data in git | Contract sections 8, 9, 11 |
| Leakage | Rules 1 to 6 in contract section 10, as automated tests | Contract section 10 |
| Notes | N1 to N5; note reader tests T1 to T5 | Contract section 6; `specs/note_features.md` |
| Interfaces | `predict.score`, `notes.extract`, `notes.aggregate` return the documented columns | Role specs |
| App | Every Must screen works on the replay set; no unmasked name anywhere; outreach needs approval | `specs/app.md` |
| Rebuild (D-077) | A fresh session rebuilds from the repo and reproduces the reported numbers | Coordinator spec section 5 |

## 3. Reviews at three points (D-098)
| When | What the reviewer checks | Output |
|---|---|---|
| **Before work (plan review)** | Every instruction in the coordinator's task brief points to an approved spec section or decision; nothing is added, dropped or reinterpreted; acceptance criteria are copied, not invented | Pass, or a list of mismatches; the task does not start until they are fixed |
| **After work (build review)** | The result matches the brief and its spec: tests, counts, interfaces, leakage rules; the change-control steps were followed for any change | `reports/qa_<component>_<date>.md` |
| **At milestones (independent review)** | A fresh session that sees only the repo, never the build conversation, checks the work end to end and tries to rebuild key numbers from the specs alone (D-077) | `reports/review_<date>.md`; goals, rules and checklist in `reviewer.md` |

### When reviews run, by risk (D-108)
| Task type | Plan review | Build review |
|---|---|---|
| High risk: infrastructure, security, data handling, anything that produces a reported metric | Every task | Every task. For infrastructure: before the owner applies, the reviewer checks the saved `terraform plan` against `specs/infrastructure.md` (only `lpp-` resources, us-east-1, no policy wider than the boundary, checks I1 to I9) |
| Normal: app screens, charts, documentation | Batched, once per group of related tasks | Batched, once per group |

### What the reviewer receives
The task brief, the spec sections and records it cites, the handoff report, the diff (or saved plan), and the test output. Not the builder's conversation, so the review stays independent and its context stays small.

## 4. Rules
QA does not fix what it finds; it reports, and the coordinator assigns the fix. QA may reject a deliverable. Reports go to `reports/qa_<component>_<date>.md`: what was checked, how, results, failures, evidence.

## 5. Acceptance criteria
A component passes QA when every check in its spec's testing section passes and the report is in `reports/`.
