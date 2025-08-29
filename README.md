# tmux-dashboard

A real-time terminal dashboard that displays all tmux sessions in a beautiful tiled layout, providing a comprehensive overview of your terminal activities at a glance.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![tmux](https://img.shields.io/badge/tmux-3.2%2B-green)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Features

- **Automatic Session Detection**: Discovers and displays all tmux sessions (except the dashboard itself)
- **Tiled Layout**: Intelligently arranges sessions in a responsive grid layout
- **Real-time Updates**: Continuously monitors and updates session content
- **Color Preservation**: Maintains ANSI colors and TrueColor formatting from original sessions
- **Column-Major Ordering**: Sessions are arranged vertically (top-to-bottom, then left-to-right) for better readability
- **VS Code Terminal Support**: Intelligent pane scanning ensures proper display even from VS Code integrated terminals
- **Non-invasive**: Uses window-specific settings only (`-w`), never modifies global tmux configuration
- **Bottom-Aligned Display**: Shows the most recent output (bottom lines) of each session
- **Auto-resizing**: Automatically adjusts layout when terminal is resized or sessions are added/removed
- **Session Auto-creation**: Dashboard session is created automatically if it doesn't exist

## Requirements

- **OS**: Linux or macOS
- **tmux**: Version 3.2 or higher
- **Python**: Version 3.10 or higher

## Installation

### Using uv (Recommended)

1. Install [uv](https://github.com/astral-sh/uv) (fast Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone https://github.com/chemitaro/tmux-dashboard.git
cd tmux-dashboard
```

3. Install dependencies:
```bash
uv sync
```

### Using pip

```bash
git clone https://github.com/chemitaro/tmux-dashboard.git
cd tmux-dashboard
pip install -r requirements.txt
```

## Quick Start

Simply run the dashboard:
```bash
# Using uv
uv run python -m tmux_dashboard

# Using pip
python -m tmux_dashboard
```

The dashboard will:
1. Automatically create a tmux session named "dashboard" if it doesn't exist
2. Display all other tmux sessions in a tiled layout
3. Update in real-time as you work

To attach to the dashboard:
```bash
tmux attach -t dashboard
```

## Configuration

### Configuration File Locations

The dashboard looks for configuration in the following order:
1. Command-line specified: `--config /path/to/config.yaml`
2. Project directory: `configs/dashboard.yaml`
3. User home: `~/.config/tmux-dashboard/config.yaml`
4. Built-in defaults

### Configuration Options

Create a configuration file based on the example:
```bash
cp configs/dashboard.example.yaml configs/dashboard.yaml
```

Key configuration options:

```yaml
# Minimum width for each tile (in columns)
min_tile_width: 40

# Session detection interval (seconds)
poll_interval_sec: 2

# Exclude specific sessions from display
exclude_patterns:
  - "^dashboard$"
  - "^temp-.*"

# Display settings
viewer:
  capture_buffer_multiplier: 2.0
  capture_buffer_max: 200
  capture_buffer_min_extra: 20
  max_fps: 30
  truecolor: true

# Logging
logging:
  level: "INFO"
  dir: "~/.local/state/tmux-dashboard"
```

## Usage Examples

### Basic Usage
```bash
# Start the dashboard
uv run python -m tmux_dashboard

# Start with custom config
uv run python -m tmux_dashboard --config ~/my-dashboard.yaml

# Run for a specific number of iterations (useful for testing)
uv run python -m tmux_dashboard --iterations 5
```

### Working with the Dashboard
```bash
# Create new tmux sessions - they'll automatically appear in the dashboard
tmux new-session -s development
tmux new-session -s monitoring
tmux new-session -s logs

# The dashboard will display them in alphabetical order, arranged in columns
```

## Advanced Features

### Session Ordering
Sessions are displayed in **column-major order** (vertically), sorted alphabetically:
```
+----------+----------+----------+
| alpha    | gamma    | epsilon  |
+----------+----------+----------+
| beta     | delta    |          |
+----------+----------+----------+
```

### VS Code Terminal Compatibility
The dashboard intelligently detects and properly displays sessions created from VS Code's integrated terminal, even when VS Code is not in focus.

### Smart Content Capture
- Captures sufficient scrollback buffer to ensure smooth display
- Shows the bottom-most lines of each session (most recent output)
- Preserves ANSI color codes and formatting

## Troubleshooting

### Dashboard appears empty
- Ensure other tmux sessions are running
- Check that sessions aren't excluded by patterns in your config
- Verify tmux version is 3.2 or higher: `tmux -V`

### Sessions from VS Code don't display correctly
- The dashboard automatically handles VS Code terminals
- If issues persist, ensure VS Code terminal is using tmux properly

### Performance issues with many sessions
- Adjust `poll_interval_sec` in configuration (higher = less CPU usage)
- Reduce `max_fps` for smoother but less frequent updates
- Increase `min_tile_width` to show fewer tiles

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Python and the power of tmux
- Inspired by the need for better terminal session management
- Special thanks to the tmux and Python communities

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/chemitaro/tmux-dashboard/issues) on GitHub.