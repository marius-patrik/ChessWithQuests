"""Unit tests for Antigravity CI Agent runner and utilities."""

import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

# Add .github/scripts to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from antigravity_runner import (
    classify_type_and_area,
    format_conventional_commit,
    refresh_google_oauth_token,
    setup_antigravity_credentials,
    dispatch_event,
    is_bot_or_agent_comment,
    run_agy_prompt,
    find_parent_request_number,
    generate_branch_name,
    handle_implement,
    handle_self_review,
    handle_plan_alignment,
)


def test_classify_type_and_area():
    # Feat + Model
    t, a = classify_type_and_area("Add knight jump quest logic and piece movement")
    assert t == "feat"
    assert a == "area:model"

    # Bug + View
    t, a = classify_type_and_area("Fix rendering glitch in GUI window chessboard display")
    assert t == "bug"
    assert a == "area:view"

    # Refactor + Controller
    t, a = classify_type_and_area("Refactor controller event handler loop")
    assert t == "refactor"
    assert a == "area:controller"

    # Docs + Docs
    t, a = classify_type_and_area("Update documentation for mkdocs materials")
    assert t == "docs"
    assert a == "area:docs"

    # Chore / CI + CI
    t, a = classify_type_and_area("Update GitHub Actions workflow and docker runner")
    assert t in ("ci", "chore")
    assert a == "area:ci"

    # Test + Model
    t, a = classify_type_and_area("Add unit test for bishop piece diagonal movement")
    assert t == "test"
    assert a == "area:model"


def test_format_conventional_commit():
    assert (
        format_conventional_commit("feat", "area:ci", "Add containerized runner")
        == "feat(ci): add containerized runner"
    )
    assert (
        format_conventional_commit("bug", "area:model", "fix pawn en passant rule")
        == "fix(model): fix pawn en passant rule"
    )
    assert (
        format_conventional_commit("docs", "docs", "Update AGENTS.md rules")
        == "docs(docs): update AGENTS.md rules"
    )
    assert (
        format_conventional_commit("refactor", "controller", "simplify game loop")
        == "refactor(controller): simplify game loop"
    )


def test_refresh_google_oauth_token_success():
    fake_response = io.BytesIO(
        json.dumps(
            {"access_token": "ya29.test_token_123", "expires_in": 3600, "token_type": "Bearer"}
        ).encode("utf-8")
    )

    with patch("urllib.request.urlopen", return_value=fake_response):
        res = refresh_google_oauth_token("mock_refresh_token")
        assert res["access_token"] == "ya29.test_token_123"
        assert res["expires_in"] == 3600


