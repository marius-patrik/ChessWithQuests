"""Documentation hooks that generate the entire site tree from the repository layout.

Nothing about the documentation is stored. ``properdocs.yml`` points ``docs_dir`` at a
placeholder child directory and every page - the overview, the architecture notes and one
page per Python module - is emitted here as a virtual file.

The navigation is built by the same walk that emits the pages, so the two cannot drift:
adding, renaming or deleting a module needs no configuration edit, and a navigation entry
can never point at a page that does not exist. That is what `--strict` would otherwise
turn into a build failure.
"""

import os
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

from properdocs.structure.files import File, Files

#: Repository directories that hold importable Python, in navigation order.
SOURCE_ROOTS: Tuple[str, ...] = ("model", "controller", "view", "games")

#: Navigation section label for each source root.
SECTION_LABELS: Dict[str, str] = {
    "model": "Model",
    "controller": "Controllers",
    "view": "View",
    "games": "Games",
}

#: A generated page: its documentation path, its navigation label and its Markdown body.
Page = Tuple[str, str, str]


def _get_repo_root(config: Any) -> str:
    """Resolve the repository root directory from configuration.

    Args:
        config: The documentation configuration object or dictionary.

    Returns:
        Absolute path to the repository root directory.
    """
    config_file = (
        config.get("config_file_path")
        if hasattr(config, "get")
        else getattr(config, "config_file_path", None)
    )
    if config_file:
        return os.path.dirname(os.path.abspath(config_file))

    docs_dir = (
        config.get("docs_dir") if hasattr(config, "get") else getattr(config, "docs_dir", None)
    )
    if docs_dir:
        return os.path.dirname(os.path.abspath(docs_dir))

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_notes_dir(config: Any) -> Optional[str]:
    """Resolve the notes directory from configuration.

    Args:
        config: The documentation configuration object or dictionary.

    Returns:
        Absolute path to the notes directory, or None when it does not exist.
    """
    custom = (
        config.get("notes_dir") if hasattr(config, "get") else getattr(config, "notes_dir", None)
    )
    if custom and os.path.isdir(custom):
        return os.path.abspath(custom)

    notes_dir = os.path.join(_get_repo_root(config), "notes")
    return notes_dir if os.path.isdir(notes_dir) else None


def _module_pages(repo_root: str) -> List[Page]:
    """Build one page per Python module found under the source roots.

    A package directory yields an ``index.md`` for its ``__init__.py``; every other module
    yields a page named after it. The dotted path is what ``mkdocstrings`` resolves, so it
    is derived from the directory layout rather than declared anywhere.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        List of (doc_path, nav_label, markdown_body) triples, sorted by doc_path.
    """
    pages: List[Page] = []
    for root_name in SOURCE_ROOTS:
        base = os.path.join(repo_root, root_name)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            rel_dir = os.path.relpath(dirpath, repo_root)
            parts: List[str] = [] if rel_dir == os.curdir else rel_dir.split(os.sep)

            if "__init__.py" in filenames:
                dotted = ".".join(parts)
                doc_path = "/".join(parts + ["index.md"])
                label = f"{parts[-1]} package ({dotted})"
                pages.append(
                    (doc_path, label, f"# {parts[-1].capitalize()} package\n\n::: {dotted}\n")
                )

            for name in sorted(filenames):
                if not name.endswith(".py") or name == "__init__.py":
                    continue
                dotted = ".".join(parts + [name[:-3]])
                doc_path = "/".join(parts + [name[:-3] + ".md"])
                label = f"{name[:-3]} ({dotted})"
                pages.append((doc_path, label, f"# {name[:-3].capitalize()}\n\n::: {dotted}\n"))
    return sorted(pages, key=lambda page: page[0])


