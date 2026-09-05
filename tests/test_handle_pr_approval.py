"""Unit tests for handle_pr_approval script."""

import json
import os
import sys
from unittest.mock import MagicMock, call, patch
import pytest

# Add .github/scripts to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from handle_pr_approval import reconcile_post_merge, handle_pr_approval


def test_reconcile_post_merge_unmerged_pr():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"state": "OPEN", "closingIssuesReferences": [], "body": ""}),
        )
        reconcile_post_merge(10, "marius-patrik/ChessWithQuests")
        # Only the pr view command was executed
        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]
        assert "pr" in cmd and "view" in cmd


def test_reconcile_post_merge_bound_issues():
    with patch("subprocess.run") as mock_run:

        def fake_subprocess_run(args, **kwargs):
            cmd_str = " ".join(args)
            if "pr view" in cmd_str:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "state": "MERGED",
                            "closingIssuesReferences": [{"number": 101}],
                            "body": "Resolves #102 and fixes https://github.com/marius-patrik/ChessWithQuests/issues/103",
                            "url": "https://github.com/marius-patrik/ChessWithQuests/pull/10",
                        }
                    ),
                )
            elif "project view" in cmd_str:
                return MagicMock(returncode=0, stdout=json.dumps({"id": "proj-14"}))
            elif "project item-add" in cmd_str:
                return MagicMock(returncode=0, stdout=json.dumps({"id": "item-abc"}))
            elif "project item-edit" in cmd_str:
                return MagicMock(returncode=0, stdout="{}")
            elif "issue close" in cmd_str or "issue edit" in cmd_str:
                return MagicMock(returncode=0, stdout="{}")
            return MagicMock(returncode=0, stdout="{}")

        mock_run.side_effect = fake_subprocess_run

        reconcile_post_merge(10, "marius-patrik/ChessWithQuests")

        # Verify calls for issues 101, 102, 103
        executed_cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]

        # Issues should be closed
        assert any("issue close 101" in c for c in executed_cmds)
        assert any("issue close 102" in c for c in executed_cmds)
        assert any("issue close 103" in c for c in executed_cmds)

        # Issues should be tagged Done
        assert any("issue edit 101" in c and "Done" in c for c in executed_cmds)
        assert any("issue edit 102" in c and "Done" in c for c in executed_cmds)
        assert any("issue edit 103" in c and "Done" in c for c in executed_cmds)

        # Status on Project 14 should be edited to Done option ID
        assert any("project item-edit" in c and "db1d3578" in c for c in executed_cmds)


def test_handle_pr_approval_unauthorized_actor():
    env = {
        "GITHUB_EVENT_NAME": "pull_request_review",
        "GITHUB_ACTOR": "unauthorized-hacker",
        "REPO_OWNER": "marius-patrik",
        "GITHUB_REPOSITORY": "marius-patrik/ChessWithQuests",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            handle_pr_approval()
        assert exc.value.code == 0


def test_handle_pr_approval_non_approval_comment():
    env = {
        "GITHUB_EVENT_NAME": "issue_comment",
        "GITHUB_ACTOR": "marius-patrik",
        "REPO_OWNER": "marius-patrik",
        "GITHUB_REPOSITORY": "marius-patrik/ChessWithQuests",
        "IS_PR": "true",
        "PR_NUMBER": "10",
        "COMMENT_BODY": "Can you explain this change?",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            handle_pr_approval()
        assert exc.value.code == 0


def test_handle_pr_approval_issue_comment_not_pr():
    env = {
        "GITHUB_EVENT_NAME": "issue_comment",
        "GITHUB_ACTOR": "marius-patrik",
        "REPO_OWNER": "marius-patrik",
        "GITHUB_REPOSITORY": "marius-patrik/ChessWithQuests",
        "IS_PR": "false",
        "PR_NUMBER": "10",
        "COMMENT_BODY": "approve",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            handle_pr_approval()
        assert exc.value.code == 0


def test_handle_pr_approval_valid_review_flow():
    env = {
        "GITHUB_EVENT_NAME": "pull_request_review",
        "GITHUB_ACTOR": "marius-patrik",
        "REPO_OWNER": "marius-patrik",
        "GITHUB_REPOSITORY": "marius-patrik/ChessWithQuests",
        "REVIEW_STATE": "APPROVED",
        "PR_NUMBER": "25",
    }

    with patch.dict(os.environ, env, clear=True):
        with (
            patch("subprocess.run") as mock_run,
            patch("handle_pr_approval.reconcile_post_merge") as mock_reconcile,
            patch("time.sleep") as mock_sleep,
        ):

            def fake_subprocess_run(args, **kwargs):
                cmd_str = " ".join(args)
                if "pr view 25 --json isDraft,state,reviewDecision" in cmd_str:
                    return MagicMock(
                        returncode=0,
                        stdout=json.dumps(
                            {
                                "isDraft": True,
                                "state": "OPEN",
                                "reviewDecision": "REVIEW_REQUIRED",
                            }
                        ),
                    )
                elif "pr ready 25" in cmd_str:
                    return MagicMock(returncode=0, stdout="Ready")
                elif "pr review 25 --approve" in cmd_str:
                    return MagicMock(returncode=0, stdout="Approved")
                elif "pr merge 25" in cmd_str:
                    return MagicMock(returncode=0, stdout="Auto-merge enabled", stderr="")
                elif "pr view 25 --json state" in cmd_str:
                    return MagicMock(returncode=0, stdout=json.dumps({"state": "MERGED"}))
                return MagicMock(returncode=0, stdout="{}")

            mock_run.side_effect = fake_subprocess_run

            handle_pr_approval()

            executed_cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]

            # 1. Marked ready from draft
            assert any("pr ready 25" in c for c in executed_cmds)

            # 2. Approved as proxy bot
            assert any("pr review 25 --approve" in c for c in executed_cmds)

            # 3. Enabled auto-merge with --delete-branch
            assert any("pr merge 25 --auto --merge --delete-branch" in c for c in executed_cmds)

            # 4. Post-merge reconciliation called
            mock_reconcile.assert_called_once_with(25, "marius-patrik/ChessWithQuests")
