# tmux-dashboard

Transform your tmux experience with a real-time, bird's-eye view of all your terminal sessions. Never lose track of what's happening across your development environment again.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![tmux](https://img.shields.io/badge/tmux-3.2%2B-green)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Why tmux-dashboard?

If you're a developer who:
- Works with multiple tmux sessions simultaneously
- Struggles to keep track of various background processes
- Needs to monitor logs, builds, and tests across different sessions
- Uses VS Code's integrated terminal with tmux
- Wants a clean, organized view of your entire terminal workspace

Then tmux-dashboard is built for you. It provides a **live, tiled dashboard** that displays all your tmux sessions at once, updating in real-time as your processes run.

## Key Features

### 🎯 Smart Session Display
- **Automatic Detection**: Discovers all tmux sessions instantly (excluding the dashboard itself)
- **Intelligent Content Capture**: Shows the most recent output (bottom lines) - what matters most
- **Column-Major Layout**: Sessions arranged vertically for natural reading flow
- **Alphabetical Ordering**: Predictable, organized session arrangement

### 🎨 Visual Excellence
- **Color Preservation**: Full ANSI and TrueColor support - your terminal colors remain intact
- **Clean Borders**: Each session clearly labeled with its name
- **Responsive Grid**: Automatically adjusts when you resize your terminal
- **Smart Clipping**: Content fits perfectly within each tile

### 💪 Robust Design
- **VS Code Compatible**: Works seamlessly with VS Code's integrated terminal
- **Non-Invasive**: Never modifies your global tmux configuration
- **Auto-Creation**: Dashboard session created automatically on startup
- **Real-Time Updates**: Configurable refresh rate (default: 2 seconds)
- **Efficient**: Smart buffering and frame dropping for smooth performance

## How It Works

tmux-dashboard creates a special tmux session called "dashboard" that acts as your command center. Each tile in the dashboard is a live view of another tmux session, continuously updated using tmux's `capture-pane` functionality. The tool uses intelligent pane scanning to ensure content is displayed even when sessions are inactive (like in VS Code terminals).

## Installation

1. Install [uv](https://github.com/astral-sh/uv) (fast Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone https://github.com/chemitaro/tmux-dashboard.git
cd tmux-dashboard
```

3. Install the global command (includes dependency sync, may require sudo):
```bash
make install
```

> Note:
> - `make install` creates a symlink to this repository's `./tmux-dashboard` script.
>   If you move or delete the repository, the `tmux-dashboard` command will break — re-run `make install`.
> - On Apple Silicon Homebrew, you may want `make install PREFIX=/opt/homebrew` (or `PREFIX="$(brew --prefix)"`).
> - Runtime does not call `uv`; the wrapper launches the repo-local `.venv/bin/python` directly.
> - If `uv` cache access is restricted on your machine, use a safe local cache during setup:
>   `UV_CACHE_DIR="$(pwd)/.tmp/uv-cache" uv sync --locked`

## Quick Start

Install a global command (to `/usr/local/bin`, may require sudo):
```bash
make install
```

To uninstall:
```bash
make uninstall
```

Then run from anywhere:
```bash
tmux-dashboard
```

Alternatively, run directly via uv:
```bash
uv run python -m tmux_dashboard
```

Or run directly via the repo virtualenv:
```bash
.venv/bin/python -m tmux_dashboard
```

The dashboard will:
1. Create a "dashboard" tmux session automatically
2. Detect all your existing tmux sessions
3. Display them in a beautiful tiled layout
4. Update continuously as you work

To view the dashboard:
```bash
tmux attach -t dashboard
```

To stop (runner exits when the session is killed):
```bash
tmux kill-session -t dashboard
```

## Real-World Usage

### Development Workflow
```bash
# Start your development sessions
tmux new-session -d -s backend 'npm run dev'
tmux new-session -d -s frontend 'yarn start'
tmux new-session -d -s tests 'pytest --watch'
tmux new-session -d -s logs 'tail -f app.log'

# Launch the dashboard to monitor everything
uv run python -m tmux_dashboard

# Attach to see all sessions at once
tmux attach -t dashboard
```

### Session Layout Example
```
┌─────────────┬─────────────┬─────────────┐
│   backend   │   frontend  │    logs     │
│             │             │             │
│ Server      │ webpack 5.1 │ [INFO] App  │
│ running on  │ compiled    │ started     │
│ port 3000   │ successfully│ [DEBUG] ... │
├─────────────┼─────────────┼─────────────┤
│   tests     │             │             │
│             │             │             │
│ ......✓     │             │             │
│ 15 passed   │             │             │
└─────────────┴─────────────┴─────────────┘
```

## Configuration

Create a custom configuration file:
```bash
cp configs/dashboard.example.yaml ~/.config/tmux-dashboard/config.yaml
```

### Key Settings

```yaml
# Minimum width for each tile (columns)
min_tile_width: 40

# Update interval (seconds)
poll_interval_sec: 2

# Exclude patterns (regex)
exclude_patterns:
  - "^dashboard$"    # Don't show the dashboard itself
  - "^temp-.*"       # Ignore temporary sessions

# Display optimization
viewer:
  max_fps: 30                      # Smooth updates without overload
  capture_buffer_multiplier: 2.0   # Buffer size for scrollback
  truecolor: true                  # Enable 24-bit colors

# Logging
logging:
  level: "INFO"
  dir: "~/.local/state/tmux-dashboard"
```

## Advanced Features

### Column-Major Ordering
Sessions are arranged top-to-bottom, then left-to-right:
- Better for reading terminal output
- Groups related sessions naturally
- Maintains spatial consistency

### VS Code Terminal Support
The dashboard uses intelligent pane scanning to detect and display content from VS Code integrated terminals, even when VS Code is minimized or unfocused. This ensures you never miss important output.

### Performance Optimization
- **Smart Buffering**: Captures just enough scrollback for smooth display
- **Frame Dropping**: Maintains responsiveness under high load
- **Differential Updates**: Only redraws changed content
- **Configurable FPS**: Balance between smoothness and CPU usage

## Command-Line Options

```bash
# Use custom configuration
uv run python -m tmux_dashboard --config ~/my-config.yaml

# Run specific iterations (for testing)
uv run python -m tmux_dashboard --once --iterations 5

# Target different window
uv run python -m tmux_dashboard --window-target dashboard:1
```

## Troubleshooting

### Dashboard is empty
- Ensure you have other tmux sessions running
- Check exclude patterns in your configuration
- Verify: `tmux list-sessions`

### Wrapper exits before attach
- Run `make doctor` first. It now checks `.venv` import health, not just binary presence.
- If you see `broken virtualenv`, rebuild the environment:
```bash
rm -rf .venv
UV_CACHE_DIR="$(pwd)/.tmp/uv-cache" uv sync --locked
```
- If the wrapper reports `runner bootstrap failed before attach`, inspect the runner pane output shown on stderr and retry with:
```bash
.venv/bin/python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1
```

### `uv` works in one environment but not on this machine
- Some local setups point `uv` cache to a protected or external volume.
- Check whether `uv run ...` fails with an `Operation not permitted` error under a cache path such as `/Volumes/.../.cache/uv`.
- If so, use a writable local cache for setup and repair commands:
```bash
UV_CACHE_DIR="$(pwd)/.tmp/uv-cache" uv sync --locked
```

### High CPU usage
- Increase `poll_interval_sec` (e.g., to 5 seconds)
- Reduce `max_fps` (e.g., to 10)
- Increase `min_tile_width` to show fewer tiles

### Colors not displaying correctly
- Ensure your terminal supports TrueColor
- Try setting `truecolor: false` in config for 256-color mode
- Check your TERM environment variable

## Why Choose tmux-dashboard?

- **Zero Learning Curve**: If you know tmux, you're ready to go
- **Non-Intrusive**: Doesn't modify your tmux configuration or workflow
- **Lightweight**: Pure Python with minimal dependencies
- **Reliable**: Robust error handling and automatic recovery
- **Open Source**: MIT licensed, free to use and modify

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or request features via [Issues](https://github.com/chemitaro/tmux-dashboard/issues)
- Submit pull requests with improvements
- Share your use cases and configuration tips

## License

MIT License - Copyright (c) 2025 chemitaro

## Acknowledgments

Built with ❤️ for the terminal enthusiast community. Special thanks to:
- The tmux maintainers for an incredible terminal multiplexer
- The Python community for excellent libraries
- All contributors and users who make this project better

---

**Start monitoring your tmux sessions like a pro. Install tmux-dashboard today!**
