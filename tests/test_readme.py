"""Unit tests verifying README documentation and architecture links."""

import os
import pytest


def test_readme_exists_and_contains_docs_and_diagram_links() -> None:
    """Verify README.md exists and contains valid links to docs and architecture diagram."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")
    assert os.path.exists(readme_path), "README.md must exist at repo root"

    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    docs_url = "https://marius-patrik.github.io/ChessWithQuests/"
    diagram_url = "https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8"
    page_id = "C5RBs43oDa-KdzZeNtuy"

    assert docs_url in content, f"README.md must include documentation URL: {docs_url}"
    assert diagram_url in content, f"README.md must include architecture diagram URL: {diagram_url}"
    assert page_id in content, f"README.md diagram link must reference pageId: {page_id}"
