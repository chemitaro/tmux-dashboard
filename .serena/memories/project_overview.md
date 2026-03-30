# tmux-dashboard overview
- Purpose: provide a live tiled dashboard inside a dedicated tmux session named `dashboard` that shows the latest output from other tmux sessions.
- Stack: Python 3.10+, tmux 3.2+, PyYAML, wcwidth, libtmux. Uses `uv` for environment management.
- Entry points: `python -m tmux_dashboard` and the repo-level `tmux-dashboard` script / `make install` symlink flow.
- Core architecture: `orchestrator.py` computes session list and layout, `tmuxio.py` abstracts tmux drivers (libtmux/cli), `tile.py` renders one dashboard pane from a target pane, `renderer.py` provides formatting/diff helpers, `config.py` loads YAML/defaults, `layout.py` computes column-major tile positions, `session_manager.py` ensures the dashboard session exists.
- Behavior highlights: excludes the dashboard session itself, sorts sessions ASCII ascending, rebuilds layout on session/size/title integrity changes, sets pane borders per-window (`set-option -w`), and chooses a best pane per session with VS Code-aware heuristics.
- Test status observed on 2026-03-14: `uv run pytest -q` => 67 passed, 3 xfailed. xfails are headless tmux E2E limitations around `split-window`.
