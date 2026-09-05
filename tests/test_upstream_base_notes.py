import os
import pytest


def test_upstream_base_notes_exists_and_documents_fork_diff():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    notes_file = os.path.join(repo_root, "notes", "upstream_base.md")

    assert os.path.exists(notes_file), "notes/upstream_base.md must exist"

    with open(notes_file, encoding="utf-8") as f:
        content = f.read()

    lower_content = content.lower()
    assert "upstream-base" in lower_content
    assert "a98e36d" in lower_content
    assert "docekalgjkt/chesswithquests" in lower_content
    assert "protection" in lower_content
