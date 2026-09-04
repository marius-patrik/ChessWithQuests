import os
import sys
import pytest

# Ensure .github/scripts is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from project_automation import (
    extract_bound_issues,
    determine_status_from_labels,
    process_event,
    STATUS_OPTIONS,
)


def test_extract_bound_issues_various_formats():
    assert extract_bound_issues("Closes #123") == [123]
    assert extract_bound_issues("Fixes #45 and resolves #67") == [45, 67]
    assert extract_bound_issues("CLOSED #10") == [10]
    assert extract_bound_issues(
        "Resolves https://github.com/marius-patrik/ChessWithQuests/issues/89"
    ) == [89]
    assert extract_bound_issues("Just discussing issue #123 without keyword") == []
    assert extract_bound_issues("") == []
    assert extract_bound_issues(None) == []


def test_determine_status_from_labels():
    assert determine_status_from_labels(["bug", "Blocked"]) == "Blocked"
    assert determine_status_from_labels(["enhancement", "In Progress"]) == "In Progress"
    assert determine_status_from_labels(["Backlog"]) == "Backlog"
    assert determine_status_from_labels(["ToDo"]) == "ToDo"
    assert determine_status_from_labels(["Done"]) == "Done"
    assert determine_status_from_labels(["random", "label"]) == "ToDo"
    assert determine_status_from_labels([]) == "ToDo"


class MockGitHubProjectClient:
    def __init__(self):
        self.added_items = []
        self.edited_statuses = []
        self.added_labels = []

    def add_item(self, url):
        item_id = f"item-{len(self.added_items) + 1}"
        self.added_items.append((url, item_id))
        return item_id

    def edit_status(self, item_id, status_name):
        self.edited_statuses.append((item_id, status_name))
        return True

    def add_issue_label(self, repo, issue_number, label):
        self.added_labels.append((repo, issue_number, label))


def test_process_event_issue_opened():
    client = MockGitHubProjectClient()
    payload = {
        "action": "opened",
        "issue": {
            "html_url": "https://github.com/test/repo/issues/1",
            "labels": [{"name": "In Progress"}],
        },
    }
    process_event("issues", payload, client=client)
    assert len(client.added_items) == 1
    assert client.edited_statuses == [("item-1", "In Progress")]


def test_process_event_issue_closed():
    client = MockGitHubProjectClient()
    payload = {
        "action": "closed",
        "repository": {"full_name": "marius-patrik/ChessWithQuests"},
        "issue": {
            "number": 1,
            "html_url": "https://github.com/marius-patrik/ChessWithQuests/issues/1",
            "labels": [],
        },
    }
    process_event("issues", payload, client=client)
    assert client.edited_statuses == [("item-1", "Done")]
    assert client.added_labels == [("marius-patrik/ChessWithQuests", 1, "Done")]


def test_process_event_pr_opened_with_bound_issue():
    client = MockGitHubProjectClient()
    payload = {
        "action": "opened",
        "repository": {"full_name": "marius-patrik/ChessWithQuests"},
        "pull_request": {
            "body": "Implements new feature. Closes #5",
        },
    }
    process_event("pull_request", payload, client=client)
    assert client.added_labels == [("marius-patrik/ChessWithQuests", 5, "In Progress")]
    assert client.edited_statuses == [("item-1", "In Progress")]


def test_process_event_pr_merged_with_bound_issue():
    client = MockGitHubProjectClient()
    payload = {
        "action": "closed",
        "repository": {"full_name": "marius-patrik/ChessWithQuests"},
        "pull_request": {
            "body": "Fixes bug. Resolves #5",
            "merged": True,
        },
    }
    process_event("pull_request", payload, client=client)
    assert client.added_labels == [("marius-patrik/ChessWithQuests", 5, "Done")]
    assert client.edited_statuses == [("item-1", "Done")]


def test_workflow_files_exist():
    verify_pr_file = os.path.join(repo_root, ".github", "workflows", "verify-pr-issue.yml")
    project_auto_file = os.path.join(repo_root, ".github", "workflows", "project-automation.yml")

    assert os.path.isfile(verify_pr_file), "verify-pr-issue.yml must exist"
    assert os.path.isfile(project_auto_file), "project-automation.yml must exist"
