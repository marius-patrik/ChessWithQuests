import os
import pytest


def test_documentation_mirrors_code_structure():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code_dirs = ["controller", "model", "view"]

    missing_docs = []
    checked_count = 0
    for code_dir in code_dirs:
        full_code_dir = os.path.join(repo_root, code_dir)
        for root, _, files in os.walk(full_code_dir):
            for file in files:
                if file.endswith(".py"):
                    checked_count += 1
                    rel_path = os.path.relpath(os.path.join(root, file), repo_root)
                    doc_rel_path = os.path.splitext(rel_path)[0] + ".md"
                    doc_full_path = os.path.join(repo_root, "docs", doc_rel_path)
                    if not os.path.exists(doc_full_path):
                        missing_docs.append(doc_rel_path)

    assert checked_count == 27, f"Expected 27 Python modules, found {checked_count}"
    assert missing_docs == [], f"Missing documentation files in docs/: {missing_docs}"
