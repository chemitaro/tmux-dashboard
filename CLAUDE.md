# AI Coding Agent Instructions

This file provides guidance to AI Coding Agents when working with this project.
Both Claude Code and OpenAI Codex CLI (and other AI agents) should refer to this file.

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
- Record all work in report.md with timestamps

#### 3. Completion Phase

**QA & Documentation**
- Run tests and linters
- Create report (`@planning/current/report.md`)
- Archive 4 documents to `planning/completed/YYYYMMDD_HHMM_task_name/`

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

## Starting a New Task

1. Copy requirement template to current:
   ```bash
   cp planning/templates/requirement.md planning/current/requirement.md
   ```

2. After requirement approval, prepare all documents:
   ```bash
   cp planning/templates/*.md planning/current/
   ```

3. Use TodoWrite to track implementation progress

4. Archive completed work:
   ```bash
   mkdir planning/completed/$(date +%Y%m%d_%H%M)_task_name/
   cp planning/current/*.md planning/completed/$(date +%Y%m%d_%H%M)_task_name/
   ```

## File References

When working with planning documents, use these references:
- `@planning/current/requirement.md`
- `@planning/current/design.md`
- `@planning/current/task.md`
- `@planning/current/report.md`

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

## Project-Specific Configuration

### Environment Variables

```bash
# List important environment variables here
# Example:
# NODE_ENV=development
# DATABASE_URL=...
```

### Project Structure

```
# Define your project structure here
# Example:
# /src/           # Source code
# /tests/         # Test files
# /docs/          # Documentation
# /planning/      # Spec-driven development documents
```

### Dependencies

```bash
# List key dependencies and their versions
# Example:
# Node.js >= 18.0.0
# Python >= 3.10
# Rust >= 1.70
```

## GitHub Operations (if applicable)

If working with GitHub repositories:

```yaml
Repository: [repository-name]
Owner: [owner]
Default Branch: [main/master/develop]
```

### Using GitHub CLI
```bash
# Pull Request Operations
gh pr create --title "title" --body "description"
gh pr list
gh pr view <PR number>

# Issue Operations
gh issue create --title "title" --body "description"
gh issue list
gh issue view <issue number>
```

## Command Execution Notes

### Docker Environment (if using)
```bash
# Example Docker commands
# docker compose exec [service] [command]
# docker compose run --build --rm [test-service]
```

### Local Environment
```bash
# Commands run directly in the development environment
```

## AI Agent Specific Constraints

1. **No Interactive Mode**: Cannot use commands with -i flag
2. **No Auto-commit**: Only commit with explicit instructions
3. **@ Notation Support**: Resolve @ references in project files
4. **Parallel Execution**: Execute multiple independent tasks when possible

## Effective Development Tips

1. **Parallel Tool Execution**: Execute multiple independent tasks simultaneously
2. **Pre-load Multiple Files**: Load related files in batch
3. **Proactive TodoWrite Usage**: Visualize progress with task management
4. **Use appropriate tools**: For complex searches requiring multiple rounds

## Important Reminders

- **Always follow spec-driven development**: Create and maintain 4 documents
- **95% Understanding Rule**: Never proceed without full understanding
- **Use TodoWrite proactively**: For task management and progress tracking
- **Test-Driven Development**: Red → Green → Refactor cycle
- **Document everything**: Keep report.md updated in real-time