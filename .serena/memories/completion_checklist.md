# Completion checklist
- Run `uv run pytest -q` and confirm the suite is green (allowing known xfails when expected).
- Update `planning/current/report.md` with timestamped work log and validation results.
- Keep requirement/design/task alignment in sync with any behavioral changes.
- Verify non-invasive tmux behavior assumptions when touching layout or tmux commands (`set-option -w`, not global settings).
- If file paths were added/renamed, verify uppercase-path constraint with `rg --files | rg '[A-Z]'`.
