# VS Code Terminal Support Implementation

## Problem Description

When tmux sessions are launched from VS Code's integrated terminal, the dashboard would show them as black/empty even though the sessions were running normally. This occurred because VS Code terminals become inactive when not focused, causing all `window_active` and `pane_active` flags to be 0.

## Root Cause Analysis

tmux uses a client-server model where:
- Multiple clients can connect to the same session
- Each client has its own active window/pane
- When a client is disconnected or inactive, its active flags are not set

VS Code's integrated terminal acts as a tmux client, but when:
- The VS Code terminal tab is not active
- VS Code itself is in the background
- The terminal is not focused

The tmux session has no active client, resulting in all `window_active = 0` and `pane_active = 0`.

## Solution: Intelligent All-Pane Scan

We implemented a `resolve_best_pane` method that:

### 1. Performance Optimization
First checks if there are any active windows/panes. If yes, uses the traditional method for best performance.

### 2. VS Code Detection
When all windows/panes are inactive (VS Code scenario), skips the traditional method entirely.

### 3. Comprehensive Scan
Scans all panes in the session and captures their content to find panes with actual output.

### 4. Freshness Scoring
Prioritizes panes based on content freshness:
- ANSI escape sequences (+1 point)
- Command prompts (`$`, `>`, `#`, `%`) (+2 points)
- Non-empty lines (+0.5 points)
- Focus on the last 10 lines for recency

### 5. Smart Selection
Selects the pane with the highest freshness score, ensuring the most relevant pane is displayed.

## Implementation Details

### Files Modified

1. **tmux_dashboard/tmuxio.py**
   - Added `resolve_best_pane` method to both `CliDriver` and `LibtmuxDriver`
   - Added `_calculate_content_freshness` helper method
   - Updated `TmuxIO` interface to expose the new method

2. **tmux_dashboard/orchestrator.py**
   - Updated to use `resolve_best_pane` with fallback to `resolve_active_pane`
   - Maintains backward compatibility with existing test fixtures

3. **tests/test_vscode_terminal_support.py**
   - Comprehensive test suite covering:
     - Traditional active pane selection
     - VS Code all-inactive scenario
     - Content freshness prioritization
     - Fallback behavior

## Test Coverage

All tests pass successfully:
- 5 new tests specifically for VS Code terminal support
- 50 total tests passing (including existing test suite)
- No regression in existing functionality

## Usage

The VS Code terminal support is automatic and requires no configuration changes. The dashboard will:
1. Detect when sessions are launched from VS Code terminals
2. Intelligently scan for the most relevant pane
3. Display real-time content even when VS Code is not focused

## Performance Considerations

- Traditional method is used first when possible (minimal overhead)
- Full scan only occurs in VS Code scenarios (all inactive)
- Capture buffer size is limited to prevent memory issues
- Freshness calculation is lightweight and efficient

## Future Improvements

Potential enhancements for consideration:
- Configuration option to always use intelligent scan
- Customizable freshness scoring weights
- Caching of pane selections with TTL
- Metrics on scan frequency and performance