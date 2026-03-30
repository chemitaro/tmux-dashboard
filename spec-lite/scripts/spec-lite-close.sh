#!/bin/bash
set -eEuo pipefail

# colorized logs
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

emit_kv() {
    local key=$1
    local value=$2
    printf '%s=%s\n' "$key" "$value"
}

on_error() {
    local exit_code=$?
    log_error "spec-lite close failed (exit code: ${exit_code})"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "FAILED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "unexpected error"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
    exit "$exit_code"
}
trap on_error ERR

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$repo_root" ]]; then
    log_error "Error: Not in a git repository"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "FAILED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "not in git repo"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
    exit 1
fi
cd "$repo_root"

echo "Starting spec-lite close process..."

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log_error "Error: Not in a git repository"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "FAILED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "not in git repo"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
    exit 1
fi

mkdir -p spec-lite/completed

readonly CURRENT_DIR="spec-lite/current"
readonly TEMPLATE_DIR="spec-lite/templates"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
    log_error "Error: templates directory not found"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "FAILED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "templates directory missing"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
    exit 1
fi

if [[ -d "$CURRENT_DIR" ]]; then
    if diff -qr "$CURRENT_DIR" "$TEMPLATE_DIR" >/dev/null 2>&1; then
        log_warn "spec-lite/current matches templates. Skipping archive/copy."
        emit_kv "SPEC_LITE_CLOSE_STATUS" "SKIPPED"
        emit_kv "SPEC_LITE_CLOSE_MESSAGE" "current matches template"
        emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
        exit 0
    else
        diff_status=$?
        if [[ $diff_status -ne 1 ]]; then
            log_error "Error: diff command failed"
            emit_kv "SPEC_LITE_CLOSE_STATUS" "FAILED"
            emit_kv "SPEC_LITE_CLOSE_MESSAGE" "diff command failed"
            emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
            exit "$diff_status"
        fi
    fi
fi

archived=0
archive_dir="-"

if [[ -d "$CURRENT_DIR" ]]; then
    branch_raw=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
    if [[ -z "$branch_raw" ]] || [[ "$branch_raw" == "HEAD" ]]; then
        branch_raw=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        log_warn "Detached HEAD detected, using commit hash: $branch_raw"
    fi

    branch_name=$(echo "$branch_raw" | tr '/' '_' | tr -cs 'A-Za-z0-9._-' '_' | sed 's/_\+/_/g; s/^_//; s/_$//')

    timestamp=$(date +%Y%m%d_%H%M%S)
    archive_dir="spec-lite/completed/${timestamp}_${branch_name}"

    if [[ -d "$archive_dir" ]]; then
        counter=2
        while [[ -d "${archive_dir}_${counter}" ]]; do
            ((counter++))
        done
        archive_dir="${archive_dir}_${counter}"
    fi

    mv "$CURRENT_DIR" "$archive_dir"
    archived=1
    log_info "Archived to: $archive_dir"
else
    log_warn "No current directory to archive (will create current from templates)"
fi

cp -r "$TEMPLATE_DIR" "$CURRENT_DIR"
log_info "Templates copied to spec-lite/current"

if [[ $archived -eq 1 ]]; then
    log_info "spec-lite close completed successfully (archived)"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "ARCHIVED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "archived current and restored templates"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "$archive_dir"
else
    log_info "spec-lite close completed successfully (created)"
    emit_kv "SPEC_LITE_CLOSE_STATUS" "CREATED"
    emit_kv "SPEC_LITE_CLOSE_MESSAGE" "created current from templates"
    emit_kv "SPEC_LITE_CLOSE_ARCHIVE_DIR" "-"
fi
