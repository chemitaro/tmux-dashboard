---
name: spec-driven-tdd-workflow
description: A workflow that drives development from requirements refined into observable behaviors (AC/EC) through requirement definition → design → implementation planning → TDD (Red/Green/Refactor) implementation → reporting → commit. Apply to tasks that execute based on `spec-lite/current/*.md`.
---

# Spec-driven TDD Workflow

- Open `spec-lite/docs/spec-lite-guide.md` first, and follow it for the rest of the workflow.
- Create/update `spec-lite/current/requirement.md`, `spec-lite/current/design.md`, `spec-lite/current/plan.md`, and `spec-lite/current/report.md` to maintain traceability from requirements → design → plan → implementation.
- Put investigation/interview materials in `spec-lite/current/discussions/` (prefer Markdown; embed diagrams with PlantUML; organize freely).
- Keep user interviews/questions short and prioritized. For each question, include answer candidates (options) and your recommended choice based on analysis/simulation to reduce cognitive load.
- Implement each step in `spec-lite/current/plan.md` as one observable behavior via TDD (Red → Green → Refactor).
- Record commands/results/changes/decisions in `spec-lite/current/report.md` per session, and `git commit` at the end of the phase.
