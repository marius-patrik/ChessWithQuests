import os
import pytest


def test_agents_and_symlinks_resolve():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, ".agents", "AGENTS.md")
    readme_file = os.path.join(repo_root, "README.md")
    contributing_file = os.path.join(repo_root, "CONTRIBUTING.md")

    assert os.path.exists(agents_file), ".agents/AGENTS.md must exist"
    assert os.path.islink(readme_file), "README.md must be a symlink"
    assert os.path.islink(contributing_file), "CONTRIBUTING.md must be a symlink"
    assert os.readlink(readme_file) == ".agents/AGENTS.md"
    assert os.readlink(contributing_file) == ".agents/AGENTS.md"

    with open(agents_file, encoding="utf-8") as f:
        agents_content = f.read()

    with open(readme_file, encoding="utf-8") as f:
        readme_content = f.read()

    with open(contributing_file, encoding="utf-8") as f:
        contrib_content = f.read()

    assert "ChessWithQuests" in readme_content
    assert readme_content == agents_content
    assert contrib_content == agents_content

    docs_dir = os.path.join(repo_root, "docs")
    notes_dir = os.path.join(repo_root, "notes")
    assert os.path.isdir(docs_dir), "docs must be a real directory at root"
    assert not os.path.islink(docs_dir), "docs must not be a symlink at root"
    assert os.path.isdir(notes_dir), "notes must be a real directory at root"
    assert not os.path.islink(notes_dir), "notes must not be a symlink at root"

    agents_docs = os.path.join(repo_root, ".agents", "docs")
    agents_notes = os.path.join(repo_root, ".agents", "notes")
    assert os.path.islink(agents_docs), ".agents/docs must be a symlink"
    assert os.path.islink(agents_notes), ".agents/notes must be a symlink"
    assert os.readlink(agents_docs) == "../docs"
    assert os.readlink(agents_notes) == "../notes"
    assert os.path.exists(os.path.join(agents_docs, "controller")), ".agents/docs must resolve to docs folder"
    assert os.path.exists(os.path.join(agents_notes, "object_model.md")), ".agents/notes must resolve to notes folder"


