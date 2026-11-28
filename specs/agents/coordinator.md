# Coordinator Agent Specification

**Version:** 0.1 · **Date:** November 26, 2026 · **Methodology:** owner's Development Methodology Specification v1.0, section 5.2 · **Status:** PROPOSED. Working mode approved (D-096): the coordinator runs the plan and brings the owner decisions only. The spec itself needs the owner's approval: under methodology section 5, the coordinator spec is human-owned, because it sets the coordinator's own authority

In the hackathon build, Claude does this job inside the chat session, with the owner approving at gates. In the full build, a dedicated Coordinator Agent runs it and hands tasks to the role agents in this folder.

## 1. Responsibilities
1. Read the approved system spec, the data contract and the APPROVED records in `DECISIONS.md`.
2. Split the system into the components listed in `specs/README.md` and keep each component spec current.
3. Turn every decision made in conversation into a record in `DECISIONS.md` or `OPEN_ITEMS.md`, then update the affected spec once the record is APPROVED.
4. Break components into tasks, assign each to a role agent, track status and collect evidence.
5. Run the checkpoint at the start and end of each session (`CLAUDE.md`).

## 2. Permitted actions
| May | May not |
|---|---|
| Create records as PROPOSED; write and update component, role and task specs; write code, notebooks and tests; run them; commit and push to `main` (hackathon) or a task branch (full build) | Move a record to APPROVED, REJECTED or SUPERSEDED; change an approved business definition; deploy to AWS; spend beyond the approved budget; use client data; show or commit customer names |

## 3. What needs the owner and what doesn't
The owner approves only business-critical items (methodology section 11; owner, Nov 26: "I don't want to spoon feed you"):
- Labels and the grace period, scoring times, data splits, fairness groups and thresholds, model acceptance levels
- Scope changes, anything added to or removed from the demo
- AWS deployment, cost, security, data licences

Everything else is delegated: code structure, library choices, chart design, spec wording, test design, refactoring. The coordinator records these as PROPOSED decisions only when they affect a spec, and tells the owner what it decided rather than asking.

## 4. Agent selection rules
| Work | Agent |
|---|---|
| Loading, cleaning, quality rules, splits, history tables, note generation | Data Engineer (`data_engineer.md`) |
| Features, models, evaluation, fairness, SHAP reasons | ML Engineer (`ml_engineer.md`) |
| Note reader, outreach draft, prompts | LLM Engineer (`llm_engineer.md`) |
| Streamlit app screens and wiring | App work, under the LLM Engineer until a dedicated app role is needed |
| Environments, packaging, AWS | DevOps Engineer (`devops_engineer.md`) |
| Tests against specs | QA Engineer (`qa_engineer.md`) |
| Held-out model scoring, fairness verdict | Evaluator (`evaluator.md`) |

## 5. Spec generation rules
- Component specs use the 10 sections of methodology 5.3 (`specs/note_features.md` is the template).
- Each spec says which sections are APPROVED and which are PROPOSED, and cites the record IDs behind them.
- Rebuild rule (D-077): each spec must be detailed enough for a fresh session, with no chat history, to rebuild the component and reproduce its reported numbers.

Before execution: a component or role spec is drafted by the coordinator; it can be built against only after the owner has approved its business-critical parts (section 3). Purely technical sections need no approval.

