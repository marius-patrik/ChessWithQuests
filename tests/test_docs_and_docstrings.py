import ast
import importlib.util
import os
import subprocess
import sys

import properdocs.config
from properdocs.structure.files import Files, get_files

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
package_roots = ("model", "controller", "view", "games")

hook_path = os.path.join(repo_root, ".github", "scripts", "docs_hooks.py")
spec = importlib.util.spec_from_file_location("docs_hooks", hook_path)
docs_hooks = importlib.util.module_from_spec(spec)
sys.modules["docs_hooks"] = docs_hooks
spec.loader.exec_module(docs_hooks)


def _source_modules():
    """Yield the path of every Python module under the package roots."""
    for root in package_roots:
        base = os.path.join(repo_root, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def _nav_labels(fragment):
    """Yield every navigation label, at any depth."""
    for item in fragment:
        for label, value in item.items():
            yield label
            if isinstance(value, list):
                yield from _nav_labels(value)


def _load_config():
    config = properdocs.config.load_config(os.path.join(repo_root, "properdocs.yml"))
    return docs_hooks.on_config(config)


def test_all_source_modules_have_google_docstrings():
    missing = []

    for path in _source_modules():
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)

        if not ast.get_docstring(tree):
            missing.append(f"{path}: missing module docstring")

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    missing.append(f"{path} Class {node.name}: missing class docstring")
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and (
                        not sub.name.startswith("_") or sub.name == "__init__"
                    ):
                        if not ast.get_docstring(sub):
                            missing.append(
                                f"{path} Class {node.name}.{sub.name}: missing docstring"
                            )
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if not ast.get_docstring(node):
                    missing.append(f"{path} Function {node.name}: missing docstring")

    assert not missing, "Missing docstrings found:\n" + "\n".join(missing)


def test_every_source_module_gets_a_page():
    """Each module on disk must be reachable in the generated documentation."""
    _, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})
    directives = {body.rsplit("::: ", 1)[1].strip() for _, _, body in pages if ":::" in body}

    missing = []
    for path in _source_modules():
        dotted = os.path.relpath(path, repo_root)[: -len(".py")].replace(os.sep, ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        if dotted not in directives:
            missing.append(dotted)

    assert not missing, f"Modules without a generated page: {missing}"


def test_navigation_and_pages_cannot_drift():
    """Every navigation target must resolve to a page, and every page must be in the nav.

    This is the invariant `--strict` would otherwise fail the build over: a hand-written
    navigation entry pointing at a deleted module is a warning, and warnings are errors.
    """
    nav, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})
    documented = {doc_path for doc_path, _, _ in pages}

    targets = []

    def walk(fragment):
        for item in fragment:
            if isinstance(item, dict):
                for label, value in item.items():
                    if isinstance(value, list):
                        walk(value)
                    else:
                        targets.append((label, value))

    walk(nav)

    dangling = [target for _, target in targets if target not in documented]
    assert not dangling, f"Navigation entries without a generated page: {dangling}"

    unlisted = sorted(documented - {target for _, target in targets})
    assert not unlisted, f"Generated pages missing from the navigation: {unlisted}"


def test_module_pages_emit_mkdocstrings_directives():
    _, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})

    for doc_path, _, body in pages:
        if doc_path.startswith("notes/") or doc_path == "index.md":
            continue
        assert ":::" in body, f"Generated page {doc_path} carries no mkdocstrings directive"


def test_renaming_a_module_needs_no_configuration_edit(tmp_path):
    """A module discovered only in the hook's tree must appear without a nav edit."""
    package = tmp_path / "model" / "widget"
    package.mkdir(parents=True)
    (tmp_path / "model" / "__init__.py").write_text('"""Model layer."""\n', encoding="utf-8")
    (package / "__init__.py").write_text('"""Widgets."""\n', encoding="utf-8")
    (package / "sprocket.py").write_text('"""A sprocket."""\n', encoding="utf-8")

    docs_dir = tmp_path / ".docs"
    docs_dir.mkdir()

    nav, pages = docs_hooks.build_nav({"docs_dir": str(docs_dir)})
    documented = {doc_path for doc_path, _, _ in pages}

    assert "model/widget/sprocket.md" in documented
    assert "model/widget/index.md" in documented
    assert any("sprocket (model.widget.sprocket)" == label for label in _nav_labels(nav))


def test_on_files_appends_every_generated_page():
    config = _load_config()
    files = docs_hooks.on_files(Files([]), config)
    generated = {file.src_uri for file in files if getattr(file, "_content", None)}

    assert "index.md" in generated
    assert "model/game/board.md" in generated
    assert "notes/index.md" in generated
    assert docs_hooks.on_files(files, config) is files


def test_notes_are_published_with_a_hub_page():
    _, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})
    by_path = {doc_path: body for doc_path, _, body in pages}

    for name in sorted(os.listdir(os.path.join(repo_root, "notes"))):
        if not name.endswith(".md") or name == "index.md":
            continue
        doc_path = f"notes/{name}"
        assert doc_path in by_path
        with open(os.path.join(repo_root, "notes", name), encoding="utf-8") as handle:
            assert by_path[doc_path] == handle.read()

    hub = by_path["notes/index.md"]
    assert "# Architecture & Design Notes" in hub
    assert "chess_rules.md" in hub


def test_unreadable_note_is_skipped_without_failing_the_build(tmp_path, capsys):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "corrupted.md").write_bytes(b"\x80\x81\xff")
    (notes_dir / "readable.md").write_text("# Readable\n", encoding="utf-8")
    docs_dir = tmp_path / ".docs"
    docs_dir.mkdir()

    _, pages = docs_hooks.build_nav({"docs_dir": str(docs_dir), "notes_dir": str(notes_dir)})
    documented = {doc_path for doc_path, _, _ in pages}

    assert "notes/readable.md" in documented
    assert "notes/corrupted.md" not in documented
    assert "notes/index.md" in documented
    assert "Warning: Failed to read note" in capsys.readouterr().out


def test_absent_notes_directory_publishes_no_notes_section(tmp_path):
    docs_dir = tmp_path / ".docs"
    docs_dir.mkdir()

    nav, pages = docs_hooks.build_nav({"docs_dir": str(docs_dir)})

    assert not any(isinstance(item, dict) and "Notes" in item for item in nav)
    assert not any(doc_path.startswith("notes/") for doc_path, _, _ in pages)


def test_docs_config_and_strict_build():
    """The site must build with zero warnings, which is what `--strict` enforces."""
    config_path = os.path.join(repo_root, "properdocs.yml")
    assert os.path.isfile(config_path), "properdocs.yml must exist at repository root"

    result = subprocess.run(
        [sys.executable, "-m", "properdocs", "build", "--strict"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"properdocs build --strict failed with code {result.returncode}:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_generated_docs_directory_is_not_tracked():
    """`docs_dir` is a generated placeholder; nothing it produces may reach the index."""
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", ".docs/index.md"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "generated documentation pages must be git-ignored"
