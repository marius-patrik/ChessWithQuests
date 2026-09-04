import os
import pytest


def test_docs_md_and_index_symlink():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_md = os.path.join(repo_root, "DOCS.md")
    index_md = os.path.join(repo_root, "docs", "INDEX.md")
    agents_docs_md = os.path.join(repo_root, ".agents", "DOCS.md")

    assert os.path.exists(docs_md), "DOCS.md must exist at root"
    assert not os.path.islink(docs_md), "DOCS.md must be a real file"

    assert os.path.exists(index_md), "docs/INDEX.md must exist"
    assert os.path.islink(index_md), "docs/INDEX.md must be a symlink"
    assert os.readlink(index_md) == "../DOCS.md", "docs/INDEX.md must symlink to ../DOCS.md"

    assert os.path.exists(agents_docs_md), ".agents/DOCS.md must exist"
    assert os.path.islink(agents_docs_md), ".agents/DOCS.md must be a symlink"
    assert os.readlink(agents_docs_md) == "../DOCS.md", ".agents/DOCS.md must symlink to ../DOCS.md"

    with open(docs_md, encoding="utf-8") as f:
        docs_content = f.read()

    with open(index_md, encoding="utf-8") as f:
        index_content = f.read()

    with open(agents_docs_md, encoding="utf-8") as f:
        agents_docs_content = f.read()

    assert index_content == docs_content, "docs/INDEX.md content must match DOCS.md"
    assert agents_docs_content == docs_content, ".agents/DOCS.md content must match DOCS.md"

    # Verify that every documentation file in docs/ (except INDEX.md) is referenced in DOCS.md
    docs_dir = os.path.join(repo_root, "docs")
    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".md") and file != "INDEX.md":
                rel_path = os.path.relpath(os.path.join(root, file), repo_root)
                assert rel_path in docs_content, f"Documentation file {rel_path} must be referenced in DOCS.md"


def test_agents_rule_requires_index_update():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    assert "DOCS.md" in content
    assert "INDEX.md" in content
    assert "updated with every docs change" in content or "index" in content.lower()

