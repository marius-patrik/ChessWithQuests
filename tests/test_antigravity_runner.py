"""Unit tests for Antigravity CI Agent runner helper functions.

Tests quota exhaustion pattern matching, exponential backoff with jitter constraints,
model fallback chain ordering, atomic checkpointing with structure validation,
git command stderr diagnostics, and project board status updates.
"""

import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch
import pytest

# Ensure .github/scripts is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(repo_root, ".github", "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from antigravity_runner import (
    CHECKPOINT_FILENAME,
    DEFAULT_MODEL_FALLBACK_CHAIN,
    PROJECT_NUMBER,
    PROJECT_OWNER,
    QUOTA_EXHAUSTION_PATTERNS,
    STATE_DIR,
    WORKSPACE_DIR,
    calculate_backoff,
    clear_checkpoint,
    dispatch_event,
    find_plan_issue_for_pr,
    get_model_fallback_chain,
    handle_implement,
    handle_plan_alignment,
    handle_self_review,
    is_quota_exhausted,
    load_checkpoint,
    run_agy_prompt,
    run_git,
    save_checkpoint,
    unblock_entity,
    update_project_status_blocked,
    _exclude_checkpoint_from_git,
)

# ============================================================================
# 1. is_quota_exhausted Regex Edge Cases (Findings 2 & 3)
# ============================================================================


def test_is_quota_exhausted_line_number_false_positives():
    """Verify that stack traces and messages containing line number 429 are NOT matched."""
    assert is_quota_exhausted('File "runner.py", line 429, in run') is False
    assert is_quota_exhausted("Line 429: syntax error encountered") is False
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/workspace/src/game_manager.py", line 429, in update_board\n'
        '    raise ValueError("Invalid move coordinates")'
    )
    assert is_quota_exhausted(tb) is False


def test_is_quota_exhausted_overloaded_false_positives():
    """Verify compiler and linter method overloading messages are NOT matched."""
    assert (
        is_quota_exhausted("TypeError: overloaded function call does not match signature") is False
    )
    assert (
        is_quota_exhausted("cannot resolve overloaded method 'add' with arguments (int, str)")
        is False
    )
    assert (
        is_quota_exhausted("mypy: overloaded function implementation does not match overload")
        is False
    )


def test_is_quota_exhausted_http_status_codes():
    """Verify standard HTTP / API 429 status code patterns match."""
    assert is_quota_exhausted("Status code: 429") is True
    assert is_quota_exhausted("status_code = 429") is True
    assert is_quota_exhausted("HTTP 429 Too Many Requests") is True
    assert is_quota_exhausted("Error: 429 Too Many Requests") is True
    assert is_quota_exhausted("429 Too Many Requests") is True
    assert is_quota_exhausted("429 ResourceExhausted: Quota limit hit") is True
    assert is_quota_exhausted("429 RESOURCE_EXHAUSTED") is True
    assert is_quota_exhausted("429: Rate limit reached") is True


def test_is_quota_exhausted_multiline_matching():
    """Verify multi-line error payloads with quota and exceeded on separate lines match."""
    multiline_1 = (
        "GoogleGenerativeAIError:\nQuota for metric GenerateContent\nhas been exceeded for project."
    )
    assert is_quota_exhausted(multiline_1) is True

    multiline_2 = "Error detail:\nExceeded current daily\nAPI call quota limit."
    assert is_quota_exhausted(multiline_2) is True


def test_is_quota_exhausted_service_overloaded_and_unavailable():
    """Verify model/server/service overload and unavailability patterns match."""
    assert is_quota_exhausted("Model overloaded. Please try again shortly.") is True
    assert is_quota_exhausted("Server is overloaded.") is True
    assert is_quota_exhausted("Service overloaded") is True
    assert is_quota_exhausted("The requested model is unavailable") is True
    assert is_quota_exhausted("service unavailable") is True
    assert is_quota_exhausted("endpoint is unavailable") is True


def test_is_quota_exhausted_exhaustion_and_quota_limit_phrases():
    """Verify 'quota exhausted', 'quota limit', and runner sentinel error string match."""
    assert is_quota_exhausted("quota exhausted") is True
    assert (
        is_quota_exhausted("Quota exhausted across all fallback models (gemini-3.8-flash-high): ")
        is True
    )
    assert (
        is_quota_exhausted(
            "[Antigravity Agent Execution Error]: Quota exhausted across all fallback models (gemini-3.8-flash-high): "
        )
        is True
    )
    assert is_quota_exhausted("API quota limit reached for project") is True
    assert is_quota_exhausted("Current quota limit has been hit") is True
    assert is_quota_exhausted("exhaustion of quota for model") is True
    assert is_quota_exhausted("exhausted API quota") is True
    assert is_quota_exhausted("out of quota") is True


