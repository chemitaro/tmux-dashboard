# Style and conventions
- User-facing chat should be in Japanese for this project.
- Spec-driven workflow uses planning docs under `planning/current/`: requirement, design, task, report.
- Tests should have Japanese docstrings for modules and test functions describing purpose, preconditions, expected outcome.
- TDD is expected: Red -> Green -> Refactor, and phase completion should include `uv run pytest`.
- Avoid uppercase in newly created or renamed paths; prefer lowercase `a-z0-9._-`.
- Commit messages, if requested, must be Japanese multi-line Conventional Commits.
- Implementation uses typed Python and small focused modules rather than one large script.
