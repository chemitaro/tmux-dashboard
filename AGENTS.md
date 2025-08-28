# AI Coding Agent Development Guide

This file provides guidance to AI Coding Agents when working with this project.

## Project Overview

[プロジェクトの概要をここに記載してください]

### Development Status

**Development Phase**: [開発フェーズを記載]
- **Data**: [データの扱い方針]
- **Breaking Changes**: [破壊的変更の許容度]

## Development Workflow

### Spec-Driven Development Methodology

This project follows a strict specification-driven development approach with a 4-document system.

#### 1. Preparation Phase

**Master Plan → Investigation (95%) → Requirements → Design → Implementation Plan**

1. **Master Plan Analysis**: Review `@planning/master_plan.md` & `master_requirement.md` (if exists)
2. **Code Investigation**: Investigate until 95% understanding
3. **Requirements**: Define WHAT (`@planning/current/requirement.md`)
4. **Design**: Define HOW after 95% understanding (`@planning/current/design.md`)
5. **Implementation Plan**: Task checkboxes (`@planning/current/task.md`)

#### 2. Implementation Phase

**TDD Cycle**: Red → Green → Refactor
- Break down task.md items → TodoWrite → Implement → Update checkboxes

#### 3. Completion Phase

**QA & Documentation**
- Run tests and linters
- Create report (`@planning/current/report.md`)
- Archive 4 documents

### Important Principles

- **95% Understanding Rule**: Never proceed without 95% understanding and confidence
- **Strict 4-Document System**: All development follows this system
- **@ Notation References**: Maintain inter-document linkage
- **TodoWrite Integration**: Break down task.md items into concrete work
- **TDD First**: Always follow Test-Driven Development

## Current Development Planning

See: @planning/current/requirement.md
See: @planning/current/design.md
See: @planning/current/task.md
See: @planning/current/report.md

## Development Commands

### Test Execution

```bash
# Define your test commands here
# Example:
# npm test
# pytest
# cargo test
```

### Code Quality Checks

```bash
# Define your linting commands here
# Example:
# npm run lint
# ruff check .
# cargo clippy
```

## Testing Strategy

### Testing Principles

#### TDD (Test-Driven Development)

Following Kent Beck & Takuto Wada (t-wada) principles:

1. **Red**: Write a failing test
2. **Green**: Minimal code to pass the test
3. **Refactor**: Improve the code

Golden Rule: "Never write a line of functional code without a failing automated test"

#### Three Principles
- **Test First**: Write tests before implementation
- **Baby Steps**: Progress in small increments
- **Triangulation**: Generalize from multiple concrete examples

## Implementation Prerequisites

### 95% Rule
**Never implement without 95% understanding AND 95% confidence.** 
Must understand: codebase structure, dependencies, business logic, impact.

### Workflow: Investigate → Ask → Design → Implement
1. **Investigate** code thoroughly
2. **Ask user** if understanding < 95%
3. **Design** only after full understanding
4. **Implement** with confidence

### When Uncertain, Ask About:
Business logic, expected behavior, constraints, component relationships

## TodoWrite Task Management

### When to Use

Proactively use TodoWrite tool:

1. **Multi-step tasks**: When there are 3 or more steps
2. **Complex tasks**: When planned execution is needed
3. **User request**: When explicitly requesting Todo list
4. **Multiple tasks**: Numbered or comma-separated tasks
5. **New instruction receipt**: Record requirements as Todo
6. **Work start**: Mark as in_progress when starting
7. **Completion**: Mark as completed and move on

### When NOT to Use
- Single simple task
- Simple work with less than 3 steps
- Pure conversation or information provision

### Task Breakdown Principles

Break down the minimum units from `@planning/current/task.md` into concrete coding operations:
- Which files to create/modify
- What code to write
- How to verify

Each TodoWrite item should be a concrete action executable in 15-30 minutes.

## Important Notes

**Follow the spec-driven development process strictly**: Always create and maintain the 4 documents throughout development.