def test_is_quota_exhausted_empty_and_unrelated():
    """Verify empty or unrelated errors return False."""
    assert is_quota_exhausted("") is False
    assert is_quota_exhausted(None) is False
    assert is_quota_exhausted("Keyring authorization denied.") is False
    assert is_quota_exhausted("SyntaxError: invalid syntax in file.py") is False
    assert is_quota_exhausted("fatal: not a git repository") is False


def test_is_quota_exhausted_rate_limit_and_quota_false_positives():
    """Verify non-error headers, configuration flags, and unexhausted limits are ignored."""
    assert is_quota_exhausted("x-ratelimit-remaining: 99") is False
    assert is_quota_exhausted("rate_limit=100") is False
    assert is_quota_exhausted("Config: max_rate_limit: 50") is False
    assert is_quota_exhausted("Quota limit is 1000") is False
    assert is_quota_exhausted("Daily quota limit: 500 requests remaining") is False

    # Distant "quota" on line 1 and "limit" on subsequent lines without failure keywords
    distant_log = "Quota: OK\n" + "processing record\n" * 30 + "Recursion limit reached"
    assert is_quota_exhausted(distant_log) is False


def test_is_quota_exhausted_tightened_rate_limit_matches():
    """Verify rate limit errors with explicit failure keywords are matched."""
    assert is_quota_exhausted("Rate limit exceeded") is True
    assert is_quota_exhausted("API rate-limit exceeded: 15 RPM") is True
    assert is_quota_exhausted("Rate limit reached for gemini-3.8-flash-high") is True
    assert is_quota_exhausted("Quota limit exceeded") is True
    assert is_quota_exhausted("quota limit has been reached") is True


# ============================================================================
# 2. calculate_backoff Constraints & Overflow (Findings 4 & 5)
# ============================================================================


def test_calculate_backoff_upper_bound_with_jitter():
    """Verify delay with jitter NEVER exceeds max_delay."""
    for attempt in range(25):
        for _ in range(10):
            delay = calculate_backoff(
                attempt=attempt,
                base_delay=2.0,
                backoff_factor=2.0,
                max_delay=30.0,
                jitter=True,
                jitter_factor=0.5,
            )
            assert delay <= 30.0, f"Delay {delay} exceeded max_delay 30.0 at attempt {attempt}"


def test_calculate_backoff_jitter_bounds():
    """Verify delay falls within expected jitter range before max_delay capping."""
    base_delay = 1.0
    backoff_factor = 2.0
    jitter_factor = 0.5
    for attempt in range(4):
        raw_base = base_delay * (backoff_factor**attempt)
        for _ in range(10):
            val = calculate_backoff(
                attempt=attempt,
                base_delay=base_delay,
                backoff_factor=backoff_factor,
                max_delay=100.0,
                jitter=True,
                jitter_factor=jitter_factor,
            )
            assert val >= raw_base, f"Delay {val} was below raw base {raw_base}"
            assert val <= raw_base * (1.0 + jitter_factor) + 1e-6


def test_calculate_backoff_large_attempt_overflow_protection():
    """Verify very large attempt counts do not raise OverflowError."""
    delay = calculate_backoff(attempt=1000, base_delay=1.0, max_delay=60.0)
    assert delay <= 60.0

    delay_huge = calculate_backoff(attempt=1000000, base_delay=1.0, max_delay=60.0)
    assert delay_huge <= 60.0


def test_calculate_backoff_negative_attempt_handled_safely():
    """Verify negative attempt count is treated as attempt 0."""
    val = calculate_backoff(attempt=-5, base_delay=1.5, jitter=False)
    assert val == 1.5


def test_calculate_backoff_exponential_scaling_deterministic():
    """Verify deterministic exponential scaling progression without jitter."""
    delays = [
        calculate_backoff(attempt=i, base_delay=1.0, backoff_factor=2.0, jitter=False)
        for i in range(5)
    ]
    assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_calculate_backoff_nonzero_jitter_at_max_delay():
    """Verify non-zero jitter at ceiling to prevent thundering herd in concurrent retries."""
    max_delay = 60.0
    jitter_factor = 0.5
    # High attempt count where raw delay (1024.0) exceeds max_delay (60.0)
    samples = [
        calculate_backoff(
            attempt=10,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=max_delay,
            jitter=True,
            jitter_factor=jitter_factor,
        )
        for _ in range(30)
    ]
    # 1. No sample should exceed max_delay
    assert all(s <= max_delay for s in samples)
    # 2. Ceiling should not clamp to a constant 60.0; jitter must produce variation
    assert len(set(samples)) > 1
    # 3. Spread should fall within the expected ceiling jitter window [max_delay / (1 + jitter_factor), max_delay]
    min_expected = max_delay / (1.0 + jitter_factor)
    assert all(s >= min_expected - 1e-6 for s in samples)
    assert min(samples) < max_delay  # Not all clamped to 60.0


