"""Dynamic MkDocs hook for generating virtual documentation pages from Python docstrings."""

from collections.abc import MutableMapping
import os
import shutil
from typing import Any, List, Optional, Tuple
from mkdocs.structure.files import File, Files


def _get_repo_root(config: MutableMapping[str, Any]) -> str:
    """Resolve repository root directory from MkDocs configuration.

    Args:
        config (MutableMapping[str, Any]): The MkDocs configuration object or dictionary.

    Returns:
        str: The absolute path to the repository root.
    """
    config_file_path = getattr(config, "config_file_path", None)
    if not config_file_path and isinstance(config, dict):
        config_file_path = config.get("config_file_path")
    if config_file_path:
        return os.path.dirname(os.path.abspath(config_file_path))

    docs_dir = (
        config.get("docs_dir") if hasattr(config, "get") else getattr(config, "docs_dir", None)
    )
    if docs_dir:
        return os.path.abspath(os.path.join(docs_dir, ".."))

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_notes_dir(config: MutableMapping[str, Any]) -> str:
    """Resolve notes directory from MkDocs configuration or fallback.

    Args:
        config (MutableMapping[str, Any]): The MkDocs configuration object or dictionary.

    Returns:
        str: The path to the notes directory.
    """
    repo_root = _get_repo_root(config)
    notes_dir = os.path.join(repo_root, "notes")
    if not os.path.isdir(notes_dir) and os.path.isdir("notes"):
        notes_dir = os.path.abspath("notes")
    return notes_dir


def on_config(config: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Inspect notes directory and dynamically populate the Notes navigation section.

    Args:
        config (MutableMapping[str, Any]): The MkDocs configuration dictionary.

    Returns:
        MutableMapping[str, Any]: The updated MkDocs configuration dictionary with notes navigation.
    """
    notes_dir = _get_notes_dir(config)
    if not os.path.isdir(notes_dir):
        return config

    if "nav" not in config or config["nav"] is None:
        config["nav"] = []

    notes_section: Optional[List[Any]] = None
    for item in config["nav"]:
        if isinstance(item, dict) and "Notes" in item:
            if not isinstance(item["Notes"], list):
                item["Notes"] = []
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

    for f in sorted(os.listdir(notes_dir)):
        note_path = os.path.join(notes_dir, f)
        if (
            f.endswith(".md")
            and f != "index.md"
            and not f.startswith(".")
            and os.path.isfile(note_path)
        ):
            note_uri = f"notes/{f}"
            if not _is_present(note_uri):
                notes_section.append(note_uri)

    return config


def on_files(files: Files, config: MutableMapping[str, Any]) -> Files:
    """Dynamically generate virtual markdown documentation pages for Python modules and notes.

    Args:
        files (Files): The MkDocs collection of File objects.
        config (MutableMapping[str, Any]): The MkDocs configuration dictionary.

    Returns:
        Files: The updated collection of File objects including virtual documentation.
    """
    if hasattr(config, "plugins") and not hasattr(config.plugins, "_current_plugin"):
        config.plugins._current_plugin = None

    repo_root = _get_repo_root(config)
    notes_dir = _get_notes_dir(config)

    note_entries: List[Tuple[str, str, str]] = []
    if os.path.isdir(notes_dir):
        for f in sorted(os.listdir(notes_dir)):
            if f.endswith(".md") and f != "index.md" and not f.startswith("."):
                note_path = os.path.join(notes_dir, f)
                if os.path.isfile(note_path):
                    with open(note_path, "r", encoding="utf-8") as nf:
                        content = nf.read()
                    title = os.path.splitext(f)[0].replace("_", " ").title()
                    note_entries.append((f, title, content))

                    doc_uri = f"notes/{f}"
                    if not files.get_file_from_path(doc_uri):
                        gen_file = File.generated(
                            config,
                            doc_uri,
                            content=content,
                        )
                        files.append(gen_file)

    # Dynamically generate virtual notes/index.md hub page if not present
    notes_disk_index = os.path.join(notes_dir, "index.md")
    if not files.get_file_from_path("notes/index.md"):
        if os.path.isfile(notes_disk_index):
            with open(notes_disk_index, "r", encoding="utf-8") as f:
                notes_hub_content = f.read()
        else:
            hub_lines = [
                "# Architecture & Design Notes",
                "",
                "Authoritative architectural references, design decisions, and baseline rules for the ChessWithQuests project.",
                "",
                "## Table of Contents",
                "",
            ]
            for f, title, _ in note_entries:
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
            with open(readme_path, "r", encoding="utf-8") as rf:
                overview_content = rf.read()
        else:
            overview_content = "# ChessWithQuests\n\nAutogenerated API Documentation.\n"

        overview_content += "\n\n---\n\n## Reference Architecture Diagram\n- [Architecture Diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)\n"

        overview_content += (
            "\n\n---\n\n## Architecture & Reference Notes\n- [Notes Overview](notes/index.md)\n"
        )
        for f, title, _ in note_entries:
            overview_content += f"- [{title}](notes/{f})\n"

        index_file = File.generated(
            config,
            "index.md",
            content=overview_content,
        )
        files.append(index_file)

    src_dir = config["docs_dir"]
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


def on_post_build(config: MutableMapping[str, Any]) -> None:
    """Ensure site/index.html is available.

    Args:
        config (MutableMapping[str, Any]): The MkDocs configuration dictionary.

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
