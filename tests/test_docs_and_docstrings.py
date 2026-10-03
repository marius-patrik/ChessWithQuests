import ast
import importlib.util
import json
import os
import re
import subprocess
import sys

import properdocs.config
import pytest
from properdocs.structure.files import Files

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
package_roots = ("src/model", "src/controller", "src/view", "src/games")

hook_path = os.path.join(repo_root, ".github", "scripts", "docs_hooks.py")
spec = importlib.util.spec_from_file_location("docs_hooks", hook_path)
docs_hooks = importlib.util.module_from_spec(spec)
sys.modules["docs_hooks"] = docs_hooks
spec.loader.exec_module(docs_hooks)


def _source_modules():
    """Yield the path of every Python module under the src/ package roots."""
    for root in package_roots:
        base = os.path.join(repo_root, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def _dotted_module(path):
    """Return the importable dotted name for a module below src/."""
    relative = os.path.relpath(path, os.path.join(repo_root, "src"))
    dotted = relative[: -len(".py")].replace(os.sep, ".")
    if dotted.endswith(".__init__"):
        return dotted[: -len(".__init__")]
    return dotted


def _nav_labels(fragment):
    """Yield every navigation label, at any depth."""
    for item in fragment:
        if isinstance(item, dict):
            for label, value in item.items():
                yield label
                if isinstance(value, list):
                    yield from _nav_labels(value)


def _nav_targets(fragment):
    """Yield every navigation target path, at any depth."""
    targets = []

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for nested in value.values():
                walk(nested)
        elif isinstance(value, str):
            targets.append(value)

    walk(fragment)
    return targets


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
        dotted = _dotted_module(path)
        if dotted not in directives:
            missing.append(dotted)

    assert not missing, f"Modules without a generated page: {missing}"


def test_navigation_and_pages_cannot_drift():
    """Every navigation target must resolve to a page, and every page must be in the nav.

    This is the invariant `--strict` would otherwise fail the build over: a navigation
    entry pointing at a deleted module is a warning, and warnings are errors.
    """
    nav, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})
    documented = {doc_path for doc_path, _, _ in pages}
    targets = _nav_targets(nav)

    dangling = [target for target in targets if target not in documented]
    assert not dangling, f"Navigation entries without a generated page: {dangling}"

    unlisted = sorted(documented - set(targets))
    assert not unlisted, f"Generated pages missing from the navigation: {unlisted}"


def test_module_pages_emit_mkdocstrings_directives():
    _, pages = docs_hooks.build_nav({"docs_dir": os.path.join(repo_root, ".docs")})

    for doc_path, _, body in pages:
        if doc_path.startswith("notes/") or doc_path == "index.md":
            continue
        assert ":::" in body, f"Generated page {doc_path} carries no mkdocstrings directive"


def test_renaming_a_module_needs_no_configuration_edit(tmp_path):
    """A module discovered only in the hook's tree must appear without a nav edit."""
    package = tmp_path / "src" / "model" / "widget"
    package.mkdir(parents=True)
    (tmp_path / "src" / "model" / "__init__.py").write_text(
        '"""Model layer."""\n', encoding="utf-8"
    )
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


def test_every_note_is_published_verbatim_and_linked_from_a_hub(tmp_path):
    """Each Markdown file in a notes directory becomes a page carrying its bytes.

    Driven from a fixture the test owns, so it asserts what the hook does rather than
    what this repository happens to have written in `notes/`.
    """
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "chess_rules.md").write_text("# Chess\n\nRank one is White's.\n", encoding="utf-8")
    (notes_dir / "object_model.md").write_text(
        "# Object Model\n\nDeviations live here.\n", encoding="utf-8"
    )
    (tmp_path / "properdocs.yml").write_text("site_name: t\n", encoding="utf-8")

    _, pages = docs_hooks.build_nav(
        {"config_file_path": str(tmp_path / "properdocs.yml"), "docs_dir": str(tmp_path / ".docs")}
    )
    by_path = {doc_path: body for doc_path, _, body in pages}

    assert by_path["notes/chess_rules.md"] == "# Chess\n\nRank one is White's.\n"
    assert by_path["notes/object_model.md"] == "# Object Model\n\nDeviations live here.\n"

    hub = by_path["notes/index.md"]
    assert hub.startswith("# Architecture & Design Notes")
    assert "- [Chess Rules](chess_rules.md)" in hub
    assert "- [Object Model](object_model.md)" in hub


