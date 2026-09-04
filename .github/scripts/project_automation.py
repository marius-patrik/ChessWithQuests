import json
import os
import re
import subprocess
import sys
from typing import List, Optional, Dict, Any

PROJECT_OWNER = "marius-patrik"
PROJECT_NUMBER = 14
STATUS_FIELD_ID = "PVTSSF_lAHOBCXFy84BidGlzhhVH8o"

STATUS_OPTIONS = {
    "Backlog": "e779dd67",
    "ToDo": "9b2525b6",
    "In Progress": "7508a487",
    "Blocked": "ca3ddd1a",
    "Done": "93aba873",
}

CLOSING_PATTERN = re.compile(
    r"(?i)\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:#(\d+)|https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+))\b"
)


def extract_bound_issues(pr_body: Optional[str]) -> List[int]:
    """Extract issue numbers bound to a pull request using closing keywords."""
    if not pr_body:
        return []
    matches = CLOSING_PATTERN.findall(pr_body)
    issues = set()
    for m in matches:
        num_str = m[0] or m[1]
        if num_str:
            issues.add(int(num_str))
    return sorted(issues)


def determine_status_from_labels(labels: List[str]) -> str:
    """Determine project board status from issue labels."""
    normalized = {lbl.strip().lower(): lbl for lbl in labels}
    if "blocked" in normalized:
        return "Blocked"
    if "in progress" in normalized:
        return "In Progress"
    if "backlog" in normalized:
        return "Backlog"
    if "todo" in normalized or "to do" in normalized:
        return "ToDo"
    return "ToDo"


class GitHubProjectClient:
    def __init__(self, owner: str = PROJECT_OWNER, project_number: int = PROJECT_NUMBER):
        self.owner = owner
        self.project_number = project_number

    def run_gh(self, args: List[str]) -> str:
        cmd = ["gh"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def add_item(self, url: str) -> Optional[str]:
        try:
            output = self.run_gh(
                [
                    "project",
                    "item-add",
                    str(self.project_number),
                    "--owner",
                    self.owner,
                    "--url",
                    url,
                    "--format",
                    "json",
                ]
            )
            data = json.loads(output)
            return data.get("id")
        except Exception as e:
            print(f"Error adding item {url}: {e}", file=sys.stderr)
            return None

    def edit_status(self, item_id: str, status_name: str) -> bool:
        option_id = STATUS_OPTIONS.get(status_name)
        if not option_id:
            print(f"Unknown status: {status_name}", file=sys.stderr)
            return False
        try:
            # Query project ID
            project_output = self.run_gh(
                [
                    "project",
                    "view",
                    str(self.project_number),
                    "--owner",
                    self.owner,
                    "--format",
                    "json",
                ]
            )
            project_id = json.loads(project_output).get("id")
            self.run_gh(
                [
                    "project",
                    "item-edit",
                    "--id",
                    item_id,
                    "--project-id",
                    project_id,
                    "--field-id",
                    STATUS_FIELD_ID,
                    "--single-select-option-id",
                    option_id,
                    "--format",
                    "json",
                ]
            )
            return True
        except Exception as e:
            print(f"Error updating item status: {e}", file=sys.stderr)
            return False

    def add_issue_label(self, repo: str, issue_number: int, label: str) -> None:
        try:
            self.run_gh(["issue", "edit", str(issue_number), "--repo", repo, "--add-label", label])
        except Exception as e:
            print(f"Error adding label to issue #{issue_number}: {e}", file=sys.stderr)


def process_event(
    event_name: str, payload: Dict[str, Any], client: Optional[GitHubProjectClient] = None
):
    if client is None:
        client = GitHubProjectClient()

    if event_name == "issues":
        action = payload.get("action")
        issue = payload.get("issue", {})
        issue_url = issue.get("html_url")
        labels = [
            lbl.get("name") if isinstance(lbl, dict) else str(lbl)
            for lbl in issue.get("labels", [])
        ]

        if not issue_url:
            return

        if action in ("opened", "reopened"):
            item_id = client.add_item(issue_url)
            status = "ToDo" if action == "reopened" else determine_status_from_labels(labels)
            if item_id:
                client.edit_status(item_id, status)
                print(f"Issue {issue_url} added to project with status {status}")

        elif action in ("labeled", "unlabeled"):
            item_id = client.add_item(issue_url)
            status = determine_status_from_labels(labels)
            if item_id:
                client.edit_status(item_id, status)
                print(f"Issue {issue_url} status updated to {status}")

        elif action == "closed":
            item_id = client.add_item(issue_url)
            if item_id:
                client.edit_status(item_id, "Done")
                print(f"Issue {issue_url} status updated to Done")

    elif event_name == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repo_full_name = payload.get("repository", {}).get(
            "full_name", "marius-patrik/ChessWithQuests"
        )
        pr_body = pr.get("body", "")
        merged = pr.get("merged", False)

        bound_issues = extract_bound_issues(pr_body)
        print(f"PR event {action}: detected bound issues {bound_issues}")

        if action == "opened":
            for issue_num in bound_issues:
                issue_url = f"https://github.com/{repo_full_name}/issues/{issue_num}"
                client.add_issue_label(repo_full_name, issue_num, "In Progress")
                item_id = client.add_item(issue_url)
                if item_id:
                    client.edit_status(item_id, "In Progress")
                    print(f"Issue #{issue_num} moved to In Progress")

        elif action == "closed" and merged:
            for issue_num in bound_issues:
                issue_url = f"https://github.com/{repo_full_name}/issues/{issue_num}"
                item_id = client.add_item(issue_url)
                if item_id:
                    client.edit_status(item_id, "Done")
                    print(f"Issue #{issue_num} moved to Done")


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if not event_path or not os.path.exists(event_path):
        print(f"No GITHUB_EVENT_PATH found or event {event_name}")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    process_event(event_name, payload)


if __name__ == "__main__":
    main()
