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
    """Verify that dynamic docs hook generates mkdocstrings ':::' directives for source modules."""
    import mkdocs.config
    from mkdocs.structure.files import get_files
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(repo_root, ".github", "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import mkdocs_hooks

    cfg = mkdocs.config.load_config(os.path.join(repo_root, "mkdocs.yml"))
    files = get_files(cfg)
    files = mkdocs_hooks.on_files(files, cfg)

    generated_files = [f for f in files if getattr(f, "_content", None)]
    assert (
        len(generated_files) >= 25
    ), f"Expected dynamic files generated, found {len(generated_files)}"
    for f in generated_files:
        if f.src_uri != "index.md":
            assert ":::" in f._content, f"Generated file {f.src_uri} missing ':::' directive"


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
