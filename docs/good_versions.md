# Known good versions

Each line is a commit that passed its tests and checks. To go back: `git checkout <commit>` (or `git revert` to undo on main).
Tags can't be pushed from the build workspace (GitHub returns 403 through its proxy), so this file is the record (coordinator spec, section 13).

| Name | Commit | Date | What was verified |
|---|---|---|---|
| good-20261127-1 | ce4d919 | Nov 27, 2026 | 11 tests pass; notebooks 01 to 07 run; Stage 1 and IBM models validated; masking N6 = 0 |
| good-20261127-2 | feb1c10 | Nov 27, 2026 | Review fixes: 32 tests pass; notebooks 04 to 07 rerun; Stage 1 calibrated. Stage 2 headline not valid (D-101) |
| good-20261128-1 | 9fa1c27 | Nov 28, 2026 | Stage 2 rebuilt; 32 tests pass; notebooks 05 to 07 rerun |
| good-20261128-2 | 2584a13 | Nov 28, 2026 | Stage 2 review fixes; 36 tests pass; notebooks 05 to 07 rerun |
