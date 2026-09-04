import os
import pytest


def test_documentation_mirrors_code_structure():
    """Verify that all source modules are documented dynamically without static markdown files in docs/."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(repo_root, "src")
    docs_dir = os.path.join(repo_root, "docs")

    # Count source modules
    source_count = sum(1 for root, _, files in os.walk(src_dir) for f in files if f.endswith(".py"))
    assert source_count >= 28, f"Expected at least 28 Python modules, found {source_count}"

    # Verify docs/ contains only index.md and no static boilerplate files
    doc_files = [f for root, _, files in os.walk(docs_dir) for f in files if f.endswith(".md")]
    assert doc_files == ["index.md"], f"Expected only index.md in docs/, found: {doc_files}"


def test_verify_docs_workflow_exists():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "verify-docs.yml")

    assert os.path.isfile(workflow_path), "verify-docs.yml workflow must exist"
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    assert "Verify Docs Layout" in content
    assert "src" in content and "docs" in content
    assert "test_docs_mirror.py" in content
