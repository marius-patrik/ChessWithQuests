import os
import pytest


def test_agents_rule_mandates_branches_prs_ci_and_protection():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    assert os.path.exists(agents_file), "AGENTS.md must exist"

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "pull request" in lower_content or "pr" in lower_content
    assert "branch" in lower_content
    assert "ci" in lower_content
    assert "protect" in lower_content
    assert "main" in lower_content


def test_agents_rule_mandates_bound_issue_autoclose_and_project_automation():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "closes" in lower_content or "bound issue" in lower_content
    assert "project board" in lower_content or "project" in lower_content
    assert "deleted" in lower_content
    assert "in progress" in lower_content
    assert "backlog" in lower_content
    assert "todo" in lower_content or "to do" in lower_content
    assert "blocked" in lower_content


def test_agents_rule_mandates_implementation_plan_and_review():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "implementation plan" in lower_content
    assert "review" in lower_content
    assert "matches plan" in lower_content or "plan alignment" in lower_content


def test_agents_rule_mandates_pr_review_approval():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "review approval" in lower_content or "approving review" in lower_content
    assert "marius-patrik" in content


def test_agents_rule_mandates_user_request_issue_and_verbatim_prompt():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "user request" in lower_content
    assert "issue" in lower_content
    assert "verbatim" in lower_content
