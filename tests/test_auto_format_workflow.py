import os
import pytest


def test_auto_format_workflow_configuration():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_file = os.path.join(repo_root, ".github", "workflows", "auto-format.yml")

    assert os.path.isfile(workflow_file), ".github/workflows/auto-format.yml must exist"

    with open(workflow_file, encoding="utf-8") as f:
        content = f.read()

    assert "push:" in content
    assert "contents: write" in content
    assert "black" in content
    assert "github-actions[bot]" in content
    assert "actions/checkout@v4" in content


def test_dev_requirements_and_pyproject_include_black():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    req_file = os.path.join(repo_root, "requirements-dev.txt")
    pyproject_file = os.path.join(repo_root, "pyproject.toml")

    with open(req_file, encoding="utf-8") as f:
        req_content = f.read()
    assert "black" in req_content

    with open(pyproject_file, encoding="utf-8") as f:
        pyproject_content = f.read()
    assert "[tool.black]" in pyproject_content
