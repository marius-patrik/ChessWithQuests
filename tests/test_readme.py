"""Tests verifying README contents and attribution."""

import os
import pytest


def test_readme_contains_forked_attribution():
    """Verify that README.md contains class project attribution and no shared repo disclaimer."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")
    assert os.path.isfile(readme_path), "README.md must exist at repository root"

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Forked from class project base" in content
    assert "Shared repository of all students" not in content
