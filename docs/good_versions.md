# Known good versions

Each line is a commit that passed its tests and checks. To go back: `git checkout <commit>` (or `git revert` to undo on main).
Tags can't be pushed from the build workspace (GitHub returns 403 through its proxy), so this file is the record (coordinator spec, section 13).

| Name | Commit | Date | What was verified |
|---|---|---|---|
| good-20261127-1 | ce4d919 | Nov 27, 2026 | 11 tests pass; notebooks 01 to 07 run; Stage 1 and IBM models validated; masking N6 = 0 |
