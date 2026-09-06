"""Unit tests for Antigravity CI Agent runner and utilities."""

import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch, ANY
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
    is_quota_exhausted,
    calculate_backoff,
    get_model_fallback_chain,
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    update_project_status_blocked,
    checkpoint_and_notify_exhaustion,
    DEFAULT_MODEL_FALLBACK_CHAIN,
    CHECKPOINT_FILENAME,
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
    # 1. Classic "Parent Request: #42"
    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps(
            {"body": "Implementation plan.\n\nParent Request: #42\nDetails..."}
        )
        assert find_parent_request_number(43, "test/repo") == 42

    # 2. Native GitHub sub-issue parent metadata
    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps({"body": "Plan body", "parent": {"number": 99}})
        assert find_parent_request_number(43, "test/repo") == 99

    # 3. "Linked Parent: #55" or "Parent Request #55" (no colon)
    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps(
            {"body": "Implementation plan for Parent Request #55.\n\nLinked Parent: #55"}
        )
        assert find_parent_request_number(43, "test/repo") == 55

    # 4. In comments
    with patch("antigravity_runner.run_gh") as mock_gh:
        mock_gh.return_value = json.dumps(
            {
                "body": "Plan body",
                "comments": [{"body": "- **Parent Request**: #77"}],
            }
        )
        assert find_parent_request_number(43, "test/repo") == 77

    # 5. No parent reference
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


def test_is_quota_exhausted_detection():
    # Quota and rate limit errors
    assert is_quota_exhausted("Error: 429 Too Many Requests") is True
    assert is_quota_exhausted("Status code: 429") is True
    assert (
        is_quota_exhausted("google.api_core.exceptions.ResourceExhausted: 429 Resource exhausted")
        is True
    )
    assert is_quota_exhausted("RESOURCE_EXHAUSTED: Quota exceeded for metric") is True
    assert is_quota_exhausted("You have exceeded your current quota.") is True
    assert is_quota_exhausted("Quota exceeded for quota metric 'GenerateContent'") is True
    assert is_quota_exhausted("insufficient quota for model execution") is True
    assert is_quota_exhausted("Out of quota. Please check your billing plan.") is True
    assert is_quota_exhausted("Rate limit reached for gemini-3.8-flash-high") is True
    assert is_quota_exhausted("Rate-limit exceeded: 15 RPM") is True
    assert is_quota_exhausted("Hit ratelimit, please slow down") is True
    assert is_quota_exhausted("Too many requests sent to backend") is True
    assert is_quota_exhausted("The requested model is unavailable") is True
    assert is_quota_exhausted("model unavailable at this time") is True
    assert is_quota_exhausted("Model overloaded. Please try again shortly.") is True
    assert is_quota_exhausted("Server is overloaded.") is True

    # Non-quota errors must return False
    assert is_quota_exhausted("Keyring authorization denied.") is False
    assert (
        is_quota_exhausted(
            "[Antigravity Agent Execution Error]: `agy` CLI binary not found in PATH."
        )
        is False
    )
    assert is_quota_exhausted("SyntaxError: invalid syntax in file.py") is False
    assert (
        is_quota_exhausted("fatal: not a git repository (or any of the parent directories)")
        is False
    )
    assert is_quota_exhausted("Unrecognized argument: --invalid-flag") is False
    assert is_quota_exhausted("") is False


def test_calculate_backoff_exponential_and_jitter():
    # Deterministic exponential delays without jitter
    assert calculate_backoff(0, base_delay=1.0, backoff_factor=2.0, jitter=False) == 1.0
    assert calculate_backoff(1, base_delay=1.0, backoff_factor=2.0, jitter=False) == 2.0
    assert calculate_backoff(2, base_delay=1.0, backoff_factor=2.0, jitter=False) == 4.0
    assert calculate_backoff(3, base_delay=1.0, backoff_factor=2.0, jitter=False) == 8.0

    # Max delay cap
    assert (
        calculate_backoff(10, base_delay=1.0, backoff_factor=2.0, max_delay=15.0, jitter=False)
        == 15.0
    )

    # Jitter range
    for attempt in range(4):
        base = 1.0 * (2.0**attempt)
        val = calculate_backoff(
            attempt, base_delay=1.0, backoff_factor=2.0, jitter=True, jitter_factor=0.5
        )
        assert val >= base
        assert val <= base * 1.5 + 0.001


def test_run_agy_prompt_transient_retry_and_backoff():
    # Model fails with 429 on first attempt, succeeds on second attempt
    err_429 = subprocess.CalledProcessError(
        returncode=1, cmd=["agy"], stderr="429 ResourceExhausted: Quota limit hit"
    )
    success_mock = MagicMock(stdout="Recovered response after transient 429")

    with (
        patch("subprocess.run", side_effect=[err_429, success_mock]) as mock_subproc,
        patch("time.sleep") as mock_sleep,
    ):
        result = run_agy_prompt(
            "Test prompt",
            model="gemini-3.8-flash-high",
            max_retries=2,
            base_delay=0.1,
            backoff_factor=2.0,
        )
        assert result == "Recovered response after transient 429"
        assert mock_subproc.call_count == 2
        assert mock_sleep.call_count == 1
        # Both attempts should use the primary model without escalating
        for call_args in mock_subproc.call_args_list:
            cmd = call_args[0][0]
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "gemini-3.8-flash-high"


