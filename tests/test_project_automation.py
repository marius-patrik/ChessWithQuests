import os
import sys
import pytest

# Ensure .github/scripts is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir in sys.path:
    sys.path.remove(scripts_dir)
sys.path.insert(0, scripts_dir)
sys.modules.pop("project_automation", None)

from unittest.mock import MagicMock, patch

from project_automation import (
    GitHubProjectClient,
    STATUS_LABELS,
    STATUS_OPTIONS,
    determine_status_from_labels,
    extract_bound_issues,
    process_event,
    reconcile_unassigned_statuses,
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
    assert determine_status_from_labels(["Superseded"]) == "Superseded"
    assert determine_status_from_labels(["Dropped"]) == "Dropped"
    assert determine_status_from_labels(["random", "label"]) == "ToDo"
    assert determine_status_from_labels([]) == "ToDo"


def test_status_options_taxonomy():
    assert STATUS_OPTIONS["Backlog"] == "8dbcec6a"
    assert STATUS_OPTIONS["ToDo"] == "fc671069"
    assert STATUS_OPTIONS["In Progress"] == "5879826b"
    assert STATUS_OPTIONS["Blocked"] == "dd704e81"
    assert STATUS_OPTIONS["Done"] == "db1d3578"
    assert STATUS_OPTIONS["Superseded"] == "1ea57ba8"
    assert STATUS_OPTIONS["Dropped"] == "7d7814ed"


def test_status_labels_taxonomy():
    assert STATUS_LABELS == {
        "Backlog",
        "ToDo",
        "In Progress",
        "Blocked",
        "Done",
        "Superseded",
        "Dropped",
    }


class MockGitHubProjectClient:
    def __init__(self):
        self.added_items = []
        self.edited_statuses = []
        self.added_labels = []
        self.status_labels = []
        self.project_number = 14
        self.owner = "marius-patrik"
        self.gh_responses = {}

    def add_item(self, url):
        item_id = f"item-{len(self.added_items) + 1}"
        self.added_items.append((url, item_id))
        return item_id

    def edit_status(self, item_id, status_name):
        self.edited_statuses.append((item_id, status_name))
        return True

    def set_status_label(self, repo, issue_number, status_name):
        self.status_labels.append((repo, issue_number, status_name))

    def add_issue_label(self, repo, issue_number, label):
        self.added_labels.append((repo, issue_number, label))
        if label in STATUS_LABELS:
            self.set_status_label(repo, issue_number, label)

    def run_gh(self, args):
        cmd = " ".join(args)
        for pattern, resp in self.gh_responses.items():
            if pattern in cmd:
                return resp
        return "{}"


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


def test_process_event_pr_edited_with_bound_issue():
    client = MockGitHubProjectClient()
    payload = {
        "action": "edited",
        "repository": {"full_name": "marius-patrik/ChessWithQuests"},
        "pull_request": {
            "body": "Updated description to bind issue. Closes #25",
        },
    }
    process_event("pull_request", payload, client=client)
    assert client.added_labels == [("marius-patrik/ChessWithQuests", 25, "In Progress")]
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


def test_reconcile_unassigned_statuses():
    import json

    client = MockGitHubProjectClient()
    items_data = {
        "items": [
            {
                "id": "item-open-unassigned",
                "status": None,
                "content": {"closed": False, "title": "Request: Doc updates"},
            },
            {
                "id": "item-done",
                "status": "Done",
                "content": {"closed": True, "title": "Request: Old feature"},
            },
            {
                "id": "item-closed-unassigned",
                "status": None,
                "content": {"closed": True, "title": "Dropped request"},
            },
            {
                "id": "item-in-prog",
                "status": "In Progress",
                "content": {"closed": False, "title": "Active feature"},
            },
        ]
    }
    client.gh_responses["project item-list"] = json.dumps(items_data)

    reconcile_unassigned_statuses(client)
    assert ("item-open-unassigned", "ToDo") in client.edited_statuses
    assert len(client.edited_statuses) == 1


def test_process_event_workflow_dispatch_reconciles():
    import json

    client = MockGitHubProjectClient()
    items_data = {
        "items": [
            {
                "id": "item-10",
                "status": None,
                "content": {"closed": False, "title": "Unassigned Issue"},
            }
        ]
    }
    client.gh_responses["project item-list"] = json.dumps(items_data)

    process_event("workflow_dispatch", {}, client=client)
    assert client.edited_statuses == [("item-10", "ToDo")]


def test_set_status_label_status_exclusivity():
    """Applying a status label issues a single gh command adding it and removing the other 6."""
    client = GitHubProjectClient(owner="marius-patrik", project_number=14)
    with patch.object(client, "run_gh") as mock_run_gh:
        client.set_status_label("marius-patrik/ChessWithQuests", 42, "Done")
        mock_run_gh.assert_called_once()
        args = mock_run_gh.call_args[0][0]

        # Verify command prefix and add-label
        assert args[0:5] == ["issue", "edit", "42", "--repo", "marius-patrik/ChessWithQuests"]
        assert args[5:7] == ["--add-label", "Done"]

        # Exactly 6 remove-label flags for the other status labels
        remove_flags = [args[i + 1] for i, x in enumerate(args) if x == "--remove-label"]
        expected_removed = sorted(STATUS_LABELS - {"Done"})
        assert remove_flags == expected_removed
        assert "Done" not in remove_flags
        assert "In Progress" in remove_flags
        assert len(remove_flags) == 6


def test_set_status_label_reverse_transition():
    """Transitioning back to an active status (e.g. In Progress) removes Done."""
    client = GitHubProjectClient(owner="marius-patrik", project_number=14)
    with patch.object(client, "run_gh") as mock_run_gh:
        client.set_status_label("marius-patrik/ChessWithQuests", 42, "In Progress")
        mock_run_gh.assert_called_once()
        args = mock_run_gh.call_args[0][0]

        assert args[5:7] == ["--add-label", "In Progress"]
        remove_flags = [args[i + 1] for i, x in enumerate(args) if x == "--remove-label"]
        expected_removed = sorted(STATUS_LABELS - {"In Progress"})
        assert remove_flags == expected_removed
        assert "Done" in remove_flags
        assert "In Progress" not in remove_flags
        assert len(remove_flags) == 6


@pytest.mark.parametrize("non_status_label", ["bug", "area:ci", "enhancement", "documentation"])
def test_add_issue_label_preserves_non_status_labels(non_status_label):
    """Adding non-status labels does not append any --remove-label flags."""
    client = GitHubProjectClient(owner="marius-patrik", project_number=14)
    with patch.object(client, "run_gh") as mock_run_gh:
        client.add_issue_label("marius-patrik/ChessWithQuests", 42, non_status_label)
        mock_run_gh.assert_called_once_with(
            [
                "issue",
                "edit",
                "42",
                "--repo",
                "marius-patrik/ChessWithQuests",
                "--add-label",
                non_status_label,
            ]
        )
        args = mock_run_gh.call_args[0][0]
        assert "--remove-label" not in args


@pytest.mark.parametrize("status_label", sorted(STATUS_LABELS))
def test_add_issue_label_delegates_to_set_status_label(status_label):
    """Calling add_issue_label with any board status label delegates to set_status_label."""
    client = GitHubProjectClient(owner="marius-patrik", project_number=14)
    with patch.object(client, "set_status_label") as mock_set_status:
        client.add_issue_label("marius-patrik/ChessWithQuests", 42, status_label)
        mock_set_status.assert_called_once_with("marius-patrik/ChessWithQuests", 42, status_label)


def test_add_issue_label_does_not_delegate_for_non_status_labels():
    """Non-status labels are not routed through set_status_label."""
    client = GitHubProjectClient(owner="marius-patrik", project_number=14)
    with (
        patch.object(client, "set_status_label") as mock_set_status,
        patch.object(client, "run_gh") as mock_run_gh,
    ):
        client.add_issue_label("marius-patrik/ChessWithQuests", 42, "bug")
        mock_set_status.assert_not_called()
        mock_run_gh.assert_called_once()
