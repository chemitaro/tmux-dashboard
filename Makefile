UV ?= uv
PY ?= python3
CONFIG ?= $(if $(wildcard $(CURDIR)/configs/dashboard.yaml),$(CURDIR)/configs/dashboard.yaml,$(HOME)/.config/tmux-dashboard/config.yaml)
PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
BIN ?= tmux-dashboard
BIN_SCRIPT ?= $(CURDIR)/$(BIN)

.PHONY: help doctor install uninstall start run attach stop

## help: Show available targets
help:
	@grep -E '^## ' Makefile | sed 's/^## //'

## doctor: Check environment and report issues with guidance
doctor:
	@set -e; problems=0; \
	if ! command -v tmux >/dev/null 2>&1; then \
		echo 'ERROR: tmux not found. Install tmux (3.2+ recommended).'; problems=1; \
	else \
		v=$$(tmux -V | awk '{print $$2}'); \
		maj=$${v%%.*}; min=$${v#*.}; min=$${min%%[^0-9]*}; \
		if [ $$maj -lt 3 ] || { [ $$maj -eq 3 ] && [ $$min -lt 2 ]; }; then \
			echo "WARN: tmux $$v detected. tmux 3.2+ is recommended."; \
		else \
			echo "OK: tmux $$v"; \
		fi; \
	fi; \
	if ! command -v $(UV) >/dev/null 2>&1; then \
		echo 'ERROR: uv not found. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh'; problems=1; \
	else \
		echo 'OK: uv found'; \
	fi; \
	if ! $(PY) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then \
		echo 'ERROR: Python 3.10+ required.'; problems=1; \
	else \
		echo 'OK: Python >=3.10'; \
	fi; \
	if [ ! -x "$(CURDIR)/.venv/bin/python" ]; then \
		echo 'ERROR: repo virtualenv is missing or incomplete (.venv/bin/python not found).'; problems=1; \
	elif ! (cd "$(CURDIR)" && "$(CURDIR)/.venv/bin/python" -c 'import yaml, libtmux, tmux_dashboard') >/dev/null 2>&1; then \
		echo 'ERROR: repo virtualenv is broken (cannot import PyYAML/libtmux/tmux_dashboard).'; \
		echo 'INFO: repair with: cd "$(CURDIR)" && rm -rf .venv && UV_CACHE_DIR="$(CURDIR)/.tmp/uv-cache" $(UV) sync --locked'; \
		problems=1; \
	else \
		echo 'OK: repo virtualenv imports are healthy'; \
	fi; \
	if [ -f "$(CONFIG)" ]; then \
		echo "OK: config found -> $(CONFIG)"; \
	else \
		echo 'INFO: no config found. You can copy configs/dashboard.example.yaml to ~/.config/tmux-dashboard/config.yaml'; \
	fi; \
	if [ $$problems -eq 0 ]; then \
		echo 'All checks passed.'; \
	else \
		echo 'Found issues above. Please fix them and re-run make doctor.'; exit 1; \
	fi

## start: Start dashboard runner and display dashboard:0 (no dependency sync)
start:
	@./tmux-dashboard --config "$(CONFIG)"

## install: Install tmux-dashboard command to /usr/local/bin (may require sudo)
install:
	$(UV) sync --locked
	@chmod +x "$(BIN_SCRIPT)"
	@if [ -w "$(BINDIR)" ]; then \
		ln -sf "$(BIN_SCRIPT)" "$(BINDIR)/$(BIN)"; \
	else \
		echo "INFO: $(BINDIR) is not writable; trying sudo..."; \
		sudo ln -sf "$(BIN_SCRIPT)" "$(BINDIR)/$(BIN)"; \
	fi
	@echo "OK: installed $(BINDIR)/$(BIN) -> $(BIN_SCRIPT)"

## uninstall: Remove tmux-dashboard command from /usr/local/bin (may require sudo)
uninstall:
	@if [ -e "$(BINDIR)/$(BIN)" ] || [ -L "$(BINDIR)/$(BIN)" ]; then \
		if [ -w "$(BINDIR)" ]; then \
			rm -f "$(BINDIR)/$(BIN)"; \
		else \
			echo "INFO: $(BINDIR) is not writable; trying sudo..."; \
			sudo rm -f "$(BINDIR)/$(BIN)"; \
		fi; \
		echo "OK: removed $(BINDIR)/$(BIN)"; \
	else \
		echo "INFO: not installed: $(BINDIR)/$(BIN)"; \
	fi

## run: Sync dependencies and run dashboard in foreground
run:
	$(UV) sync
	$(UV) run $(PY) -m tmux_dashboard --config "$(CONFIG)"

## attach: Attach to dashboard session (create if missing)
attach:
	tmux attach -t dashboard || tmux new -A -s dashboard

## stop: Terminate the dashboard session
stop:
	- tmux kill-session -t dashboard || true