def test_get_model_fallback_chain():
    # Default fallback chain
    chain = get_model_fallback_chain()
    assert chain == [
        "gemini-3.8-flash-high",
        "claude-opus-4-6-thinking",
    ]

    # Starting with a specific tier from the chain
    chain_mid = get_model_fallback_chain("claude-opus-4-6-thinking")
    assert chain_mid == ["claude-opus-4-6-thinking"]

    # Custom chain override
    custom = ["custom-model-1", "custom-model-2"]
    assert get_model_fallback_chain(custom_chain=custom) == custom


def test_run_agy_prompt_model_fallback_escalation():
    # Primary model (gemini-3.8-flash-high) exhausts retries with 429,
    # then fallback model (claude-opus-4-6-thinking) succeeds
    err_exhausted = subprocess.CalledProcessError(
        returncode=1, cmd=["agy"], stderr="429 Quota exceeded for gemini-3.8-flash-high"
    )
    success_fallback = MagicMock(stdout="Output generated by fallback model")

    # Primary attempts: 2 (attempt 0, attempt 1 with max_retries=1)
    # Secondary attempt: 1 (succeeds)
    with (
        patch(
            "subprocess.run",
            side_effect=[err_exhausted, err_exhausted, success_fallback],
        ) as mock_subproc,
        patch("time.sleep"),
    ):
        result = run_agy_prompt(
            "Implement feature",
            model="gemini-3.8-flash-high",
            max_retries=1,
            base_delay=0.001,
        )
        assert result == "Output generated by fallback model"
        assert mock_subproc.call_count == 3

        # Verify models used in call sequence
        calls = mock_subproc.call_args_list
        model_1 = calls[0][0][0][calls[0][0][0].index("--model") + 1]
        model_2 = calls[1][0][0][calls[1][0][0].index("--model") + 1]
        model_3 = calls[2][0][0][calls[2][0][0].index("--model") + 1]

        assert model_1 == "gemini-3.8-flash-high"
        assert model_2 == "gemini-3.8-flash-high"
        assert model_3 == "claude-opus-4-6-thinking"


def test_run_agy_prompt_non_quota_error_no_fallback():
    # Non-quota error should abort immediately without retrying or falling back
    err_syntax = subprocess.CalledProcessError(
        returncode=2, cmd=["agy"], stderr="Unrecognized argument: --bogus"
    )
    with (
        patch("subprocess.run", side_effect=err_syntax) as mock_subproc,
        patch("time.sleep") as mock_sleep,
    ):
        result = run_agy_prompt("Test prompt", model="gemini-3.8-flash-high", max_retries=2)
        assert result.startswith("[Antigravity Agent Execution Error]")
        assert "Unrecognized argument: --bogus" in result
        assert mock_subproc.call_count == 1
        assert mock_sleep.call_count == 0


def test_save_load_clear_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Load from empty directory
        assert load_checkpoint(cwd=tmpdir) is None

        # Save checkpoint
        payload = {
            "issue_number": 42,
            "status": "Blocked",
            "completed_steps": ["Step 1", "Step 2"],
        }
        path = save_checkpoint(payload, cwd=tmpdir)
        assert os.path.isfile(path)

        # Load checkpoint
        loaded = load_checkpoint(cwd=tmpdir)
        assert loaded is not None
        assert loaded["issue_number"] == 42
        assert loaded["status"] == "Blocked"
        assert loaded["completed_steps"] == ["Step 1", "Step 2"]

        # Clear checkpoint
        clear_checkpoint(cwd=tmpdir)
        assert load_checkpoint(cwd=tmpdir) is None


