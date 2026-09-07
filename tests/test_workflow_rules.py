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


def test_agents_rule_mandates_pr_review_approval_and_automerge():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "review approval" in lower_content or "approving review" in lower_content
    assert "marius-patrik" in content
    assert "last pusher" in lower_content
    assert "auto-merge" in lower_content


def test_agents_rule_mandates_draft_prs_and_latest_main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "draft" in lower_content
    assert "latest main" in lower_content or "latest `main`" in lower_content


def test_agents_rule_mandates_bot_authored_prs():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert (
        "github-actions[bot]" in lower_content
        or "actions bot" in lower_content
        or "open-pr.yml" in lower_content
    )


def test_agents_rule_mandates_user_request_issue_and_verbatim_prompt():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "user request" in lower_content
    assert "issue" in lower_content
    assert "verbatim" in lower_content


def test_agents_rule_mandates_request_plan_hierarchy_and_confirmation_gate():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "request" in lower_content
    assert "plan" in lower_content
    assert "interpretation" in lower_content
    assert "confirmation" in lower_content
    assert "child issue" in lower_content or "sub-issue" in lower_content
    assert "decomposed" in lower_content or "decomposition" in lower_content


def test_open_pr_workflow_and_script_exist():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "open-pr.yml")
    script_path = os.path.join(repo_root, ".github", "scripts", "open_pr.py")

    assert os.path.isfile(workflow_path), "open-pr.yml must exist"
    assert os.path.isfile(script_path), "open_pr.py must exist"

    with open(workflow_path, encoding="utf-8") as f:
        wf_content = f.read()

    assert "workflow_dispatch" in wf_content
    assert "gh pr create" in wf_content

    with open(script_path, encoding="utf-8") as f:
        py_content = f.read()

    assert "open_pr_as_bot" in py_content


def test_pr_approval_automerge_workflow_exists():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "pr-approval-automerge.yml")
    script_path = os.path.join(repo_root, ".github", "scripts", "handle_pr_approval.py")

    assert os.path.isfile(workflow_path), "pr-approval-automerge.yml must exist"
    assert os.path.isfile(script_path), "handle_pr_approval.py must exist"

    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    assert "pull_request_review" in content
    assert "issue_comment" in content
    assert "handle_pr_approval.py" in content


def test_agents_rule_mandates_a_harness_agnostic_agent():
    """The rule used to name one vendor, one model and one person's account.

    That is the divergence the shared pipeline removes: a single vendor's quota halted delivery
    outright. The rule now describes a registry of harnesses that degrades gracefully, and names
    no individual - a governance document in a public repository is the wrong place for an
    address.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "AGENTS.md"), encoding="utf-8") as handle:
        content = handle.read()
    lower = content.lower()

    assert "harness-agnostic" in lower
    assert "fallback" in lower and "quota" in lower
    assert "skipped rather" in lower or "graceful" in lower
    assert "@gmail.com" not in lower, "no personal address belongs in a public governance document"
    assert "gemini-3.8-flash" not in lower, "the rule must not pin one vendor's model"


def test_agents_rule_mandates_conventional_commits_and_taxonomy():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "conventional commits" in lower_content
    assert "area:model" in lower_content
    assert "area:view" in lower_content
    assert "area:controller" in lower_content
    assert "area:ci" in lower_content
    assert "area:docs" in lower_content


def test_agents_rule_mandates_project_board_statuses_and_autodeletion():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "superseded" in lower_content
    assert "dropped" in lower_content
    assert "auto-deletion" in lower_content or "delete_branch_on_merge" in lower_content


def test_the_agent_calls_the_pinned_runner_rather_than_carrying_one():
    """The runner, the container and the harness registry all live upstream now.

    This repository used to carry `antigravity_runner.py` and a Dockerfile of its own, which is
    exactly the divergence the shared pipeline exists to remove: a single-vendor runner that
    stalled when that vendor's quota ran out. The replacement is harness-agnostic and shared.
    """
    import json

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "agent.yml")
    assert os.path.isfile(workflow_path), "agent.yml must exist"

    with open(workflow_path, encoding="utf-8") as handle:
        content = handle.read()
    with open(os.path.join(repo_root, ".github", "darkfactory.json"), encoding="utf-8") as handle:
        pinned = json.load(handle)["upstream"]

    assert f"agent.yml@{pinned['ref']}" in content, "the agent must call the pinned pipeline"
    assert not os.path.isfile(
        os.path.join(repo_root, ".github", "scripts", "antigravity_runner.py")
    ), "the bespoke runner must be gone, not merely unused"


def test_the_agent_caller_passes_every_credential_it_holds():
    """Secrets do not cross a workflow_call boundary unless they are passed explicitly.

    A credential omitted here is not an error anywhere: the harness that needed it is simply
    skipped, and the agent quietly loses a fallback tier.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(
        os.path.join(repo_root, ".github", "workflows", "agent.yml"), encoding="utf-8"
    ) as handle:
        content = handle.read()

    for credential in (
        "ANTIGRAVITY_REFRESH_TOKEN",
        "ANTIGRAVITY_CLIENT_ID",
        "ANTIGRAVITY_CLIENT_SECRET",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GH_PROJECT_TOKEN",
    ):
        assert (
            f"{credential}: ${{{{ secrets.{credential} }}}}" in content
        ), f"{credential} is held by this repository but never reaches the runner"