# ============================================================================
# 3. get_model_fallback_chain Behavior (Findings 6 & 7)
# ============================================================================


def test_get_model_fallback_chain_default():
    """Verify default fallback chain returned when no args passed."""
    chain = get_model_fallback_chain()
    assert chain == DEFAULT_MODEL_FALLBACK_CHAIN
    # Check that it returns a copy
    chain.append("extra-model")
    assert "extra-model" not in DEFAULT_MODEL_FALLBACK_CHAIN


def test_get_model_fallback_chain_no_circular_wrapping():
    """Verify starting with a downstream tier cascades only downstream without wrap-around."""
    chain = get_model_fallback_chain("claude-opus-4-6-thinking")
    assert chain == ["claude-opus-4-6-thinking"]
    assert "gemini-3.8-flash-high" not in chain

    chain_last = get_model_fallback_chain("claude-opus-4-6-thinking")
    assert chain_last == ["claude-opus-4-6-thinking"]


def test_get_model_fallback_chain_unknown_initial_model():
    """Verify unknown initial model is prepended to default chain."""
    chain = get_model_fallback_chain("experimental-gemini-4.0")
    assert chain[0] == "experimental-gemini-4.0"
    assert chain[1:] == DEFAULT_MODEL_FALLBACK_CHAIN


def test_get_model_fallback_chain_empty_custom_chain():
    """Verify empty custom chain is preserved and not replaced with default chain."""
    assert get_model_fallback_chain(custom_chain=[]) == []
    assert get_model_fallback_chain("model-x", custom_chain=[]) == ["model-x"]


def test_get_model_fallback_chain_custom_chain_cascading():
    """Verify custom chain cascades downstream consistently."""
    custom = ["tier-1", "tier-2", "tier-3"]
    assert get_model_fallback_chain(custom_chain=custom) == ["tier-1", "tier-2", "tier-3"]
    assert get_model_fallback_chain("tier-2", custom_chain=custom) == ["tier-2", "tier-3"]
    assert get_model_fallback_chain("tier-0", custom_chain=custom) == [
        "tier-0",
        "tier-1",
        "tier-2",
        "tier-3",
    ]


# ============================================================================
# 4. Checkpointing: Atomic Writes, Dict Validation, Exclude (Findings 8, 9, 10)
# ============================================================================


def test_save_checkpoint_atomic_write_and_no_tmp_leftover():
    """Verify save_checkpoint writes atomically without leaving temporary files behind."""
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = {"task": "test", "step": 1}
        path = save_checkpoint(payload, cwd=tmpdir)
        assert os.path.isfile(path)

        # Verify no .tmp files left in the directory
        dir_files = os.listdir(tmpdir)
        assert dir_files == [CHECKPOINT_FILENAME]

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == payload


def test_load_checkpoint_validates_dictionary_structure():
    """Verify load_checkpoint returns None and warns when JSON is not a dictionary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ckpt_path = os.path.join(tmpdir, CHECKPOINT_FILENAME)

        # 1. Non-dict: JSON array
        with open(ckpt_path, "w", encoding="utf-8") as f:
            f.write('["step1", "step2"]')
        assert load_checkpoint(cwd=tmpdir) is None

        # 2. Non-dict: JSON primitive string
        with open(ckpt_path, "w", encoding="utf-8") as f:
            f.write('"simple string"')
        assert load_checkpoint(cwd=tmpdir) is None

        # 3. Non-dict: JSON primitive integer
        with open(ckpt_path, "w", encoding="utf-8") as f:
            f.write("42")
        assert load_checkpoint(cwd=tmpdir) is None

        # 4. Corrupted / incomplete JSON
        with open(ckpt_path, "w", encoding="utf-8") as f:
            f.write('{"unclosed": ')
        assert load_checkpoint(cwd=tmpdir) is None

        # 5. Valid dict loads successfully
        with open(ckpt_path, "w", encoding="utf-8") as f:
            f.write('{"valid": true, "count": 1}')
        loaded = load_checkpoint(cwd=tmpdir)
        assert loaded == {"valid": True, "count": 1}


def test_clear_checkpoint_removes_file():
    """Verify clear_checkpoint removes the file and handles non-existent file gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_checkpoint({"status": "running"}, cwd=tmpdir)
        assert load_checkpoint(cwd=tmpdir) is not None

        clear_checkpoint(cwd=tmpdir)
        assert load_checkpoint(cwd=tmpdir) is None

        # Clearing again on non-existent file should not raise
        clear_checkpoint(cwd=tmpdir)


