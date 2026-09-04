import os
import sys
import pytest
from unittest.mock import MagicMock

# Ensure .github/scripts is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from verify_issue_plan import (
    extract_bound_issues,
    has_comprehensive_plan,
    has_valid_review_or_alignment,
    verify_issue_plan_and_review,
)


def test_extract_bound_issues_various_formats():
    assert extract_bound_issues("Closes #123") == [123]
    assert extract_bound_issues("Fixes #45, Resolves #67") == [45, 67]
    assert extract_bound_issues("No bound issue here") == []
    assert extract_bound_issues(
        "Resolves https://github.com/marius-patrik/ChessWithQuests/issues/88"
    ) == [88]


def test_has_comprehensive_plan_valid():
    comments = [
        {"body": "Some casual comment"},
        {"body": """### Implementation Plan: New Feature

#### 1. Scope
- Add new validation module and update controllers.

#### 2. Verification Plan
- Run pytest test_new_feature.py
- Ensure black checks pass cleanly.
"""},
    ]
    ok, msg = has_comprehensive_plan(comments)
    assert ok is True
    assert "Valid comprehensive implementation plan" in msg


def test_has_comprehensive_plan_missing():
    comments = [{"body": "Working on this now."}, {"body": "Will push a branch soon."}]
    ok, msg = has_comprehensive_plan(comments)
    assert ok is False
    assert "No comment containing an 'Implementation Plan'" in msg


def test_has_comprehensive_plan_too_short():
    comments = [{"body": "### Implementation Plan\nDo it."}]
    ok, msg = has_comprehensive_plan(comments)
    assert ok is False
    assert "too short" in msg


def test_has_valid_review_matches_plan():
    comments = [{"body": """### Implementation Review: PR #10
- **Plan Match**: Matches Plan Exactly (Yes)
- All steps completed and verified green.
"""}]
    ok, msg = has_valid_review_or_alignment(comments)
    assert ok is True
    assert "matches plan" in msg


def test_has_valid_review_approved_alignment():
    comments = [{"body": """### Plan Alignment: PR #10
- Divergence: Used pyproject.toml instead of setup.py.
- Status: Approved by team.
"""}]
    ok, msg = has_valid_review_or_alignment(comments)
    assert ok is True
    assert "Plan alignment comment found with approved status" in msg


def test_has_valid_review_missing():
    comments = [{"body": "Just finished coding."}]
    ok, msg = has_valid_review_or_alignment(comments)
    assert ok is False
    assert "No comment containing an 'Implementation Review'" in msg


def test_has_valid_review_unapproved_deviation():
    comments = [{"body": """### Plan Alignment: PR #10
- We changed the API signatures completely without approval.
- Status: Pending review.
"""}]
    ok, msg = has_valid_review_or_alignment(comments)
    assert ok is False
    assert "does not explicitly confirm" in msg


def test_verify_issue_plan_and_review_full_pass():
    mock_comments = [
        {"body": """### Implementation Plan: Add Feature
1. Create new models and data structures in src/model.
2. Add comprehensive unit tests and verify full test suite passes.
"""},
        {"body": """### Implementation Review: PR #5
- Plan Match: Matches the plan exactly.
- All unit tests verified green.
"""},
    ]

    def mock_fetcher(repo, issue_num):
        return mock_comments

    ok, errors = verify_issue_plan_and_review("Closes #12", "test/repo", fetcher=mock_fetcher)
    assert ok is True
    assert errors == []


def test_verify_issue_plan_and_review_missing_review_fails():
    mock_comments = [{"body": """### Implementation Plan: Add Feature
1. Create new models and data structures in src/model.
2. Add comprehensive unit tests and verify full test suite passes.
"""}]

    def mock_fetcher(repo, issue_num):
        return mock_comments

    ok, errors = verify_issue_plan_and_review("Closes #12", "test/repo", fetcher=mock_fetcher)
    assert ok is False
    assert any("Implementation Review" in e for e in errors)


def test_workflow_files_exist_and_configured():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    verify_pr_path = os.path.join(repo_root, ".github", "workflows", "verify-pr-issue.yml")
    open_pr_path = os.path.join(repo_root, ".github", "workflows", "open-pr.yml")

    assert os.path.isfile(verify_pr_path), "verify-pr-issue.yml must exist"
    assert os.path.isfile(open_pr_path), "open-pr.yml must exist"

    with open(verify_pr_path, encoding="utf-8") as f:
        content = f.read()
    assert "verify_issue_plan.py" in content

    with open(open_pr_path, encoding="utf-8") as f:
        content = f.read()
    assert "gh pr create" in content
