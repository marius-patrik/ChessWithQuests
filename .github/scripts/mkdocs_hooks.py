"""Dynamic MkDocs hook for generating virtual documentation pages from Python docstrings."""

import os
import shutil
from typing import Any, List, Optional, Tuple
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files


def _get_repo_root(config: Any) -> str:
    """Resolve the repository root directory from configuration.

    Args:
        config (Any): The MkDocs configuration object or dictionary.

    Returns:
        str: Absolute path to the repository root directory.
    """
    docs_dir = (
        config.get("docs_dir") if hasattr(config, "get") else getattr(config, "docs_dir", None)
    )
    if docs_dir:
        return os.path.abspath(os.path.join(docs_dir, ".."))
    elif hasattr(config, "config_file_path") and config.config_file_path:
        return os.path.dirname(os.path.abspath(config.config_file_path))
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_notes_dir(config: Any) -> Optional[str]:
    """Resolve the notes directory from configuration if present.

    Args:
        config (Any): The MkDocs configuration object or dictionary.

    Returns:
        Optional[str]: Absolute path to the notes directory if it exists, None otherwise.
    """
    docs_dir = (
        config.get("docs_dir") if hasattr(config, "get") else getattr(config, "docs_dir", None)
    )
    if docs_dir:
        repo_root = os.path.abspath(os.path.join(docs_dir, ".."))
    elif hasattr(config, "config_file_path") and config.config_file_path:
        repo_root = os.path.dirname(os.path.abspath(config.config_file_path))
    else:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    notes_dir = os.path.join(repo_root, "notes")
    if not os.path.isdir(notes_dir) and os.path.isdir("notes"):
        notes_dir = os.path.abspath("notes")
    return notes_dir if os.path.isdir(notes_dir) else None


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Inspect notes directory and dynamically populate the Notes navigation section.

    Args:
        config (MkDocsConfig): The MkDocs configuration object.

    Returns:
        MkDocsConfig: The updated MkDocs configuration object with notes navigation.
    """
    notes_dir = _get_notes_dir(config)
    if not notes_dir:
        return config

    note_files = [
        f
        for f in sorted(os.listdir(notes_dir))
        if f.endswith(".md") and f != "index.md" and os.path.isfile(os.path.join(notes_dir, f))
    ]
    notes_index_path = os.path.join(notes_dir, "index.md")
    has_notes = bool(note_files or os.path.isfile(notes_index_path))

    if not has_notes:
        return config

    if "nav" not in config or config["nav"] is None:
        config["nav"] = []

    notes_section: Optional[List[Any]] = None
    for item in config["nav"]:
        if isinstance(item, dict) and "Notes" in item:
            if item["Notes"] is None:
                item["Notes"] = []
            elif not isinstance(item["Notes"], list):
                item["Notes"] = [item["Notes"]]
            notes_section = item["Notes"]
            break

    if notes_section is None:
        notes_section = []
        config["nav"].append({"Notes": notes_section})

    def _is_present(target_path: str) -> bool:
        for entry in notes_section:
            if entry == target_path:
                return True
            if isinstance(entry, dict) and target_path in entry.values():
                return True
        return False

    if not _is_present("notes/index.md"):
        notes_section.insert(0, "notes/index.md")

    for f in note_files:
        note_uri = f"notes/{f}"
        if not _is_present(note_uri):
            notes_section.append(note_uri)

    return config


def on_files(files: Files, config: MkDocsConfig) -> Files:
    """Dynamically generate virtual markdown documentation pages for Python modules and notes.

    Args:
        files (Files): The MkDocs collection of File objects.
        config (MkDocsConfig): The MkDocs configuration object.

    Returns:
        Files: The updated collection of File objects including virtual documentation.
    """
    plugins = getattr(config, "plugins", None)
    if plugins is not None and not hasattr(plugins, "_current_plugin"):
        try:
            plugins._current_plugin = None
        except AttributeError:
            pass

    src_dir = config["docs_dir"]
    repo_root = _get_repo_root(config)
    notes_dir = _get_notes_dir(config)

    note_entries: List[Tuple[str, str]] = []
    if notes_dir and os.path.isdir(notes_dir):
        for f in sorted(os.listdir(notes_dir)):
            if f.endswith(".md") and f != "index.md":
                note_path = os.path.join(notes_dir, f)
                if os.path.isfile(note_path):
                    try:
                        with open(note_path, "r", encoding="utf-8", errors="replace") as nf:
                            content = nf.read()
                    except OSError as e:
                        print(f"Warning: Failed to read note {note_path}: {e}")
                        continue

                    title = os.path.splitext(f)[0].replace("_", " ").title()
                    note_entries.append((f, title))

                    doc_uri = f"notes/{f}"
                    if not files.get_file_from_path(doc_uri):
                        gen_file = File.generated(
                            config,
                            doc_uri,
                            content=content,
                        )
                        files.append(gen_file)

    # Dynamically generate virtual notes/index.md hub page if notes directory exists and has notes or index.md
    if notes_dir and os.path.isdir(notes_dir):
        notes_index_path = os.path.join(notes_dir, "index.md")
        has_index_on_disk = os.path.isfile(notes_index_path)
        if note_entries or has_index_on_disk:
            if not files.get_file_from_path("notes/index.md"):
                if has_index_on_disk:
                    try:
                        with open(notes_index_path, "r", encoding="utf-8", errors="replace") as f:
                            notes_hub_content = f.read()
                    except OSError as e:
                        print(f"Warning: Failed to read notes index {notes_index_path}: {e}")
                        notes_hub_content = ""
                else:
                    hub_lines = [
                        "# Architecture & Design Notes",
                        "",
                        "Authoritative architectural references, design decisions, and baseline rules for the ChessWithQuests project.",
                        "",
                        "## Table of Contents",
                        "",
                    ]
                    for f, title in note_entries:
                        hub_lines.append(f"- [{title}]({f})")
                    hub_lines.append("")
                    notes_hub_content = "\n".join(hub_lines)

                notes_index_file = File.generated(
                    config,
                    "notes/index.md",
                    content=notes_hub_content,
                )
                files.append(notes_index_file)

    # Generate virtual index.md overview from README.md if no index.md on disk
    if not files.get_file_from_path("index.md"):
        readme_path = os.path.join(repo_root, "README.md")
        overview_content = ""
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="replace") as rf:
                    overview_content = rf.read()
            except OSError as e:
                print(f"Warning: Failed to read README {readme_path}: {e}")
                overview_content = "# ChessWithQuests\n\nAutogenerated API Documentation.\n"
        else:
            overview_content = "# ChessWithQuests\n\nAutogenerated API Documentation.\n"

        overview_content += "\n\n---\n\n## Reference Architecture Diagram\n- [Architecture Diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)\n"

        if (
            notes_dir
            and os.path.isdir(notes_dir)
            and (note_entries or os.path.isfile(os.path.join(notes_dir, "index.md")))
        ):
            overview_content += (
                "\n\n---\n\n## Architecture & Reference Notes\n- [Notes Overview](notes/index.md)\n"
            )
            for f, title in note_entries:
                overview_content += f"- [{title}](notes/{f})\n"

        index_file = File.generated(
            config,
            "index.md",
            content=overview_content,
        )
        files.append(index_file)

    for root, _, filenames in os.walk(src_dir):
        for f in sorted(filenames):
            if not f.endswith(".py"):
                continue

            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, src_dir)
            parts = rel_path.split(os.sep)
            parts[-1] = os.path.splitext(parts[-1])[0]

            if parts[-1] == "__init__":
                if len(parts) == 1:
                    # Root package overview is covered by docs/index.md
                    continue
                dotted_path = ".".join(parts[:-1])
                doc_uri = "/".join(parts[:-1]) + "/index.md"
                title = f"{parts[-2].capitalize()} Package (`{dotted_path}`)"
            else:
                dotted_path = ".".join(parts)
                doc_uri = "/".join(parts) + ".md"
                title = f"{parts[-1].capitalize()} (`{dotted_path}`)"

            # Avoid collisions with static docs if already present
            if files.get_file_from_path(doc_uri):
                continue

            content = f"# {title}\n\n::: {dotted_path}\n"
            gen_file = File.generated(
                config,
                doc_uri,
                content=content,
            )
            files.append(gen_file)

    return files


def on_post_build(config: MkDocsConfig) -> None:
    """Ensure site/index.html is available.

    Args:
        config (MkDocsConfig): The MkDocs configuration object.

    Returns:
        None
    """
    site_dir = config["site_dir"]
    index_html = os.path.join(site_dir, "index.html")
    if not os.path.exists(index_html):
        for candidate in ["index.html", "__init__/index.html", "src/index.html"]:
            src = os.path.join(site_dir, candidate)
            if os.path.exists(src):
                shutil.copyfile(src, index_html)
                print(f"Generated site/index.html from {candidate}")
                break
