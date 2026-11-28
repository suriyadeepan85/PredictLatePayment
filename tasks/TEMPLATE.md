# T-### <short title>

<!-- A task brief must be understandable on its own, without any conversation history (methodology 5.4). -->

| Field | Value |
|---|---|
| Agent | e.g. DevOps Engineer |
| Risk | high (infrastructure, security, data handling, reported metrics) / normal |
| Status | CREATED → READY → ASSIGNED → IN_PROGRESS → REVIEW → COMPLETED (or BLOCKED / FAILED / REJECTED) |
| Depends on | T-### |

## Objective
One or two sentences.

## Read only these (context package)
- `specs/<file>.md` sections N, M
- `DECISIONS.md` records D-###, D-###
- Files to change: `path/…`

## Must not
- Change anything outside the files listed above
- Change an approved spec or decision (raise a question instead)

## Acceptance criteria (copied from the spec, not invented)
- [ ] …

## Evidence to hand back
Files changed, commands run, test results, for infrastructure the `terraform plan` summary, known limits, open questions.