def test_a_notes_index_supplied_by_hand_replaces_the_generated_hub(tmp_path):
    """A stored `notes/index.md` wins over the generated hub, and is published verbatim."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "chess_rules.md").write_text("# Chess\n", encoding="utf-8")
    (notes_dir / "index.md").write_text("# My Notes\n\nHand written.\n", encoding="utf-8")
    (tmp_path / "properdocs.yml").write_text("site_name: t\n", encoding="utf-8")

    _, pages = docs_hooks.build_nav(
        {"config_file_path": str(tmp_path / "properdocs.yml"), "docs_dir": str(tmp_path / ".docs")}
    )
    by_path = {doc_path: body for doc_path, _, body in pages}

    # The hook joins the stored index and terminates it, so a hand-written hub gains a
    # trailing newline it did not have. Harmless for Markdown, and pinned so a change to it
    # is deliberate.
    assert by_path["notes/index.md"] == "# My Notes\n\nHand written.\n\n"
    assert "notes/chess_rules.md" in by_path


def test_existing_notes_index_is_preserved_exactly(tmp_path):
    """An on-disk notes hub must be published verbatim, not normalized."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    custom_content = "# Real Hub Page On Disk\n\nThis is a hand-written index.md page."
    (notes_dir / "index.md").write_text(custom_content, encoding="utf-8")
    (notes_dir / "sample.md").write_text("# Sample Note\nContent here.", encoding="utf-8")
    docs_dir = tmp_path / ".docs"
    docs_dir.mkdir()

    _, pages = docs_hooks.build_nav({"docs_dir": str(docs_dir), "notes_dir": str(notes_dir)})
    by_path = {doc_path: body for doc_path, _, body in pages}

    assert by_path["notes/index.md"] == custom_content


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


def test_empty_notes_directory_publishes_no_notes_section(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    docs_dir = tmp_path / ".docs"
    docs_dir.mkdir()

    nav, pages = docs_hooks.build_nav({"docs_dir": str(docs_dir), "notes_dir": str(notes_dir)})

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


def test_pymdown_extensions_is_capped_below_the_highlight_break():
    """The pinned highlighter must match what the docs build needs.

    `pymdown-extensions` 12.2 makes `Highlight.__init__` require an `md` argument the
    extension never passes, so every build fails with "Highlight.__init__() missing 1
    required positional argument: 'md'". An unbounded requirement resolves 12.2 on CI and
    12.1 on a developer machine, which is how the break reaches production unnoticed. The
    cap in `requirements-dev.txt` is what keeps the two in step, so it is asserted here
    rather than left to review.
    """
    requirements = os.path.join(repo_root, "requirements-dev.txt")
    with open(requirements, encoding="utf-8") as handle:
        content = handle.read()

    requirement = next(
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("pymdown-extensions")
    )
    assert (
        "<12.2" in requirement
    ), f"pymdown-extensions must stay below 12.2, which breaks the docs build; found: {requirement}"

    from pymdownx.highlight import Highlight

    try:
        Highlight()
    except TypeError as error:
        pytest.fail(f"the installed pymdown-extensions is incompatible with this build: {error}")


def test_deploy_docs_workflow_exists():
    workflow_path = os.path.join(repo_root, ".github", "workflows", "deploy-docs.yml")

    assert os.path.isfile(workflow_path), "deploy-docs.yml workflow must exist"
    with open(workflow_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Deploy Documentation" in content

    # The deploy is a caller now: the build command, the theme and the version manifest all come
    # from the pinned pipeline, so this file names a pin rather than a build.
    with open(os.path.join(repo_root, ".github", "darkfactory.json"), encoding="utf-8") as handle:
        pinned = json.load(handle)["upstream"]
    assert f"deploy-docs.yml@{pinned['ref']}" in content, "the deploy must call the pinned pipeline"
    assert re.findall(r"[0-9a-f]{40}", content) == [pinned["ref"], pinned["ref"]]
    assert (
        "concurrency:" not in content
    ), "a caller naming the callee's concurrency group deadlocks the run it calls"


def test_agents_rule_mandates_google_docstrings_and_a_strict_docs_build():
    agents_file = os.path.join(repo_root, "AGENTS.md")

    with open(agents_file, encoding="utf-8") as handle:
        content = handle.read()

    assert "Google-style" in content or "Google-Style" in content
    assert "build --strict" in content, "the rule must mandate a zero-warning documentation build"
    assert "GitHub Pages" in content
