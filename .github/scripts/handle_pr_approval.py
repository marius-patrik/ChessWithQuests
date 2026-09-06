"""Script to handle PR approvals and auto-merge automation.

Transitions draft PRs to ready, submits approval as proxy if needed, enables auto-merge with
branch auto-deletion, and reconciles bound issues / project board to Done.
"""

import json
import os
import re
import subprocess
import sys
import time
from typing import Set


def reconcile_post_merge(pr_number: int, repo: str) -> None:
    """Closes bound issues and updates Project 14 board to Done post merge."""
    view_res = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "state,closingIssuesReferences,body,url"],
        capture_output=True,
        text=True,
        env=dict(os.environ, GH_REPO=repo),
    )
    if view_res.returncode != 0:
        print(f"Failed to view PR #{pr_number} for post-merge reconciliation.")
        return

    data = json.loads(view_res.stdout)
    if data.get("state") != "MERGED":
        print(f"PR #{pr_number} state is {data.get('state')}, not MERGED.")
        return

    issue_numbers: Set[int] = set()
    for ref in data.get("closingIssuesReferences", []):
        if "number" in ref:
            issue_numbers.add(ref["number"])

    body = data.get("body", "")
    for m in re.finditer(
        r"(?i)\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:#(\d+)|https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+))\b",
        body,
    ):
        num = m.group(1) or m.group(2)
        if num:
            issue_numbers.add(int(num))

    print(f"Reconciling post-merge for PR #{pr_number}. Bound issues: {sorted(issue_numbers)}")

    owner = repo.split("/")[0] if "/" in repo else "marius-patrik"
    project_num = 14
    status_field = "PVTSSF_lAHOBCXFy84BidGlzhhVH8o"
    done_option = "db1d3578"

    proj_view = subprocess.run(
        ["gh", "project", "view", str(project_num), "--owner", owner, "--format", "json"],
        capture_output=True,
        text=True,
        env=dict(os.environ, GH_REPO=repo),
    )
    project_id = None
    if proj_view.returncode == 0:
        try:
            project_id = json.loads(proj_view.stdout).get("id")
        except Exception:
            pass

    def mark_done_on_project(url: str):
        if not project_id:
            return
        add_res = subprocess.run(
            [
                "gh",
                "project",
                "item-add",
                str(project_num),
                "--owner",
                owner,
                "--url",
                url,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ, GH_REPO=repo),
        )
        if add_res.returncode == 0:
            try:
                item_id = json.loads(add_res.stdout).get("id")
                if item_id:
                    subprocess.run(
                        [
                            "gh",
                            "project",
                            "item-edit",
                            "--id",
                            item_id,
                            "--project-id",
                            project_id,
                            "--field-id",
                            status_field,
                            "--single-select-option-id",
                            done_option,
                            "--format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        env=dict(os.environ, GH_REPO=repo),
                    )
            except Exception as e:
                print(f"Project update notice for {url}: {e}")

    pr_url = data.get("url")
    if pr_url:
        mark_done_on_project(pr_url)

    for num in sorted(issue_numbers):
        issue_url = f"https://github.com/{repo}/issues/{num}"
        subprocess.run(
            ["gh", "issue", "close", str(num), "--repo", repo, "--reason", "completed"],
            capture_output=True,
            text=True,
            env=dict(os.environ, GH_REPO=repo),
        )
        subprocess.run(
            ["gh", "issue", "edit", str(num), "--repo", repo, "--add-label", "Done"],
            capture_output=True,
            text=True,
            env=dict(os.environ, GH_REPO=repo),
        )
        subprocess.run(
            ["gh", "issue", "edit", str(num), "--repo", repo, "--remove-label", "In Progress"],
            capture_output=True,
            text=True,
            env=dict(os.environ, GH_REPO=repo),
        )
        mark_done_on_project(issue_url)
        print(f"Closed issue #{num} and marked Done on Project {project_num}")


def handle_pr_approval():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    actor = os.environ.get("GITHUB_ACTOR", "")
    repo_owner = os.environ.get("REPO_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "marius-patrik/ChessWithQuests")

    allowed_users = {repo_owner.lower(), "marius-patrik"}
    if actor.lower() not in allowed_users:
        print(f"Actor {actor} not in allowed list {allowed_users}. Skipping.")
        sys.exit(0)

    pr_number = None
    is_approved = False

    if event_name == "pull_request_review":
        review_state = os.environ.get("REVIEW_STATE", "").upper()
        review_body = os.environ.get("REVIEW_BODY", "").strip()
        pr_number = os.environ.get("PR_NUMBER")
        if review_state == "APPROVED" or re.search(
            r"(?i)\b(?:approve|approved|merge)\b", review_body
        ):
            is_approved = True

    elif event_name == "issue_comment":
        is_pr = os.environ.get("IS_PR") == "true"
        if not is_pr:
            print("Comment not on pull request. Skipping.")
            sys.exit(0)
        pr_number = os.environ.get("PR_NUMBER")
        comment_body = os.environ.get("COMMENT_BODY", "").strip()
        if re.search(r"(?i)^\s*(?:/approve|approve|merge|/merge|lgtm)\s*$", comment_body):
            is_approved = True

    if not pr_number or not is_approved:
        print("Not an approval event. Skipping.")
        sys.exit(0)

    print(f"PR #{pr_number} approved by @{actor}. Preparing for auto-merge.")

    view_res = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "isDraft,state,reviewDecision"],
        capture_output=True,
        text=True,
        check=True,
        env=dict(os.environ, GH_REPO=repo),
    )
    data = json.loads(view_res.stdout)
    state = data.get("state")
    if state != "OPEN":
        print(f"PR #{pr_number} is {state}. Exiting.")
        sys.exit(0)

    # 1. Transition to ready if draft
    if data.get("isDraft"):
        print(f"Marking PR #{pr_number} ready for review...")
        subprocess.run(
            ["gh", "pr", "ready", str(pr_number)],
            check=True,
            env=dict(os.environ, GH_REPO=repo),
        )

    # 2. If review is still required, submit approval as bot
    if data.get("reviewDecision") == "REVIEW_REQUIRED":
        print(f"Submitting approving review as bot on PR #{pr_number}...")
        subprocess.run(
            [
                "gh",
                "pr",
                "review",
                str(pr_number),
                "--approve",
                "-b",
                f"Approved via automation on behalf of @{actor}.",
            ],
            check=False,
            env=dict(os.environ, GH_REPO=repo),
        )

    # 3. Enable auto-merge with branch auto-deletion
    print(f"Enabling auto-merge for PR #{pr_number} with --delete-branch...")
    merge_cmd = ["gh", "pr", "merge", str(pr_number), "--auto", "--merge", "--delete-branch"]
    res = subprocess.run(
        merge_cmd, capture_output=True, text=True, env=dict(os.environ, GH_REPO=repo)
    )
    print(f"Auto-merge result:\n{res.stdout}\n{res.stderr}")
    if res.returncode != 0:
        print("Attempting direct merge if requirements are already satisfied...")
        direct_cmd = ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch"]
        res_dir = subprocess.run(
            direct_cmd, capture_output=True, text=True, env=dict(os.environ, GH_REPO=repo)
        )
        print(f"Direct merge result:\n{res_dir.stdout}\n{res_dir.stderr}")

    # 4. Poll for merge completion to perform post-merge issue and board reconciliation
    merged = False
    for _ in range(12):  # Poll up to 60s
        check_res = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state"],
            capture_output=True,
            text=True,
            env=dict(os.environ, GH_REPO=repo),
        )
        if check_res.returncode == 0:
            cur_state = json.loads(check_res.stdout).get("state")
            if cur_state == "MERGED":
                merged = True
                print(f"PR #{pr_number} merged successfully!")
                break
        time.sleep(5)

    if merged:
        reconcile_post_merge(int(pr_number), repo)


if __name__ == "__main__":
    handle_pr_approval()
