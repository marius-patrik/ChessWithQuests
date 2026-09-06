"""Unit tests verifying the .claude symlink at repository root."""

import os


def test_claude_symlink_exists_and_is_symlink() -> None:
    """Verify .claude exists at the repository root and is a symbolic link."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    claude_path = os.path.join(repo_root, ".claude")
    assert os.path.islink(claude_path), f"Expected {claude_path} to be a symbolic link"
    assert os.path.exists(claude_path), f"Expected {claude_path} to exist"


def test_claude_symlink_target_points_to_agents() -> None:
    """Verify .claude target points directly and relatively to .agents."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    claude_path = os.path.join(repo_root, ".claude")
    target = os.readlink(claude_path)
    assert target == ".agents", f"Expected symlink target to be '.agents', got '{target}'"


def test_claude_symlink_resolves_agents_contents() -> None:
    """Verify navigation through .claude resolves canonical agent documentation files."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    claude_path = os.path.join(repo_root, ".claude")

    expected_files = [
        os.path.join(claude_path, "AGENTS.md"),
        os.path.join(claude_path, "CLAUDE.md"),
        os.path.join(claude_path, "README.md"),
        os.path.join(claude_path, "notes", "chess_rules.md"),
    ]

    for file_path in expected_files:
        assert os.path.isfile(
            file_path
        ), f"Expected file {file_path} to exist and be a regular file"
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0, f"Expected content in {file_path}"

    notes_dir = os.path.join(claude_path, "notes")
    assert os.path.isdir(notes_dir), f"Expected {notes_dir} to be a directory"
