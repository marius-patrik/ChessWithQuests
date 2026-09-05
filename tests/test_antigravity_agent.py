"""Unit tests for Antigravity CI Agent runner and utilities."""

import io
import json
import os
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
        assert payload["auth_method"] == "oauth"


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
