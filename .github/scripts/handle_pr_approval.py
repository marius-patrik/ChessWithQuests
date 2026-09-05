"""Script to handle PR approvals and auto-merge automation.

Transitions draft PRs to ready, submits approval as proxy if needed, and enables auto-merge.
"""

import json
import os
import re
import subprocess
import sys


def handle_pr_approval():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    actor = os.environ.get("GITHUB_ACTOR", "")
    repo_owner = os.environ.get("REPO_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

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

    # 2. If review is still required (e.g. self-authored PR where user could only comment), submit approval as bot
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

    # 3. Enable auto-merge
    print(f"Enabling auto-merge for PR #{pr_number}...")
    merge_cmd = ["gh", "pr", "merge", str(pr_number), "--auto", "--merge"]
    res = subprocess.run(
        merge_cmd, capture_output=True, text=True, env=dict(os.environ, GH_REPO=repo)
    )
    print(f"Auto-merge result:\n{res.stdout}\n{res.stderr}")
    if res.returncode != 0:
        print("Attempting direct merge if requirements are already satisfied...")
        direct_cmd = ["gh", "pr", "merge", str(pr_number), "--merge"]
        res_dir = subprocess.run(
            direct_cmd, capture_output=True, text=True, env=dict(os.environ, GH_REPO=repo)
        )
        print(f"Direct merge result:\n{res_dir.stdout}\n{res_dir.stderr}")


if __name__ == "__main__":
    handle_pr_approval()