def test_git_exclude_checkpoint():
    """Verify _exclude_checkpoint_from_git adds checkpoint filename to .git/info/exclude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_info_dir = os.path.join(tmpdir, ".git", "info")
        os.makedirs(git_info_dir)

        _exclude_checkpoint_from_git(tmpdir)
        exclude_path = os.path.join(git_info_dir, "exclude")
        assert os.path.isfile(exclude_path)

        with open(exclude_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert CHECKPOINT_FILENAME in content

        # Call again to ensure idempotency (no duplicate entries)
        _exclude_checkpoint_from_git(tmpdir)
        with open(exclude_path, "r", encoding="utf-8") as f:
            content_after = f.read()
        assert content_after.count(CHECKPOINT_FILENAME) == 1


def test_save_checkpoint_invokes_git_exclude():
    """Verify save_checkpoint automatically ensures CHECKPOINT_FILENAME is excluded in .git/info/exclude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_info = os.path.join(tmpdir, ".git", "info")
        os.makedirs(git_info)

        save_checkpoint({"status": "blocked"}, cwd=tmpdir)
        exclude_path = os.path.join(git_info, "exclude")
        assert os.path.isfile(exclude_path)
        with open(exclude_path, "r", encoding="utf-8") as f:
            assert CHECKPOINT_FILENAME in f.read()


def test_git_exclude_checkpoint_worktree_support():
    """Verify _exclude_checkpoint_from_git correctly resolves gitdir file pointers in worktrees."""
    with tempfile.TemporaryDirectory() as tmpdir:
        main_git_dir = os.path.join(tmpdir, "main_repo", ".git", "worktrees", "wt1")
        worktree_dir = os.path.join(tmpdir, "wt1_workdir")
        os.makedirs(main_git_dir)
        os.makedirs(worktree_dir)

        # .git in worktree is a pointer file
        git_pointer = os.path.join(worktree_dir, ".git")
        with open(git_pointer, "w", encoding="utf-8") as f:
            f.write(f"gitdir: {main_git_dir}\n")

        _exclude_checkpoint_from_git(worktree_dir)

        exclude_file = os.path.join(main_git_dir, "info", "exclude")
        assert os.path.isfile(exclude_file)
        with open(exclude_file, "r", encoding="utf-8") as f:
            assert CHECKPOINT_FILENAME in f.read()


def test_git_exclude_checkpoint_relative_worktree_support():
    """Verify _exclude_checkpoint_from_git handles relative gitdir paths in worktrees."""
    with tempfile.TemporaryDirectory() as tmpdir:
        main_git = os.path.join(tmpdir, "repo", ".git", "worktrees", "wt2")
        workdir = os.path.join(tmpdir, "repo", "wt2")
        os.makedirs(main_git)
        os.makedirs(workdir)

        git_pointer = os.path.join(workdir, ".git")
        rel_path = os.path.relpath(main_git, workdir)
        with open(git_pointer, "w", encoding="utf-8") as f:
            f.write(f"gitdir: {rel_path}\n")

        _exclude_checkpoint_from_git(workdir)

        exclude_file = os.path.join(main_git, "info", "exclude")
        assert os.path.isfile(exclude_file)
        with open(exclude_file, "r", encoding="utf-8") as f:
            assert CHECKPOINT_FILENAME in f.read()


