#!/usr/bin/env python3
"""Validate commit author and committer identities supplied as TSV."""

from __future__ import annotations

import sys


PLACEHOLDER_NAMES = {"codex", "codex-agent", "Codex Agent"}
CANONICAL_USER_EMAIL = "84865385+chemitaro@users.noreply.github.com"


def invalid_reason(name: str, email: str) -> str | None:
    """Return why an identity is an unapproved local placeholder."""

    if name in PLACEHOLDER_NAMES:
        return "known Codex placeholder name"
    if name == "chemitaro" and email != CANONICAL_USER_EMAIL:
        return "canonical email required"
    if "@" not in email:
        return "email is not an address"
    if email.endswith("@local") or email.endswith(".invalid"):
        return "local placeholder email"
    return None


def main() -> int:
    """Read five-column identity records and reject placeholder identities."""

    failed = False
    for line_number, line in enumerate(sys.stdin, start=1):
        fields = line.rstrip("\n").split("\t")
        if len(fields) != 5:
            print(f"line {line_number}: expected 5 TSV fields", file=sys.stderr)
            return 2
        commit, author_name, author_email, committer_name, committer_email = fields
        for role, name, email in (
            ("author", author_name, author_email),
            ("committer", committer_name, committer_email),
        ):
            reason = invalid_reason(name, email)
            if reason is not None:
                print(
                    f"{commit} {role}: {name} <{email}>: {reason}",
                    file=sys.stderr,
                )
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
