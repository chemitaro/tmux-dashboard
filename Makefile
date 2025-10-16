UV ?= uv
PY ?= python3
LOG_PATH ?= $(HOME)/.local/state/tmux-dashboard/runner.out
CONFIG ?= $(if $(wildcard $(CURDIR)/configs/dashboard.yaml),$(CURDIR)/configs/dashboard.yaml,$(HOME)/.config/tmux-dashboard/config.yaml)
TIMEOUT_SEC ?= 8

.PHONY: help doctor start run attach stop

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

## start: Sync dependencies, launch dashboard in background, then attach
start:
	$(UV) sync
	@mkdir -p $$(dirname $(LOG_PATH))
	@nohup $(UV) run $(PY) -m tmux_dashboard --config "$(CONFIG)" >>$(LOG_PATH) 2>&1 &
	@end=$$(( $$(date +%s) + $(TIMEOUT_SEC) )); \
	while ! tmux has-session -t dashboard 2>/dev/null; do \
		[ $$(date +%s) -lt $$end ] || { echo 'Timeout: dashboard session not ready.'; exit 1; }; \
		sleep 0.2; \
	done; \
	printf 'dashboard session ready. attaching...\n'; \
	exec tmux attach -t dashboard

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