def test_save_checkpoint_serializes_non_primitive_objects():
    """Verify save_checkpoint handles non-JSON-serializable objects (sets, exceptions) via default=str."""
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = {
            "tags": {"alpha", "beta"},
            "error": RuntimeError("Model unavailable"),
            "count": 42,
        }
        path = save_checkpoint(payload, cwd=tmpdir)
        assert os.path.isfile(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["count"] == 42
        assert "Model unavailable" in data["error"]
        assert isinstance(data["tags"], str)


def test_save_checkpoint_error_logging_on_failure(capsys):
    """Verify save_checkpoint logs error to sys.stderr before bubbling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch json.dump to raise an IOError
        with patch("json.dump", side_effect=IOError("Simulated disk full")):
            with pytest.raises(IOError):
                save_checkpoint({"key": "val"}, cwd=tmpdir)

        captured = capsys.readouterr()
        assert "Notice: Failed to save checkpoint file: Simulated disk full" in captured.err


# ============================================================================
# 5. run_git Stderr Diagnostics (Finding 11)
# ============================================================================


def test_run_git_success():
    """Verify run_git returns stripped output on success."""
    output = run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_root)
    assert output == "true"


def test_run_git_stderr_diagnostics_on_failure(capsys):
    """Verify run_git prints stderr to sys.stderr before raising CalledProcessError."""
    with pytest.raises(subprocess.CalledProcessError):
        run_git(["invalid-git-subcommand-xyz"], cwd=repo_root)

    captured = capsys.readouterr()
    assert "Git command failed (git invalid-git-subcommand-xyz):" in captured.err
    assert "is not a git command" in captured.err


# ============================================================================
# 6. update_project_status_blocked & Client Variants (Findings 1 & 12)
# ============================================================================


def test_update_project_status_blocked_with_set_status_client():
    """Verify update_project_status_blocked works with client implementing set_status."""

    class ClientWithSetStatus:
        def __init__(self):
            self.calls = []

        def set_status(self, entity_url: str, status: str):
            self.calls.append((entity_url, status))

    mock_client = ClientWithSetStatus()
    with patch("antigravity_runner.run_gh") as mock_gh:
        update_project_status_blocked(
            issue_or_pr_number=50,
            repo="test-owner/test-repo",
            is_pr=False,
            client=mock_client,
        )

        mock_gh.assert_called_once_with(
            ["issue", "edit", "50", "--add-label", "Blocked"],
            repo="test-owner/test-repo",
        )
        assert len(mock_client.calls) == 1
        assert mock_client.calls[0] == (
            "https://github.com/test-owner/test-repo/issues/50",
            "Blocked",
        )


def test_update_project_status_blocked_with_add_and_edit_status_client():
    """Verify update_project_status_blocked works with client implementing add_item & edit_status."""

    class ClientWithAddAndEdit:
        def __init__(self):
            self.added = []
            self.edited = []

        def add_item(self, url: str):
            self.added.append(url)
            return "item-node-99"

        def edit_status(self, item_id: str, status: str):
            self.edited.append((item_id, status))

    mock_client = ClientWithAddAndEdit()
    with patch("antigravity_runner.run_gh"):
        update_project_status_blocked(
            issue_or_pr_number=12,
            repo="test-owner/test-repo",
            is_pr=True,
            client=mock_client,
        )

        assert mock_client.added == ["https://github.com/test-owner/test-repo/pull/12"]
        assert mock_client.edited == [("item-node-99", "Blocked")]


def test_update_project_status_blocked_client_none_graceful_handling():
    """Verify update_project_status_blocked handles client=None and missing client dependencies gracefully."""
    with patch("antigravity_runner.run_gh"):
        update_project_status_blocked(
            issue_or_pr_number=999,
            repo="test-owner/test-repo",
            is_pr=False,
            client=None,
        )


def test_update_project_status_blocked_client_exception_suppressed(capsys):
    """Verify exceptions from the project client are caught and logged to stderr."""

    class FailingClient:
        def set_status(self, entity_url: str, status: str):
            raise RuntimeError("API timeout when updating project card")

    with patch("antigravity_runner.run_gh"):
        update_project_status_blocked(
            issue_or_pr_number=50,
            repo="test-owner/test-repo",
            is_pr=False,
            client=FailingClient(),
        )

    captured = capsys.readouterr()
    assert "Notice: Failed to update project status: API timeout" in captured.err


# ============================================================================
# 7. unblock_entity & Project Board Transitions (Finding 6)
# ============================================================================


def test_unblock_entity_with_set_status_client():
    """Verify unblock_entity removes Blocked label and sets project status to In Progress."""

    class ClientWithSetStatus:
        def __init__(self):
            self.calls = []

        def set_status(self, entity_url: str, status: str):
            self.calls.append((entity_url, status))

    mock_client = ClientWithSetStatus()
    with patch("antigravity_runner.run_gh") as mock_gh:
        unblock_entity(
            issue_or_pr_number=42,
            repo="test-owner/test-repo",
            is_pr=False,
            client=mock_client,
            target_status="In Progress",
        )
        mock_gh.assert_called_once_with(
            ["issue", "edit", "42", "--remove-label", "Blocked"],
            repo="test-owner/test-repo",
        )
        assert mock_client.calls == [
            ("https://github.com/test-owner/test-repo/issues/42", "In Progress")
        ]


def test_unblock_entity_pr_with_done_status():
    """Verify unblock_entity removes Blocked label from PR and sets project status to Done."""

    class ClientWithAddAndEdit:
        def __init__(self):
            self.added = []
            self.edited = []

        def add_item(self, url: str):
            self.added.append(url)
            return "item-node-88"

        def edit_status(self, item_id: str, status: str):
            self.edited.append((item_id, status))

    mock_client = ClientWithAddAndEdit()
    with patch("antigravity_runner.run_gh") as mock_gh:
        unblock_entity(
            issue_or_pr_number=99,
            repo="test-owner/test-repo",
            is_pr=True,
            client=mock_client,
            target_status="Done",
        )
        mock_gh.assert_called_once_with(
            ["pr", "edit", "99", "--remove-label", "Blocked"],
            repo="test-owner/test-repo",
        )
        assert mock_client.added == ["https://github.com/test-owner/test-repo/pull/99"]
        assert mock_client.edited == [("item-node-88", "Done")]


def test_unblock_entity_client_exception_suppressed(capsys):
    """Verify unblock_entity suppresses client exceptions and logs notice."""

    class FailingClient:
        def set_status(self, entity_url: str, status: str):
            raise RuntimeError("Project board connection error")

    with patch("antigravity_runner.run_gh"):
        unblock_entity(
            issue_or_pr_number=50,
            repo="test-owner/test-repo",
            is_pr=False,
            client=FailingClient(),
        )

    captured = capsys.readouterr()
    assert "Notice: Failed to update project status: Project board connection error" in captured.err


# ============================================================================
# 8. find_plan_issue_for_pr (Finding 2)
# ============================================================================


def test_find_plan_issue_for_pr_from_closing_issues_references():
    """Verify find_plan_issue_for_pr detects plan issue from closingIssuesReferences."""
    pr_meta = {
        "body": "Fixes something",
        "closingIssuesReferences": [
            {"number": 10, "labels": [{"name": "Request"}]},
            {"number": 11, "labels": [{"name": "Plan"}]},
        ],
        "comments": [],
    }
    with patch("antigravity_runner.run_gh", return_value=json.dumps(pr_meta)):
        assert find_plan_issue_for_pr(50, "test-owner/test-repo") == 11


def test_find_plan_issue_for_pr_from_body_plan_syntax():
    """Verify find_plan_issue_for_pr detects explicit Plan: #N in PR body."""
    pr_meta = {
        "body": "## Summary\nImplemented changes.\nPlan: #77\nCloses #76",
        "closingIssuesReferences": [],
        "comments": [],
    }
    with patch("antigravity_runner.run_gh", return_value=json.dumps(pr_meta)):
        assert find_plan_issue_for_pr(50, "test-owner/test-repo") == 77


def test_find_plan_issue_for_pr_from_comments():
    """Verify find_plan_issue_for_pr detects Plan in PR comments."""
    pr_meta = {
        "body": "Summary without plan mention",
        "closingIssuesReferences": [],
        "comments": [{"body": "Child Plan: #84"}],
    }
    with patch("antigravity_runner.run_gh", return_value=json.dumps(pr_meta)):
        assert find_plan_issue_for_pr(50, "test-owner/test-repo") == 84


def test_find_plan_issue_for_pr_from_closing_keyword():
    """Verify find_plan_issue_for_pr checks referenced issue labels to select the Plan issue."""
    pr_meta = {
        "body": "Closes #20\nCloses #21",
        "closingIssuesReferences": [],
        "comments": [],
    }

    def gh_side_effect(args, repo=""):
        if args[:2] == ["pr", "view"]:
            return json.dumps(pr_meta)
        if args[:2] == ["issue", "view"] and args[2] == "21":
            return json.dumps({"labels": [{"name": "Plan"}], "title": "Plan: Fix issue"})
        if args[:2] == ["issue", "view"] and args[2] == "20":
            return json.dumps({"labels": [{"name": "Request"}], "title": "Request: Fix issue"})
        return "{}"

    with patch("antigravity_runner.run_gh", side_effect=gh_side_effect):
        assert find_plan_issue_for_pr(50, "test-owner/test-repo") == 21


def test_find_plan_issue_for_pr_not_found():
    """Verify find_plan_issue_for_pr returns None when no plan is linked."""
    pr_meta = {
        "body": "Just some PR with no closing references",
        "closingIssuesReferences": [],
        "comments": [],
    }
    with patch("antigravity_runner.run_gh", return_value=json.dumps(pr_meta)):
        assert find_plan_issue_for_pr(50, "test-owner/test-repo") is None


# ============================================================================
# 9. run_agy_prompt Stderr + Stdout Quota Detection (Finding 9)
# ============================================================================


def test_run_agy_prompt_combines_stderr_and_stdout_for_quota():
    """Verify run_agy_prompt detects quota exhaustion in stdout even if stderr has text."""
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["agy"],
        output="429 Resource exhausted: Quota limit hit",
        stderr="DeprecationWarning: something is deprecated in environment",
    )
    with (
        patch("subprocess.run", side_effect=error),
        patch("time.sleep") as mock_sleep,
    ):
        result = run_agy_prompt("Test prompt", max_retries=1, base_delay=0.01)
        assert "Quota exhausted across all fallback models" in result
        assert mock_sleep.called


