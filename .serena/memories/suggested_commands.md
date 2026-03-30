# Suggested commands
- Install/sync deps: `uv sync` or `uv sync --locked`
- Run tests: `uv run pytest -q`
- Run dashboard once for testing: `uv run python -m tmux_dashboard --once --iterations 1`
- Run dashboard continuously: `uv run python -m tmux_dashboard`
- Use custom config: `uv run python -m tmux_dashboard --config /path/to/config.yaml`
- Inspect tmux sessions: `tmux list-sessions`
- Attach dashboard: `tmux attach -t dashboard`
- Stop dashboard session: `tmux kill-session -t dashboard`
- Verify uppercase path constraint after edits: `rg --files | rg '[A-Z]'`
