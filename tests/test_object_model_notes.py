import os
import pytest


def test_object_model_notes_exists_and_requires_approval():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    notes_file = os.path.join(repo_root, "notes", "object_model.md")

    assert os.path.exists(notes_file), "notes/object_model.md must exist"

    with open(notes_file, encoding="utf-8") as f:
        content = f.read()

    assert "https://app.diagrams.net/" in content
    assert "approved by the user" in content.lower() or "user approval" in content.lower()
    assert "translation policy" in content.lower() or "translations" in content.lower()