def test_refresh_google_oauth_token_failure():
    error = urllib.error.HTTPError(
        url="https://oauth2.googleapis.com/token",
        code=400,
        msg="Bad Request",
        hdrs={},
        fp=io.BytesIO(b'{"error": "invalid_grant"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError) as exc_info:
            refresh_google_oauth_token("invalid_token")
        assert "Google OAuth token refresh failed" in str(exc_info.value)


def test_setup_antigravity_credentials():
    with tempfile.TemporaryDirectory() as tmpdir:
        cred_path = setup_antigravity_credentials(
            access_token="test_acc", refresh_token="test_ref", target_dir=tmpdir
        )
        assert os.path.isfile(cred_path)

        with open(cred_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "raw" in data
        assert "payload" in data
        payload = data["payload"]
        assert payload["token"]["access_token"] == "test_acc"
        assert payload["token"]["refresh_token"] == "test_ref"
        assert payload["auth_method"] == "consumer"

        # Check that fallback files are also written
        assert os.path.isfile(os.path.join(tmpdir, "tokens.json"))
        assert os.path.isfile(os.path.join(tmpdir, "token.json"))

        # Check canonical antigravity-oauth-token file
        canon_path = os.path.join(tmpdir, "antigravity-oauth-token")
        assert os.path.isfile(canon_path)
        with open(canon_path, "r", encoding="utf-8") as f:
            c_data = json.load(f)
        assert c_data["auth_method"] == "consumer"
        assert c_data["token"]["access_token"] == "test_acc"
        assert c_data["token"]["refresh_token"] == "test_ref"

        # Check settings.json initialized
        settings_path = os.path.join(tmpdir, "settings.json")
        assert os.path.isfile(settings_path)


def test_setup_antigravity_credentials_linux_keyring():
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        patch("sys.platform", "linux"),
        patch("subprocess.Popen") as mock_popen,
    ):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_popen.return_value = mock_proc

        cred_path = setup_antigravity_credentials(
            access_token="test_acc", refresh_token="test_ref", target_dir=tmpdir
        )
        assert os.path.isfile(cred_path)
        # Verify secret-tool was called with service 'gemini' and username 'antigravity'
        calls = [call[0][0] for call in mock_popen.call_args_list]
        assert any(
            cmd[0] == "secret-tool" and "gemini" in cmd and "antigravity" in cmd for cmd in calls
        )


def test_dispatch_event_unlabelled_issue():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "opened",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "issue": {
                    "number": 99,
                    "title": "Add bishop moves",
                    "body": "Need bishop piece diagonal logic",
                    "labels": [],
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with (
            patch("antigravity_runner.run_gh") as mock_gh,
            patch("antigravity_runner.run_agy_prompt", return_value="Interpretation mock"),
        ):
            mock_gh.return_value = json.dumps(
                {"title": "Add bishop moves", "body": "Need bishop piece diagonal logic"}
            )
            dispatch_event(temp_path, "issues")

            # Check that issue was edited to add Request label
            calls = [c[0][0] for c in mock_gh.call_args_list]
            assert any("Request" in " ".join(call) for call in calls)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_create_child_plan_issue():
    from antigravity_runner import create_child_plan_issue

    with patch("antigravity_runner.run_gh") as mock_gh:
        # First call views the parent request
        # Second call creates the child plan issue
        mock_gh.side_effect = [
            json.dumps({"title": "Request: Implement Queen logic", "body": "Add queen movements"}),
            "https://github.com/marius-patrik/ChessWithQuests/issues/105",
        ]
        plan_num = create_child_plan_issue(100, "marius-patrik/ChessWithQuests")
        assert plan_num == 105

        create_call = mock_gh.call_args_list[1][0][0]
        assert "issue" in create_call
        assert "create" in create_call
        assert "--parent" in create_call
        assert "100" in create_call
        assert "--label" in create_call
        assert "Plan" in create_call


def test_antigravity_files_exist():
    dockerfile = os.path.join(repo_root, "docker", "Dockerfile.antigravity")
    workflow = os.path.join(repo_root, ".github", "workflows", "antigravity-ci-agent.yml")
    issue_tmpl = os.path.join(repo_root, ".github", "ISSUE_TEMPLATE", "request.yml")
    pr_tmpl = os.path.join(repo_root, ".github", "PULL_REQUEST_TEMPLATE.md")

    assert os.path.isfile(dockerfile), "Dockerfile.antigravity must exist"
    assert os.path.isfile(workflow), "antigravity-ci-agent.yml must exist"
    assert os.path.isfile(issue_tmpl), "request.yml issue form must exist"
    assert os.path.isfile(pr_tmpl), "PULL_REQUEST_TEMPLATE.md must exist"


def test_is_bot_or_agent_comment():
    # Bot usernames
    assert is_bot_or_agent_comment("github-actions[bot]", "Any message") is True
    assert is_bot_or_agent_comment("dependabot[bot]", "Bump version") is True
    assert is_bot_or_agent_comment("app/github-actions", "Automated trigger") is True
    assert is_bot_or_agent_comment("github-actions", "Automated trigger") is True

    # Agent markers in body (even if user is human PAT owner)
    assert is_bot_or_agent_comment("marius-patrik", "### Antigravity Agent: Interpretation") is True
    assert is_bot_or_agent_comment("marius-patrik", "### Implementation Plan for #36") is True
    assert (
        is_bot_or_agent_comment("marius-patrik", "### Implementation Review\nMatches Plan: Yes")
        is True
    )
    assert is_bot_or_agent_comment("marius-patrik", "[Antigravity Agent] processed prompt") is True
    assert is_bot_or_agent_comment("marius-patrik", "This is autogenerated by antigravity") is True
    assert is_bot_or_agent_comment("marius-patrik", "<!-- antigravity-agent --> hidden tag") is True

    # Genuine human comments
    assert is_bot_or_agent_comment("marius-patrik", "approve") is False
    assert is_bot_or_agent_comment("marius-patrik", "Please update the verification plan") is False
    assert is_bot_or_agent_comment("other-dev", "Looks good to me!") is False


def test_run_agy_prompt_error_handling():
    # FileNotFoundError (binary missing)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        res = run_agy_prompt("test prompt")
        assert res.startswith("[Antigravity Agent Execution Error]")
        assert "not found in PATH" in res

    # CalledProcessError (binary failed)
    err = subprocess.CalledProcessError(
        returncode=1, cmd=["agy"], stderr="Keyring authorization denied."
    )
    with patch("subprocess.run", side_effect=err):
        res = run_agy_prompt("test prompt")
        assert res.startswith("[Antigravity Agent Execution Error]")
        assert "Keyring authorization denied" in res

    # Success
    mock_res = MagicMock(stdout="Valid generated response\n")
    with patch("subprocess.run", return_value=mock_res):
        res = run_agy_prompt("test prompt")
        assert res == "Valid generated response"


def test_dispatch_event_pull_request_review_comment_human():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "pull_request": {"number": 42},
                "comment": {
                    "body": "Can you check line 50?",
                    "user": {"login": "marius-patrik"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with patch("antigravity_runner.handle_respond") as mock_respond:
            dispatch_event(temp_path, "pull_request_review_comment")
            mock_respond.assert_called_once_with(
                42, "Can you check line 50?", repo="marius-patrik/ChessWithQuests", is_pr=True
            )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_dispatch_event_pull_request_review_comment_bot_suppression():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "pull_request": {"number": 42},
                "comment": {
                    "body": "### Antigravity Agent\nAutomated review notice",
                    "user": {"login": "marius-patrik"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with patch("antigravity_runner.handle_respond") as mock_respond:
            dispatch_event(temp_path, "pull_request_review_comment")
            mock_respond.assert_not_called()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_dispatch_event_issue_comment_agent_loop_suppressed():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "issue": {
                    "number": 15,
                    "labels": [{"name": "Request"}],
                },
                "comment": {
                    "body": "### Antigravity Agent\nInterpreting user request...",
                    "user": {"login": "marius-patrik"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with (
            patch("antigravity_runner.handle_respond") as mock_respond,
            patch("antigravity_runner.handle_plan") as mock_plan,
        ):
            dispatch_event(temp_path, "issue_comment")
            mock_respond.assert_not_called()
            mock_plan.assert_not_called()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_generate_branch_name():
    # Strips Plan: and Request: prefixes
    assert (
        generate_branch_name("Plan: Add link to docs and diagram in README")
        == "feature/add-link-to-docs-and-diagram-in-readme"
    )
    assert (
        generate_branch_name("Request: Docs page should dynamically incorporate notes")
        == "feature/docs-page-should-dynamically-incorporate-notes"
    )
    # Strips issue numbers per AGENTS.md §7
    assert (
        generate_branch_name("Plan: Fix issue #39 with parser") == "feature/fix-issue-with-parser"
    )
    # Normalizes special characters and consecutive dashes
    assert (
        generate_branch_name("Plan: Add .claude folder @ root symlinking .agents!!")
        == "feature/add-claude-folder-root-symlinking-agents"
    )


def test_find_parent_request_number():
    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps(
            {"body": "Implementation plan.\n\nParent Request: #42\nDetails..."}
        )
        assert find_parent_request_number(43, "test/repo") == 42

    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps({"body": "Plan with no parent reference."})
        assert find_parent_request_number(43, "test/repo") is None


def test_dispatch_event_plan_approval():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "issue": {
                    "number": 43,
                    "labels": [{"name": "Plan"}],
                },
                "comment": {
                    "body": "approve",
                    "user": {"login": "marius-patrik"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with (
            patch("antigravity_runner.find_parent_request_number", return_value=42) as mock_find,
            patch("antigravity_runner.handle_implement") as mock_implement,
        ):
            dispatch_event(temp_path, "issue_comment")
            mock_find.assert_called_once_with(43, "marius-patrik/ChessWithQuests")
            mock_implement.assert_called_once_with(43, 42, "marius-patrik/ChessWithQuests")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_handle_self_review_clean():
    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
    ):
        mock_gh.side_effect = [
            "diff --git a/test.py b/test.py\n+print('hello')",  # pr diff
            json.dumps({"body": "Plan details"}),  # issue view (plan)
            "",  # pr comment (clean)
        ]
        mock_agy.return_value = "NO_FINDINGS: All code looks great."

        handle_self_review(pr_number=50, plan_number=43, repo="test/repo")

        # Verify comment on PR
        mock_gh.assert_any_call(
            [
                "pr",
                "comment",
                "50",
                "--body",
                "<!-- antigravity-agent -->\n### Self-Review Findings (Iteration 1)\n\n✅ No actionable findings. Code review passed.",
            ],
            repo="test/repo",
        )


def test_handle_self_review_with_findings_and_out_of_scope_deviation():
    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
        patch("antigravity_runner.find_parent_request_number", return_value=42) as mock_parent,
        patch("subprocess.run") as mock_subproc,
        patch("antigravity_runner.run_git") as mock_git,
    ):
        mock_gh.side_effect = [
            "diff content",  # pr diff (iter 1)
            json.dumps({"body": "Plan details"}),  # plan view (iter 1)
            "",  # pr comment (findings)
            "",  # issue comment on request (deviation)
            "",  # issue comment on plan (scope amendment)
            "",  # pr comment (fix)
            "clean diff",  # pr diff (iter 2)
            json.dumps({"body": "Plan details"}),  # plan view (iter 2)
            "",  # pr comment (clean)
        ]
        mock_agy.side_effect = [
            "OUT_OF_SCOPE: Missing database migration script.",  # review result
            "Need to add migration script because schema changed.",  # deviation text
            "Added migration script and verified.",  # fix result
            "NO_FINDINGS: All code looks great now.",  # review result iter 2
        ]
        mock_git.side_effect = [
            "",  # git add
            "M db/migration.py",  # git status
            "",  # git commit
            "",  # git push
        ]

        handle_self_review(pr_number=50, plan_number=43, repo="test/repo")

        # Verify deviation comment posted on Request issue #42
        mock_gh.assert_any_call(
            [
                "issue",
                "comment",
                "42",
                "--body",
                "<!-- antigravity-agent -->\n### Plan Deviation\n\nNeed to add migration script because schema changed.",
            ],
            repo="test/repo",
        )
        # Verify scope amendment posted on Plan issue #43
        mock_gh.assert_any_call(
            [
                "issue",
                "comment",
                "43",
                "--body",
                "<!-- antigravity-agent -->\n### Scope Amendment\n\nNeed to add migration script because schema changed.",
            ],
            repo="test/repo",
        )


def test_handle_plan_alignment_matching():
    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
    ):
        mock_gh.side_effect = [
            "diff content",  # pr diff
            json.dumps({"body": "Plan details", "comments": []}),  # plan view
            "",  # issue comment (Matches Plan: Yes)
            "",  # pr ready
        ]
        mock_agy.return_value = "MATCHES_PLAN_YES: All changes align with the plan."

        handle_plan_alignment(pr_number=50, plan_number=43, request_number=42, repo="test/repo")

        # Verify Implementation Review posted on Plan issue
        mock_gh.assert_any_call(
            [
                "issue",
                "comment",
                "43",
                "--body",
                "<!-- antigravity-agent -->\n### Implementation Review\n\n**Matches Plan**: Yes\n\nAll changes in the PR align with the plan scope.",
            ],
            repo="test/repo",
        )
        # Verify PR marked ready
        mock_gh.assert_any_call(["pr", "ready", "50"], repo="test/repo")


def test_handle_plan_alignment_divergence():
    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
    ):
        mock_gh.side_effect = [
            "diff content",  # pr diff
            json.dumps({"body": "Plan details", "comments": []}),  # plan view
            "",  # issue comment on request (Plan Alignment)
            "",  # issue comment on plan (Matches Plan: No)
        ]
        mock_agy.return_value = "Divergence found: Added extra endpoint /debug not in plan."

        handle_plan_alignment(pr_number=50, plan_number=43, request_number=42, repo="test/repo")

        # Verify deviation posted on Request issue #42
        mock_gh.assert_any_call(
            [
                "issue",
                "comment",
                "42",
                "--body",
                "<!-- antigravity-agent -->\n### Plan Alignment\n\nDivergence found: Added extra endpoint /debug not in plan.",
            ],
            repo="test/repo",
        )
        # Verify Matches Plan: No posted on Plan issue #43
        mock_gh.assert_any_call(
            [
                "issue",
                "comment",
                "43",
                "--body",
                "<!-- antigravity-agent -->\n### Implementation Review\n\n**Matches Plan**: No\n\nDivergence found: Added extra endpoint /debug not in plan.",
            ],
            repo="test/repo",
        )