# ============================================================================
# 10. Resuming Feature Branch & Checkpoint Skip (Findings 3 & 4)
# ============================================================================


def test_handle_implement_tracks_existing_remote_branch():
    """Verify handle_implement checks out existing remote branch instead of recreating from origin/main."""
    plan_data = json.dumps({"title": "Plan: Test Feature", "body": "Plan details"})

    git_calls = []

    def mock_run_git(args, cwd=None):
        git_calls.append(list(args))
        if args == ["branch", "-r"]:
            return "origin/main\norigin/feature/test-feature"
        if args == ["branch"]:
            return "main"
        if args == ["status", "--porcelain"]:
            return "M test.py"
        return ""

    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_git", side_effect=mock_run_git),
        patch("antigravity_runner.load_checkpoint", return_value=None),
        patch("antigravity_runner.run_agy_prompt", return_value="Implemented successfully"),
        patch("subprocess.run", return_value=MagicMock(returncode=0)),
        patch("antigravity_runner.handle_self_review"),
        patch("antigravity_runner.handle_plan_alignment"),
    ):

        def gh_side_effect(args, repo=""):
            if args[:2] == ["issue", "view"]:
                return plan_data
            if args[:2] == ["pr", "list"]:
                return json.dumps([{"number": 99}])
            return ""

        mock_gh.side_effect = gh_side_effect

        handle_implement(plan_number=2, request_number=1, repo="test-owner/test-repo")

        # Verify git checkout used existing remote tracking branch, NOT -b from origin/main
        checkout_call = [c for c in git_calls if c[:2] == ["checkout", "-b"]]
        assert len(checkout_call) == 1
        assert checkout_call[0] == [
            "checkout",
            "-b",
            "feature/test-feature",
            "origin/feature/test-feature",
        ]


