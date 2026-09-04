import os
import pytest


def test_documentation_mirrors_code_structure():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(repo_root, "src")
    missing_docs = []
    checked_count = 0
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                checked_count += 1
                rel_path = os.path.relpath(os.path.join(root, file), src_dir)
                doc_rel_path = os.path.splitext(rel_path)[0] + ".md"
                doc_full_path = os.path.join(repo_root, "docs", doc_rel_path)
                if not os.path.exists(doc_full_path):
                    missing_docs.append(doc_rel_path)

    assert checked_count == 28, f"Expected 28 Python modules, found {checked_count}"
    assert missing_docs == [], f"Missing documentation files in docs/: {missing_docs}"


def test_verify_docs_workflow_exists():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "verify-docs.yml")

    assert os.path.isfile(workflow_path), "verify-docs.yml workflow must exist"
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    assert "Verify Docs Layout" in content
    assert "src" in content and "docs" in content
    assert "test_docs_mirror.py" in content
