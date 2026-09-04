import ast
import os
import subprocess
import pytest


def test_all_source_modules_have_google_docstrings():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(repo_root, "src")
    missing = []

    for root, _, files in os.walk(src_dir):
        for file in sorted(files):
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)

                mod_doc = ast.get_docstring(tree)
                if not mod_doc:
                    missing.append(f"{path}: missing module docstring")

                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        class_doc = ast.get_docstring(node)
                        if not class_doc:
                            missing.append(f"{path} Class {node.name}: missing class docstring")
                        for sub in node.body:
                            if isinstance(sub, ast.FunctionDef):
                                if not sub.name.startswith("_") or sub.name == "__init__":
                                    func_doc = ast.get_docstring(sub)
                                    if not func_doc:
                                        missing.append(
                                            f"{path} Class {node.name}.{sub.name}: missing docstring"
                                        )
                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith("_"):
                            func_doc = ast.get_docstring(node)
                            if not func_doc:
                                missing.append(f"{path} Function {node.name}: missing docstring")

    assert not missing, f"Missing docstrings found:\n" + "\n".join(missing)


def test_all_docs_use_mkdocstrings_directives():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(repo_root, "docs")
    missing_directives = []

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".md") and file != "INDEX.md":
                doc_path = os.path.join(root, file)
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if ":::" not in content:
                    missing_directives.append(file)

    assert (
        not missing_directives
    ), f"The following docs files are missing mkdocstrings ':::' directives: {missing_directives}"


def test_mkdocs_config_and_strict_build():
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mkdocs_yml = os.path.join(repo_root, "mkdocs.yml")
    assert os.path.isfile(mkdocs_yml), "mkdocs.yml must exist at repository root"

    cmd = [sys.executable, "-m", "mkdocs", "build", "--strict"]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert (
        result.returncode == 0
    ), f"mkdocs build --strict failed with code {result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_deploy_docs_workflow_exists():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow_path = os.path.join(repo_root, ".github", "workflows", "deploy-docs.yml")

    assert os.path.isfile(workflow_path), "deploy-docs.yml workflow must exist"
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()

    assert "Deploy Documentation" in content
    assert "mkdocs build --strict" in content
    assert "upload-pages-artifact" in content
    assert "deploy-pages" in content


def test_agents_rule_mandates_google_docstrings_and_mkdocs():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as f:
        content = f.read()

    assert "Google-style" in content or "Google-Style" in content
    assert "mkdocs build --strict" in content
    assert "GitHub Pages" in content