def test_handle_implement_skips_when_pr_already_exists():
    """Verify handle_implement skips implementation step when open PR already exists for branch."""
    plan_data = json.dumps({"title": "Plan: Existing PR", "body": "Plan details"})

    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_git", return_value=""),
        patch("antigravity_runner.load_checkpoint", return_value={"completed_steps": ["Step 1"]}),
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
        patch("antigravity_runner.handle_self_review") as mock_review,
        patch("antigravity_runner.handle_plan_alignment") as mock_align,
    ):

        def gh_side_effect(args, repo=""):
            if args[:2] == ["issue", "view"]:
                return plan_data
            if args[:2] == ["pr", "list"]:
                return json.dumps([{"number": 123}])
            return ""

        mock_gh.side_effect = gh_side_effect

        handle_implement(plan_number=2, request_number=1, repo="test-owner/test-repo")

        # run_agy_prompt should not be called to implement
        mock_agy.assert_not_called()
        # review and alignment should be resumed directly
        mock_review.assert_called_once_with(123, 2, "test-owner/test-repo")
        mock_align.assert_called_once_with(123, 2, 1, "test-owner/test-repo")


# ============================================================================
# 11. handle_plan_alignment Checkpoint Cleanup & Unblock (Findings 4 & 6)
# ============================================================================


def test_handle_plan_alignment_matching_clears_checkpoint_and_unblocks():
    """Verify handle_plan_alignment clears checkpoint and unblocks entities with status Done on match."""
    plan_meta = json.dumps({"body": "Scope content", "comments": []})

    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.run_agy_prompt", return_value="MATCHES_PLAN_YES: All aligned"),
        patch("antigravity_runner.clear_checkpoint") as mock_clear,
        patch("antigravity_runner.unblock_entity") as mock_unblock,
    ):

        def gh_side_effect(args, repo=""):
            if args[:2] == ["pr", "diff"]:
                return "diff content"
            if args[:2] == ["issue", "view"]:
                return plan_meta
            return ""

        mock_gh.side_effect = gh_side_effect

        handle_plan_alignment(
            pr_number=50, plan_number=43, request_number=42, repo="test-owner/test-repo"
        )

        mock_clear.assert_called_once_with(cwd=WORKSPACE_DIR)
        assert mock_unblock.call_count == 3
        mock_unblock.assert_any_call(50, "test-owner/test-repo", is_pr=True, target_status="Done")
        mock_unblock.assert_any_call(43, "test-owner/test-repo", is_pr=False, target_status="Done")
        mock_unblock.assert_any_call(42, "test-owner/test-repo", is_pr=False, target_status="Done")


