# Claude Code Project Configuration

This file extends AGENTS.md with Claude Code specific configurations.

## Base Configuration

See: @AGENTS.md for general development guidelines

## Claude Code Specific Settings

### MCP Tools Configuration

If your project uses MCP (Model Context Protocol) tools, configure them here:

```yaml
# Example MCP tools configuration
tools:
  - serena-mcp: For code investigation
  - context7: For library documentation
```

### Command Execution

#### Docker Environment
If using Docker, all commands should be executed through Docker Compose:

```bash
# Example Docker commands
# docker compose exec [service] [command]
# docker compose run --build --rm [test-service]
```

#### Local Environment
If running locally in Claude Code container:

```bash
# Commands run directly in the Claude Code environment
```

### GitHub Operations

If working with GitHub repositories:

```yaml
Repository: [repository-name]
Owner: [owner]
Default Branch: [main/master/develop]
```

#### Required: Use GitHub CLI
**Use GitHub CLI (`gh` command) for all GitHub operations.**

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

### Claude Code Specific Constraints

1. **No Interactive Mode**: Cannot use commands with -i flag
2. **No Auto-commit**: Only commit with explicit instructions
3. **@ Notation Support**: Resolve @ references in project files
4. **Parallel Tool Execution**: Execute multiple independent tasks simultaneously

### Effective Usage Tips

1. **Parallel Tool Execution**: Execute multiple independent tasks simultaneously
2. **Pre-load Multiple Files**: Load related files in batch
3. **Proactive TodoWrite Usage**: Visualize progress with task management
4. **Use Task Tool**: For complex searches requiring multiple rounds

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

## Development Workflow Integration

### Starting a New Task

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

### File References

When working with planning documents, use these references:
- `@planning/current/requirement.md`
- `@planning/current/design.md`
- `@planning/current/task.md`
- `@planning/current/report.md`

## Important Reminders

- **Always follow spec-driven development**: Create and maintain 4 documents
- **95% Understanding Rule**: Never proceed without full understanding
- **Use TodoWrite proactively**: For task management and progress tracking
- **Test-Driven Development**: Red → Green → Refactor cycle