def _note_pages(notes_dir: Optional[str]) -> List[Page]:
    """Build one page per Markdown file in the notes directory.

    Args:
        notes_dir: Absolute path to the notes directory, or None when absent.

    Returns:
        List of (doc_path, nav_label, markdown_body) triples.
    """
    if not notes_dir or not os.path.isdir(notes_dir):
        return []

    pages: List[Page] = []
    hub_content = ["# Architecture & Design Notes", ""]
    for name in sorted(os.listdir(notes_dir)):
        if not name.endswith(".md") or name == "index.md":
            continue
        path = os.path.join(notes_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            print(f"Warning: Failed to read note {path}: {error}")
            continue
        title = os.path.splitext(name)[0].replace("_", " ").title()
        pages.append((f"notes/{name}", title, content))
        hub_content.append(f"- [{title}]({name})")

    index_path = os.path.join(notes_dir, "index.md")
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as handle:
                hub_content = [handle.read()]
        except (OSError, UnicodeDecodeError) as error:
            print(f"Warning: Failed to read notes index {index_path}: {error}")

    if len(hub_content) > 1 or pages:
        pages.append(("notes/index.md", "Overview", "\n".join(hub_content) + "\n"))
    return pages


def _overview_page(repo_root: str, note_pages: List[Page]) -> Page:
    """Build the site overview from the README, with links to the notes appended.

    Args:
        repo_root: Absolute path to the repository root.
        note_pages: The generated note pages, linked from the overview.

    Returns:
        The (doc_path, nav_label, markdown_body) triple for the overview.
    """
    readme_path = os.path.join(repo_root, "README.md")
    body = ""
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as handle:
                body = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            print(f"Warning: Failed to read README {readme_path}: {error}")
    if not body:
        body = "# ChessWithQuests\n"

    body += "\n---\n\n## Reference Architecture Diagram\n"
    body += (
        "- [Architecture Diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8"
        "#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)\n"
    )
    if note_pages:
        body += "\n## Architecture & Reference Notes\n"
        body += "- [Notes Overview](notes/index.md)\n"
        for doc_path, label, _ in note_pages:
            if doc_path == "notes/index.md":
                continue
            body += f"- [{label}]({doc_path})\n"
    return ("index.md", "Overview", body)


def _nest(pages: List[Page]) -> Dict[str, Any]:
    """Group pages into a directory tree keyed by path segment.

    A segment maps to a page path when it is a leaf and to a nested dictionary otherwise,
    so ``model/game/board.md`` becomes ``{"model": {"game": {"board.md": ...}}}``.

    Args:
        pages: The generated pages.

    Returns:
        Nested dictionary mirroring the documentation directory layout.
    """
    tree: Dict[str, Any] = {}
    for doc_path, label, _ in pages:
        segments = doc_path[: -len(".md")].split("/")
        node = tree
        for segment in segments[:-1]:
            child = node.setdefault(segment, {})
            if not isinstance(child, dict):
                child = {}
                node[segment] = child
            node = child
        node[segments[-1]] = (doc_path, label)
    return tree


def _order_key(item: Tuple[str, Any]) -> Tuple[int, str]:
    """Sort a navigation segment so package overviews precede their modules.

    Args:
        item: The (segment, value) pair being sorted.

    Returns:
        A sort key placing ``index`` first and everything else alphabetically.
    """
    return (0 if item[0] == "index" else 1, item[0])


def _render(node: Dict[str, Any], labels: Optional[Dict[str, str]] = None) -> List[Any]:
    """Render a nested page tree as a properdocs navigation.

    Args:
        node: The nested page tree for one section.
        labels: Optional segment-to-label overrides, used for the top-level sections.

    Returns:
        A navigation fragment.
    """
    rendered: List[Any] = []
    for segment, value in sorted(node.items(), key=_order_key):
        label = (labels or {}).get(segment, segment)
        if isinstance(value, dict):
            rendered.append({label: _render(value)})
        else:
            doc_path, entry_label = value
            rendered.append({entry_label: doc_path})
    return rendered


def build_nav(config: Any) -> Tuple[List[Any], List[Page]]:
    """Build the complete navigation and the pages it refers to.

    Args:
        config: The documentation configuration object or dictionary.

    Returns:
        A (navigation, pages) pair. Every page in ``pages`` has exactly one navigation
        entry and every navigation entry has exactly one page.
    """
    repo_root = _get_repo_root(config)
    module_pages = _module_pages(repo_root)
    note_pages = _note_pages(_get_notes_dir(config))
    overview = _overview_page(repo_root, note_pages)

    nav: List[Any] = [{"Overview": overview[0]}]

    per_root: Dict[str, List[Page]] = {}
    for doc_path, label, body in module_pages:
        per_root.setdefault(doc_path.split("/")[0], []).append((doc_path, label, body))
    for root_name in SOURCE_ROOTS:
        pages = per_root.get(root_name)
        if pages:
            nav.append({SECTION_LABELS[root_name]: _render(_nest(pages))})

    if note_pages:
        nav.append({"Notes": _render(_nest(note_pages))})

    return nav, [overview] + module_pages + note_pages


def on_config(config: Any) -> Any:
    """Replace the configured navigation with one generated from the repository layout.

    Args:
        config: The documentation configuration object or dictionary.

    Returns:
        The configuration, with ``nav`` set to the generated navigation.
    """
    nav, _ = build_nav(config)
    config["nav"] = nav
    return config


def on_files(files: Files, config: Any) -> Files:
    """Emit every documentation page as a virtual file.

    Args:
        files: The collection of files properdocs discovered in ``docs_dir``.
        config: The documentation configuration object or dictionary.

    Returns:
        The collection of files including every generated page.
    """
    plugins = getattr(config, "plugins", None)
    if plugins is not None and not hasattr(plugins, "_current_plugin"):
        # `File.generated` stamps the file with the plugin that produced it. A bare
        # configuration object built outside a plugin run has no such attribute.
        plugins._current_plugin = None

    _, pages = build_nav(config)
    for doc_path, _, body in pages:
        if files.get_file_from_path(doc_path) is None:
            files.append(File.generated(config, doc_path, content=body))
    return files


def on_post_build(config: Any) -> None:
    """Ensure the site root holds an ``index.html``.

    Args:
        config: The documentation configuration object or dictionary.

    Returns:
        None
    """
    site_dir = (
        config.get("site_dir") if hasattr(config, "get") else getattr(config, "site_dir", None)
    ) or os.path.join(_get_repo_root(config), "site")

    index_html = os.path.join(site_dir, "index.html")
    if not os.path.exists(index_html):
        for candidate in ("index.html", "__init__/index.html"):
            source = os.path.join(site_dir, candidate)
            if os.path.exists(source):
                shutil.copyfile(source, index_html)
                print(f"Generated site/index.html from {candidate}")
                break
