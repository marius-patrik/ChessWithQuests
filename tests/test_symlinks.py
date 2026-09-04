import os
import pytest


def test_agents_and_symlinks_resolve():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, ".agents", "agents.md")
    readme_file = os.path.join(repo_root, "README.md")
    contributing_file = os.path.join(repo_root, "contributing.md")

    assert os.path.exists(agents_file), ".agents/agents.md must exist"
    assert os.path.islink(readme_file), "README.md must be a symlink"
    assert os.path.islink(contributing_file), "contributing.md must be a symlink"

    with open(agents_file, encoding="utf-8") as f:
        agents_content = f.read()

    with open(readme_file, encoding="utf-8") as f:
        readme_content = f.read()

    with open(contributing_file, encoding="utf-8") as f:
        contrib_content = f.read()

    assert "ChessWithQuests" in readme_content
    assert readme_content == agents_content
    assert contrib_content == agents_content
