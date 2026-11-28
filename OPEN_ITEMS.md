# Open questions and assumptions

Format and rules: `specs/methodology.md`. Seeded November 26, 2026.

## Questions

| ID | Question | Status | Owner | Blocks |
|---|---|---|---|---|
| Q-001 | Do the organizers accept the dataset licences (CC BY-NC, and IBM with no stated licence) and use of personal AWS and Claude accounts? | OPEN | Owner (email sent?) | Presenting |
| Q-002 | Must the working application be hosted, or can it run on the owner's laptop? | OPEN | Owner | Whether AWS becomes a must |
| Q-003 | Do the AWS credits cover Claude on Bedrock? | OPEN | Owner | Outreach draft only |
| Q-004 | What business-case figure can be shared (share of invoices paid late, cost per account in collections)? | OPEN | Owner | Deck |
| Q-005 | Add results at 0, 5 and 7 days of grace to the evaluation? | OPEN | Owner | G3 |
| Q-006 | Update spec v2 to the 3-day grace period and the cleaned counts? | OPEN | Owner | Pitch narrative |
| Q-007 | Does a separate Development Methodology Specification exist anywhere? | OPEN | Owner | None |
| Q-008 | Note features: run on IBM only (real dispute events behind the notes), or on the 50,000-row data as illustrative (no real events behind them)? | RESOLVED (D-059) | Owner | Note features spec |
| Q-009 | Is the 3-day grace period counted in calendar days or business days? | RESOLVED (D-056) | Owner | G1 |
| Q-010 | Minimum number of prior paid invoices for "sufficient" history; to be set from profiling | RESOLVED (D-061) | Claude to profile, owner to approve | G1 / G2 |
| Q-011 | Data contract v1.1 (owner's draft): adopt it, and extend it for notes and the 10-day scoring time? | RESOLVED (D-057) | Owner | G1 |
| Q-012 | Also train a Stage-1-style model on IBM (no notes), so the Stage 2 gain from notes is measured on the same data? Claude recommends yes: without it, Stage 2 versus Stage 1 compares two different datasets | RESOLVED (D-071) | Owner | G1 |
| Q-013 | Use countryCode as the IBM fairness group (5 codes, 387 to 616 invoices each, late rates 18% to 36%)? Proposed by Claude | RESOLVED (D-072) | Owner | G1 |
| Q-014 | Move the system spec (Claude Doc "Late Payment Prototype v2") into the repo as `SYSTEM_SPEC.md`, so the repo is the single source for a rebuild? The Doc can remain the pitch narrative. Claude recommends yes | OPEN | Owner | G2 |
| Q-015 | G3: is D-022's exception ("unless the group really is late more often") acceptable when it lets CA02 and new customers be flagged 6 to 7 times more often by false alarm (D-091)? Claude recommends tightening it: compare false alarms to each group's own late rate, and show these groups in the app as "review" rather than "chase" | OPEN | Owner | G3 |
| Q-016 | G3: pass thresholds for M1 to M5 and default risk bands (proposed: high = top 20%, medium = next 30%) | OPEN | Owner | G3 |

## Assumptions

| ID | Assumption | Status | Evidence |
|---|---|---|---|
| A-001 | Duplicate rows are copies, not repeat invoices | RESOLVED | Every repeated doc_id is an exact copy (D-040) |
| A-002 | The 131 invoices due before their invoice date are data errors, not prepayment invoices | OPEN | Unverifiable from the data; dropping 0.3% is low-risk |
| A-003 | The meaning of payment-term codes (for example NAA8) | OPEN | Undocumented |
| A-004 | A public invoice dataset is close enough to the client's billing data to be credible | OPEN | Spec v2, A4 |
| A-005 | The approach transfers to the client; the trained model does not and is retrained there | OPEN | Spec v2, section 20 |
| A-006 | IBM disputes are raised before the Stage 2 scoring date (due date minus 10 days), so dispute notes dated before then are realistic | OPEN | The data has no dispute date |