# ============================================================================
# 12. handle_self_review Plan Deviation Quota Handling (Finding 8)
# ============================================================================


def test_handle_self_review_deviation_quota_exhausted_halts():
    """Verify handle_self_review halts when deviation prompt encounters quota exhaustion."""
    plan_meta = json.dumps({"body": "Scope content"})

    with (
        patch("antigravity_runner.run_gh") as mock_gh,
        patch("antigravity_runner.find_parent_request_number", return_value=42),
        patch("antigravity_runner.run_agy_prompt") as mock_agy,
    ):

        def gh_side_effect(args, repo=""):
            if args[:2] == ["pr", "diff"]:
                return "diff content"
            if args[:2] == ["issue", "view"]:
                return plan_meta
            return ""

        mock_gh.side_effect = gh_side_effect

        # 1st call: review findings with OUT_OF_SCOPE
        # 2nd call: deviation prompt returns quota exhausted error
        mock_agy.side_effect = [
            "OUT_OF_SCOPE: Database schema modification needed.",
            "[Antigravity Agent Execution Error]: Quota exhausted across all fallback models (gemini-3.8-flash-high): 429",
        ]

        handle_self_review(pr_number=50, plan_number=43, repo="test-owner/test-repo")

        # After deviation prompt exhausted quota, fix_prompt should NOT be called (only 2 calls to agy)
        assert mock_agy.call_count == 2


# ============================================================================
# 13. dispatch_event Resume on PR (Finding 2)
# ============================================================================


def test_dispatch_event_pr_issue_comment_resume():
    """Verify commenting /resume on a PR invokes handle_self_review."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        json.dump(
            {
                "action": "created",
                "repository": {"full_name": "test-owner/test-repo"},
                "issue": {
                    "number": 55,
                    "pull_request": {
                        "url": "https://api.github.com/repos/test-owner/test-repo/pulls/55"
                    },
                    "labels": [],
                },
                "comment": {
                    "body": "/resume",
                    "user": {"login": "human-reviewer"},
                },
            },
            f,
        )
        temp_path = f.name

    try:
        with (
            patch("antigravity_runner.find_plan_issue_for_pr", return_value=40) as mock_find_plan,
            patch("antigravity_runner.handle_self_review") as mock_self_review,
            patch("antigravity_runner.unblock_entity") as mock_unblock,
        ):
            dispatch_event(temp_path, "issue_comment")

            mock_find_plan.assert_called_once_with(55, "test-owner/test-repo")
            mock_self_review.assert_called_once_with(55, 40, "test-owner/test-repo")
            mock_unblock.assert_any_call(
                55, "test-owner/test-repo", is_pr=True, target_status="In Progress"
            )
            mock_unblock.assert_any_call(
                40, "test-owner/test-repo", is_pr=False, target_status="In Progress"
            )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ============================================================================
# 14. Project Constants DRY (Finding 10)
# ============================================================================


def test_project_constants_imported_from_project_automation():
    """Verify PROJECT_OWNER and PROJECT_NUMBER are imported from project_automation."""
    import project_automation

    assert PROJECT_OWNER == project_automation.PROJECT_OWNER
    assert PROJECT_NUMBER == project_automation.PROJECT_NUMBER


def test_default_model_fallback_chain_structure():
    """Verify fallback chain contains primary Gemini model and Claude Opus fallback only."""
    from antigravity_runner import DEFAULT_MODEL_FALLBACK_CHAIN

    assert DEFAULT_MODEL_FALLBACK_CHAIN == [
        "gemini-3.8-flash-high",
        "claude-opus-4-6-thinking",
    ]


def test_is_workflow_permission_error():
    """Verify detection of git push errors caused by missing workflow write permissions."""
    from antigravity_runner import is_workflow_permission_error

    err_github_app = (
        "! [remote rejected] branch -> branch (refusing to allow a GitHub App to create "
        "or update workflow .github/workflows/verify-docs.yml without workflows permission)"
    )
    assert is_workflow_permission_error(err_github_app) is True

    err_token = "error: refusing to allow a GitHub App to create or update workflow"
    assert is_workflow_permission_error(err_token) is True

    assert is_workflow_permission_error("failed: without workflows permission") is True

    assert is_workflow_permission_error("error: failed to push some refs to remote") is False
    assert is_workflow_permission_error("fatal: remote origin already exists") is False
    assert is_workflow_permission_error("") is False
    assert is_workflow_permission_error(None) is False
