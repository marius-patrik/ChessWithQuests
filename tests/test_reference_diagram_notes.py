import os
import pytest


def test_reference_diagram_notes_exists_and_has_link():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_file = os.path.join(repo_root, "notes", "reference_diagram.md")
    assert os.path.exists(ref_file), "notes/reference_diagram.md must exist"

    with open(ref_file, encoding="utf-8") as f:
        content = f.read()

    assert "https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8" in content
    assert "C5RBs43oDa-KdzZeNtuy" in content
