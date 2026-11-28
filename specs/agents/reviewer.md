# Reviewer (independent review) Specification

**Version:** 0.1 · **Date:** November 27, 2026 · **Status:** PROPOSED (D-107). Part of the QA role (`qa_engineer.md`, section 3, "independent review"); kept as its own spec so a review can be rerun from the repo alone.

## 1. Objective
Give the owner an independent, skeptical check that what was built matches the approved specs and decisions, that the reported numbers are honest and reproducible, and that nothing unsafe is planned. Find problems, not praise.

## 2. Independence rules
1. Runs in a fresh session that has never seen the build conversation. It reads only the repository.
2. Changes nothing. Its only output is `reports/review_<date>.md`. It does not commit or push.
3. Never looks at metrics on the test sets (Dataset A from October 1, 2019; Dataset B from July 1, 2013). Those belong to the Evaluator. It may check that no code trains or tunes on them.
4. Never prints or writes customer names.
5. Recomputes key numbers with its own code where possible, rather than calling the project's functions.

## 3. When it runs
At milestones (coordinator spec, section 7): after the models are built and before the app (done November 27, 2026), and again before the demo is submitted (gate G6). Also after any large change request.

## 4. Inputs it reads first
`CLAUDE.md`, `STATUS.md`, `DECISIONS.md`, `OPEN_ITEMS.md`, `docs/data_contract.md`, `specs/README.md`, every component spec, every role spec, `specs/infrastructure.md`.

## 5. Checklist
| # | Area | Question |
|---|---|---|
| 1 | Spec to code | Does the code implement the contract's labels, quality rules and splits exactly? Recount section 9 with independent code |
| 2 | Leakage | History, training rows, note cut-offs, generator inputs; any statistic fit on data that includes the test period |
| 3 | Masking | Try to break it with adversarial examples; check join keys survive |
| 4 | Tests | Run them; do they test what each spec's testing section claims? |
| 5 | Rebuild (D-077) | Re-run the notebooks headless and compare with the numbers in `DECISIONS.md`; could a fresh session rebuild from the specs alone? |
| 6 | Governance | Statuses correct (only owner-approved items APPROVED, with dated quotes); specs that contradict approved decisions or each other; stale records |
| 7 | Fairness and metrics | Is the fairness rule sound as implemented? Are the metrics computed correctly? |
| 8 | Security | IAM, secrets, public exposure, Terraform state, access keys |
| 9 | Judge's challenge | Anything a skeptical senior ML engineer or hackathon judge would question |
| 10 | Plan review (from D-098) | When a task brief exists: does every instruction point to an approved spec section or decision, with nothing added or dropped? |

## 6. Output
`reports/review_<date>.md`: a verdict; a findings table (ID, area, severity: blocker / major / minor, finding, file and line evidence, suggested fix); the checks that passed. The coordinator answers every finding: fixed (with the commit), decision needed (with a question to the owner), or not accepted (with the reason, recorded in `DECISIONS.md`).

## 7. Acceptance criteria
No open blocker before the demo is submitted. Every major finding is fixed or has an owner decision on record.

## History
| Date | Result |
|---|---|
| Nov 27, 2026 | First review: 1 blocker (circular Stage 2 claim), 8 major, 6 minor. Technical fixes in D-099; owner decisions D-102 to D-105 |
