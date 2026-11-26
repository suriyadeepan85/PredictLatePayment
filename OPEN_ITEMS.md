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

## Assumptions

| ID | Assumption | Status | Evidence |
|---|---|---|---|
| A-001 | Duplicate rows are copies, not repeat invoices | RESOLVED | Every repeated doc_id is an exact copy (D-040) |
| A-002 | The 131 invoices due before their invoice date are data errors, not prepayment invoices | OPEN | Unverifiable from the data; dropping 0.3% is low-risk |
| A-003 | The meaning of payment-term codes (for example NAA8) | OPEN | Undocumented |
| A-004 | A public invoice dataset is close enough to the client's billing data to be credible | OPEN | Spec v2, A4 |
| A-005 | The approach transfers to the client; the trained model does not and is retrained there | OPEN | Spec v2, section 20 |
