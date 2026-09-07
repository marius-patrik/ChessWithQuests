import os
import pytest


def test_auto_format_workflow_calls_the_pinned_pipeline():
    """Formatting runs upstream now, so this file names a pin rather than a formatter.

    The behaviour it guarantees is unchanged - the bot formats every branch and commits the
    result - but the step that does it lives in one place instead of three.
    """
    import json

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_file = os.path.join(repo_root, ".github", "workflows", "auto-format.yml")
    assert os.path.isfile(workflow_file), ".github/workflows/auto-format.yml must exist"

    with open(workflow_file, encoding="utf-8") as handle:
        content = handle.read()
    with open(os.path.join(repo_root, ".github", "darkfactory.json"), encoding="utf-8") as handle:
        ref = json.load(handle)["upstream"]["ref"]

    assert "push:" in content
    assert "contents: write" in content
    assert f"auto-format.yml@{ref}" in content, "the formatter must come from the pinned pipeline"


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
