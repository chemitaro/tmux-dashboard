"""commit identity検査CLIの外部挙動を検証する。"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_commit_identities.py")


def run_checker(records: str) -> subprocess.CompletedProcess[str]:
    """TSV形式のcommit identityを公開CLIへ渡す。"""

    return subprocess.run(
        ["python3", str(SCRIPT)],
        input=records,
        text=True,
        capture_output=True,
        check=False,
    )


class CheckCommitIdentitiesTest(unittest.TestCase):
    """許可・拒否されるidentity境界を検証する。"""

    def test_canonical_user_and_github_committer_are_accepted(self) -> None:
        """正規user authorとGitHub committerは成功終了する。"""

        result = run_checker(
            "abc123\tchemitaro\t84865385+chemitaro@users.noreply.github.com"
            "\tGitHub\tnoreply@github.com\n"
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_known_codex_placeholder_identities_are_rejected(self) -> None:
        """過去に混入したCodex placeholder identityは失敗終了する。"""

        result = run_checker(
            "logger\tcodex-agent\tcodex-agent@local.invalid"
            "\tcodex-agent\tcodex-agent@local.invalid\n"
            "tmux\tCodex Agent\tcodex-agent@local"
            "\tCodex Agent\tcodex-agent@local\n"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("logger author", result.stderr)
        self.assertIn("tmux committer", result.stderr)

    def test_chemitaro_with_noncanonical_email_is_rejected(self) -> None:
        """chemitaro名義は正規GitHub noreply email以外を拒否する。"""

        result = run_checker(
            "bad-user\tchemitaro\tiwasi_44@hotmail.com"
            "\tchemitaro\tchemitaro\n"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical email required", result.stderr)

    def test_approved_service_identities_are_accepted(self) -> None:
        """GitHub、Dependabot、既存close Botのidentityは維持して許可する。"""

        result = run_checker(
            "github\tweb-flow\tnoreply@github.com\tGitHub\tnoreply@github.com\n"
            "dependabot\tdependabot[bot]\t49699333+dependabot[bot]@users.noreply.github.com"
            "\tGitHub\tnoreply@github.com\n"
            "close-bot\tspec-lite-close-bot"
            "\tspec-lite-close-bot@users.noreply.github.com"
            "\tspec-lite-close-bot\tspec-lite-close-bot@users.noreply.github.com\n"
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
