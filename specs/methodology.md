# Development Methodology: Conversation-to-Specification

**Status:** APPROVED by the owner on November 26, 2026 (lean version of the owner's proposal).

## Why
Chat sessions get long, get overwritten and lose context. Decisions get buried. This process turns conversation into persistent, traceable records in the repo, so any new session can continue from files instead of chat history.

## Three layers
1. **Conversation:** discussion, questions, experiments, alternatives. Not authoritative.
2. **Knowledge and decisions:** `DECISIONS.md` (decisions and observations) and `OPEN_ITEMS.md` (questions and assumptions). Every record has a status, an owner and evidence.
3. **Specification:** `specs/` and `docs/data_contract.md`. Authoritative for implementation. Changes only through APPROVED records.

## Record format
| Field | Meaning |
|---|---|
| ID | D-### (decision or observation), Q-### (question), A-### (assumption) |
| Type | decision, observation, question, assumption |
| Statement | One sentence |
| Status | PROPOSED, APPROVED, REJECTED, SUPERSEDED, OPEN (questions and assumptions), RESOLVED |
| Proposed by | Owner or Claude |
| Approved | Who and when, or blank |
| Evidence | File path, or a dated quote of the owner. Never a chat link |
| Supersedes | Earlier record ID, if any |

## Governance
- Claude records only as PROPOSED. The owner approves, rejects or supersedes.
- The process keeps apart what was discussed, what the data showed (observations), what Claude recommended, what the owner approved, and what is still open.
- Specs change only after the owner approves the record behind the change.

## Timing (hybrid)
- **During a session:** capture records as they come up; update a spec as soon as its record is approved.
- **End of session:** reconcile records, update `STATUS.md`, list items waiting for approval, commit and push.
- **Start of session:** read `STATUS.md` and `OPEN_ITEMS.md`; confirm the current gate with the owner.

## Simplifications from the original proposal
- Three files instead of five: `CONVERSATION_SUMMARY.md` dropped (goes stale, duplicates the decision log); questions and assumptions merged into `OPEN_ITEMS.md`.
- Evidence points to files, not chat.

## Later (full build)
A Coordinator Agent takes over extraction, decision tracking, spec updates, versioning and session handoffs.