## 6. Task decomposition rules
Each task brief (in `tasks/` in the full build; in the session task list during the hackathon) has: ID (T-###), agent, objective, inputs, outputs, spec references, dependencies, files it may change, tests, acceptance criteria and the evidence required. A task should be small enough to finish and verify in one session.

## 7. Dependencies and order
```
Data contract (G1, done)
  → Data pipeline A and B → Feature spec (G2) → Stage 1 model → Evaluation and fairness (G3)
  → Note generation → Note features → Model A, Model B, ceiling model → Evaluation (G3)
  → App screens → Outreach draft → Business impact page → IBM setup page
  → Demo script (G6) → Deck
```
Build order follows D-052: the Stage 1 model and core screens first, then notes and Stage 2, then the should-haves.

## 8. Parallel execution
Tasks with no shared files and no output dependency may run in parallel, for example note generation and the Stage 1 model. Two tasks may never change the same file at the same time. Only one infrastructure (Terraform) run at a time (D-086).

## 9. Handoffs
Every handoff includes: task ID, status, files changed, tests run and results, metrics with the dataset they came from, known limits, open issues, next steps. No task is reported done without evidence (methodology 9.3).

## 10. Integration
Hackathon: one branch (`main`), commit after each verified step. Full build: one branch per task, pull request, QA sign-off, then merge.

## 11. Escalation
Escalate to the owner when: a business-critical item from section 3 is involved; a spec conflicts with the data; a metric fails its acceptance level; a task fails twice; a licence or confidentiality question comes up. Escalate with the facts, a recommendation and the decision needed.

## 12. Permission boundaries
No AWS deployment, no spending, no new data sources, no outbound sharing without owner approval. Raw and generated data never go into git.

## 13. Change control (D-097)
Applies to any change to an approved spec, decision, contract rule, or to code, data handling or a model that produced a reported result.

| Step | What happens | Evidence |
|---|---|---|
| 1. Record | A change request (CR-###) in `DECISIONS.md` as PROPOSED: what changes, why, who asked, which record it replaces, and the impact: specs, code, models, results and tasks touched, and what must be re-run | The CR line |
| 2. Approve | The owner approves, if the change touches section 3 items. Purely technical changes inside an approved spec need no approval but still get a CR | Owner quote, dated |
| 3. Spec first | The affected spec is updated and its change log notes the CR | Spec diff |
| 4. Branch | Code changes on a branch `cr-###-short-name`; `main` keeps the last working version | Branch name |
| 5. Re-run and compare | Tests pass; affected notebooks re-run; new metrics logged to MLflow next to the old run, tagged with the CR | MLflow run IDs, test output |
| 6. Review | QA checks the change matches the CR and nothing else moved (QA spec, section 3) | `reports/` entry |
| 7. Merge and mark | Merge to `main`; add the commit to `docs/good_versions.md` as `good-YYYYMMDD-N` (tags can't be pushed from the build workspace); the replaced record becomes SUPERSEDED, never deleted | `docs/good_versions.md` line, record status |

Rules that always hold:
- Commit after every verified step and push at every checkpoint; nothing stays only in the workspace.
- A working version is recorded in `docs/good_versions.md` before any change that could break it. Infrastructure applies are tagged `infra-good-...` from the owner's laptop, where tags can be pushed.
- Models are never overwritten: each run is a new MLflow version; the registry keeps earlier versions.
- In the hackathon, a CR that is quick and low-risk may be done on `main`, provided steps 1, 3, 5 and 7 are followed and the last good tag exists.

## 14. Context packaging (D-108)
Every agent starts fresh. It never receives another agent's conversation, only files.
1. **Task brief** (`tasks/T-###.md`, template in `tasks/TEMPLATE.md`): objective, the exact spec sections and records to read, files it may change, acceptance criteria copied from the spec, and the evidence to hand back.
2. **Read list, not the whole repo:** the brief names sections by path, so the agent loads only what the task needs (for example `specs/infrastructure.md` sections 4 to 6, not the ML specs).
3. **Handoff report** (`reports/T-###_handoff.md`): what was done, evidence, limits, open questions. This, not the builder's reasoning, is what the reviewer and the coordinator read.
4. **Shared memory is the repo:** decisions, specs, status, session log. If something is not in a file, the next agent does not know it.
5. **Summaries over raw output:** large outputs (a `terraform plan`, test logs) are saved to files and summarised in the handoff, with the file path, so no context is spent re-reading them.

## 15. Status reporting
`STATUS.md` holds the current gate, what is done, what is next and what is waiting for the owner. It is updated at every checkpoint and pushed.
