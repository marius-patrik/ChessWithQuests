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
    QUOTA_EXHAUSTION_PATTERNS,
    STATE_DIR,
    calculate_backoff,
    clear_checkpoint,
    get_model_fallback_chain,
    is_quota_exhausted,
    load_checkpoint,
    run_git,
    save_checkpoint,
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


def test_is_quota_exhausted_empty_and_unrelated():
    """Verify empty or unrelated errors return False."""
    assert is_quota_exhausted("") is False
    assert is_quota_exhausted(None) is False
    assert is_quota_exhausted("Keyring authorization denied.") is False
    assert is_quota_exhausted("SyntaxError: invalid syntax in file.py") is False
    assert is_quota_exhausted("fatal: not a git repository") is False


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
    chain = get_model_fallback_chain("gemini-3.7-flash-high")
    assert chain == ["gemini-3.7-flash-high", "gemini-3.6-flash-high", "claude-sonnet-4-6"]
    assert "gemini-3.8-flash-high" not in chain
    assert "gemini-3.8-flash-medium" not in chain

    chain_last = get_model_fallback_chain("claude-sonnet-4-6")
    assert chain_last == ["claude-sonnet-4-6"]


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
