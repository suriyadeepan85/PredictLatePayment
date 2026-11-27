# Specs index

The repo is the source for rebuilding the prototype without the chat (D-077). Methodology: the owner's Development Methodology Specification v1.0 (D-076), with the record rules in `methodology.md`.

## Role specs (`agents/`)
| Role | File | Methodology section |
|---|---|---|
| Coordinator | `agents/coordinator.md` | 5.2 |
| Data Engineer | `agents/data_engineer.md` | 7.2 |
| ML Engineer | `agents/ml_engineer.md` | 7.1 |
| LLM Engineer (and app, for now) | `agents/llm_engineer.md` | 7.3 |
| DevOps Engineer | `agents/devops_engineer.md` | 7.4, 8 |
| QA Engineer | `agents/qa_engineer.md` | 7.5 |
| Evaluator | `agents/evaluator.md` | Added (not in v1.0) |

## Component specs (10-section format, methodology 5.3)
| Component | File | Owner role | Gate | State |
|---|---|---|---|---|
| Data contract | `../docs/data_contract.md` | Data Engineer | G1 | APPROVED v1.4 |
| Feature list | `features.md` | ML Engineer | G2 | v0.1, waiting for G2 approval (D-080) |
| Note features | `note_features.md` | LLM Engineer | G2 | v0.1; signals APPROVED |
| Models, evaluation, fairness | `ml_engineer.md` sections 5 to 7, then `evaluation.md` | ML Engineer, Evaluator | G3 | Not started |
| App and outreach | `app.md` | LLM Engineer | before G6 | Not started |
| Demo script | `demo.md` | Coordinator | G6 | Not started |
| System spec | Claude Doc "Late Payment Prototype v2"; repo copy proposed (Q-014) | Owner | | |