def test_checkpoint_and_notify_exhaustion():
    class MockClient:
        def __init__(self):
            self.added_urls = []
            self.edited_statuses = []

        def add_item(self, url):
            self.added_urls.append(url)
            return "item-101"

        def edit_status(self, item_id, status):
            self.edited_statuses.append((item_id, status))
            return True

    mock_client = MockClient()

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("antigravity_runner.run_gh") as mock_gh,
            patch("antigravity_runner.run_git") as mock_git,
        ):
            mock_git.side_effect = ["", "M src/file.py", "", ""]  # add, status, commit, push

            data = checkpoint_and_notify_exhaustion(
                issue_number=67,
                repo="marius-patrik/ChessWithQuests",
                completed_steps=["Step A: Read request", "Step B: Created branch"],
                branch_name="feature/test-quota",
                is_pr=False,
                error_detail="429 Quota exhausted on all fallback models",
                cwd=tmpdir,
                client=mock_client,
            )

            # 1. Verify checkpoint file
            assert os.path.isfile(os.path.join(tmpdir, CHECKPOINT_FILENAME))
            assert data["status"] == "Blocked"
            assert data["issue_number"] == 67
            assert "Step A: Read request" in data["completed_steps"]

            # 2. Verify git operations
            assert mock_git.call_count >= 2

            # 3. Verify comment posted on issue #67
            mock_gh.assert_any_call(
                [
                    "issue",
                    "comment",
                    "67",
                    "--body",
                    ANY,
                ],
                repo="marius-patrik/ChessWithQuests",
            )
            # Find the comment body call and inspect content
            comment_call = [
                c
                for c in mock_gh.call_args_list
                if c[0][0][0] == "issue" and c[0][0][1] == "comment"
            ][0]
            comment_body = comment_call[0][0][4]
            assert "<!-- antigravity-agent -->" in comment_body
            assert "Antigravity Agent Quota Exhaustion Notice" in comment_body
            assert "gemini-3.8-flash-high" in comment_body
            assert "claude-opus-4-6-thinking" in comment_body
            assert "- [x] Step A: Read request" in comment_body
            assert "Instructions to Resume" in comment_body
            assert "Blocked" in comment_body

            # 4. Verify Blocked label added
            mock_gh.assert_any_call(
                ["issue", "edit", "67", "--add-label", "Blocked"],
                repo="marius-patrik/ChessWithQuests",
            )

            # 5. Verify project board updated to Blocked
            assert len(mock_client.added_urls) == 1
            assert (
                "https://github.com/marius-patrik/ChessWithQuests/issues/67"
                in mock_client.added_urls[0]
            )
            assert ("item-101", "Blocked") in mock_client.edited_statuses


def test_checkpoint_and_notify_exhaustion_pr():
    class MockClient:
        def __init__(self):
            self.added_urls = []
            self.edited_statuses = []

        def add_item(self, url):
            self.added_urls.append(url)
            return "item-202"

        def edit_status(self, item_id, status):
            self.edited_statuses.append((item_id, status))
            return True

    mock_client = MockClient()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("antigravity_runner.run_gh") as mock_gh:
            data = checkpoint_and_notify_exhaustion(
                issue_number=88,
                repo="marius-patrik/ChessWithQuests",
                completed_steps=["Self-review iteration 1"],
                branch_name="feature/self-review",
                is_pr=True,
                error_detail="RESOURCE_EXHAUSTED",
                cwd=tmpdir,
                client=mock_client,
            )

            # Comment posted on PR
            mock_gh.assert_any_call(
                ["pr", "comment", "88", "--body", ANY],
                repo="marius-patrik/ChessWithQuests",
            )
            # Label added to PR
            mock_gh.assert_any_call(
                ["pr", "edit", "88", "--add-label", "Blocked"],
                repo="marius-patrik/ChessWithQuests",
            )
            # Project board URL points to PR
            assert (
                "https://github.com/marius-patrik/ChessWithQuests/pull/88"
                in mock_client.added_urls[0]
            )
            assert ("item-202", "Blocked") in mock_client.edited_statuses


def test_run_agy_prompt_all_models_exhausted_triggers_checkpoint():
    err_quota = subprocess.CalledProcessError(
        returncode=1, cmd=["agy"], stderr="429 RESOURCE_EXHAUSTED"
    )
    with (
        patch("subprocess.run", side_effect=err_quota),
        patch("time.sleep"),
        patch("antigravity_runner.checkpoint_and_notify_exhaustion") as mock_checkpoint,
    ):
        ctx = {
            "issue_number": 70,
            "repo": "marius-patrik/ChessWithQuests",
            "branch_name": "feature/exhaustion",
            "completed_steps": ["Step 1", "Step 2"],
        }
        res = run_agy_prompt(
            "Task prompt",
            fallback_models=["gemini-3.8-flash-high", "gemini-3.8-flash-medium"],
            max_retries=1,
            checkpoint_context=ctx,
        )
        assert res.startswith("[Antigravity Agent Execution Error]")
        assert "Quota exhausted across all fallback models" in res
        mock_checkpoint.assert_called_once_with(
            issue_number=70,
            repo="marius-patrik/ChessWithQuests",
            completed_steps=["Step 1", "Step 2"],
            branch_name="feature/exhaustion",
            is_pr=False,
            error_detail=res,
            cwd=None,
            client=None,
        )


def test_dispatch_event_resume_comment():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "marius-patrik/ChessWithQuests"},
                "issue": {
                    "number": 70,
                    "labels": [{"name": "Plan"}],
                },
                "comment": {
                    "body": "/resume",
                    "user": {"login": "marius-patrik"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with (
            patch("antigravity_runner.find_parent_request_number", return_value=67) as mock_find,
            patch("antigravity_runner.handle_implement") as mock_implement,
        ):
            dispatch_event(temp_path, "issue_comment")
            mock_find.assert_called_once_with(70, "marius-patrik/ChessWithQuests")
            mock_implement.assert_called_once_with(70, 67, "marius-patrik/ChessWithQuests")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
