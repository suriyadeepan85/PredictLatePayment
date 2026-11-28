# Session log

A short, dated summary of each working session (D-106). It gives a fresh session the story behind the records. **The records are the authority:** decisions are in `DECISIONS.md`, questions and assumptions in `OPEN_ITEMS.md`, the current state in `STATUS.md`. This log only gives context, and it isn't a transcript.

## Before November 26: planning (voice and text)
- **Idea:** predict late invoice payments so receivables teams can act before the due date. Today's dunning only starts after it. The hackathon is due November 30, 2026; the deliverables are a deck and a working application; the judges are delivery leaders and AI practice heads.
- **Data:** no client data. Public data only: Customer Invoices (50k, Kaggle) and the IBM accounts-receivable sample. Customer names are masked.
- **Ways of working:** a light, spec-driven build. Claude builds, the owner approves at gates G1, G2, G3 and G6. Product spec v2 lives in a Claude Doc; build specs live in the repo (D-001 to D-009, D-007 methodology).
- **Profiling:** Customer Invoices profiled, grace period set at 3 days (D-012). The data contract was drafted.

## November 26
- **Scope (voice):** note features back in scope; two predictions, at the invoice date and 10 days before the due date; nothing dropped; build order set (D-050 to D-052).
- **Data contract:** v1.2 to v1.4. Two models, Stage 1 on the 50k data and Stage 2 on IBM (D-059). History groups 0 / 1-4 / 5+ (D-061). Notes linked by customer, with the generation mix (D-064 to D-067). IBM split (D-068). G1 closed (D-075).
- **Comparison models:** Model A without notes (D-071) and a ceiling model with the dispute flag (D-073). Seven note signals (D-074).
- **Methodology:** the owner's methodology attached; adopted as the target (D-076 to D-078); role specs written as decisions are made (D-079).
- **Features:** G2 spec and notebook 04 built.

## November 27
- **Approvals (voice):** G2 approved (D-080).
- **Hosting:** the app must be hosted, and judges use it on their own (D-082). Lightsail plus a SageMaker serverless endpoint, with a fallback model (D-083); App Runner closed to new customers.
- **Training process:** SageMaker Pipeline plus open-source MLflow (D-084). Adjustable risk bands (D-085).
- **Infrastructure:** Terraform with S3 native locking (D-086). Owner and agent security split (D-087). Fake personal details in the notes plus rules-based one-way masking (D-088). Infrastructure spec written.
- **Built:** Stage 1 trained (notebook 06); notes generated, masked and read (notebook 05); IBM models (notebook 07).
- **Process:** the coordinator runs the work and asks only for decisions (D-096). Change control (D-097) and three-point review (D-098) written.
- **Independent review:** 1 blocker (the Stage 2 claim was circular) and 8 major findings. Technical fixes applied and approved (D-099).
- **Owner decisions (text):** tightened fairness rule (D-102); Stage 2 scores only invoices still unpaid (D-103); honest notes plus a what-if curve (D-104); default risk bands (D-105); D-001 and D-004 superseded.
- **Open:** Q-001 (organizers' approval of the personal account), Q-003 (Bedrock credits), approval of `specs/infrastructure.md`, the coordinator spec, Q-014 (system spec in the repo).
- **Next:** rebuild Stage 2 under D-103 and D-104; the Streamlit app; the evaluator pass; deployment.

## November 28 (after midnight)
- Owner asked how the reviewer runs per task and how context is handled; written as D-108 (task briefs, handoff reports, risk-based review frequency; `tasks/TEMPLATE.md`).
- Stage 2 rebuilt: only invoices unpaid on the Stage 2 date; varied note wording; 30% of disputes noted late; routine notes on every invoice (found and removed an artifact, D-109); what-if curve averaged over 3 note generations (D-110).
- Waiting: D-109 approval (contract section 6 wording), infrastructure spec, coordinator spec, Q-001.
- Second review (Stage 2 only): R-01 and R-02 confirmed fixed; note count still hinted at disputes, cold-start fold dragged averages, specs lagged code. Fixed in D-111; results D-112. New question Q-020 on the fairness rule.
