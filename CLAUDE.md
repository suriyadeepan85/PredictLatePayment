# CLAUDE.md: Late Payment Prediction (hackathon prototype)

Owner and decision maker: Suriyadeepan Narayanasamy. Claude builds; the owner approves.

## Start of every session
1. Read `STATUS.md`, then `OPEN_ITEMS.md`, then the latest entry in `docs/session_log.md`.
2. Read the spec for the current gate in `specs/` or `docs/`.
3. Tell the owner the current gate and what is waiting for approval before doing new work.

## End of every session (checkpoint)
1. Add or update records in `DECISIONS.md` and `OPEN_ITEMS.md`, and add the session to `docs/session_log.md`.
2. Update `STATUS.md`: done, next, waiting for approval.
3. Commit and push. Unpushed work can be lost: the build workspace is temporary.

## Governance (non-negotiable)
- Claude may only create records with status PROPOSED. Only the owner moves a record to APPROVED, REJECTED or SUPERSEDED (for example, "approve D-012").
- Never change a spec, contract or approved decision without the owner's explicit approval in the current session.
- Cite evidence as a file path or a dated quote of the owner, never a chat link.
- Methodology: `specs/methodology.md`.

## Project rules
- No client data, ever. Public and synthetic data only, generic names.
- Never display or commit customer names. Mask them as "Customer 0001" and so on.
- No raw data in git (`data/raw/` is ignored). Datasets are re-downloaded and checked by SHA-256.
- Every reported metric uses real outcomes on the time-based test set.
- No AWS deployment without the owner's approval.

## Where things live
| What | Where |
|---|---|
| Product and pitch narrative | Claude Doc "Late Payment Prototype v2" (https://claude.ai/artifact/LEGMYiT5FwLRfdKCmBBd7w), updated at milestones |
| Build specs (authoritative for code) | `specs/` and `docs/data_contract.md` |
| Decisions, observations | `DECISIONS.md` |
| Questions, assumptions | `OPEN_ITEMS.md` |
| Progress and checkpoint | `STATUS.md` |
| Profiling | `notebooks/01_profile_data.ipynb` |
| Folders for future owners | `src/data`, `src/features`, `src/model`, `app`, `infra` |
