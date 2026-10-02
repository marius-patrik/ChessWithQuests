import os
import subprocess
import sys

import pytest

import chesswithquests
from model.game.games import (
    DEFAULT_GAME,
    available_games,
    configuration_path,
    games_root,
)

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
python = sys.executable


def test_games_root_holds_the_shipped_configurations():
    """`games/` lives outside the package, so resolution is the one thing that can break
    an installed distribution silently: everything else would look fine while the default
    configuration was missing."""
    root = games_root()

    assert os.path.isdir(root), f"games directory not found at {root}"
    assert os.path.isdir(os.path.join(root, DEFAULT_GAME)), "the default configuration must ship"


def test_default_configuration_is_offered_first():
    games = available_games()

    assert DEFAULT_GAME in games
    assert games == [DEFAULT_GAME, *sorted(name for name in games if name != DEFAULT_GAME)]


def test_configuration_path_resolves_and_refuses_an_unknown_name():
    path = configuration_path(DEFAULT_GAME)

    assert os.path.isdir(path)
    assert os.path.basename(path) == DEFAULT_GAME

    with pytest.raises(FileNotFoundError):
        configuration_path("no-such-game")


def test_missing_games_directory_reports_no_configurations(tmp_path, monkeypatch):
    monkeypatch.setattr("model.game.games.os.path.isdir", lambda path: False)

    assert available_games() == []


def test_entry_point_reports_its_installation_without_a_display():
    """`--check` is what makes the whole startup path verifiable on a machine with no
    window server, so continuous integration exercises it rather than skipping it."""
    result = subprocess.run(
        [python, "-m", "chesswithquests", "--check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert games_root() in result.stdout
    assert DEFAULT_GAME in result.stdout


def test_entry_point_rejects_an_unknown_configuration():
    with pytest.raises(FileNotFoundError):
        configuration_path("no-such-game")

    result = subprocess.run(
        [python, "-m", "chesswithquests", "--game", "no-such-game"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 4, result.stdout
    assert "no-such-game" in result.stderr


def test_entry_point_builds_a_window():
    """The entry point's whole job is to open a window. Tk needs a display, so the test is
    skipped rather than weakened when there is none."""
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
    except tkinter.TclError as error:  # pragma: no cover - depends on the machine
        pytest.skip(f"no display available: {error}")

    try:
        window = chesswithquests.build_window(root, DEFAULT_GAME)
        assert window.winfo_exists() == 1
        assert DEFAULT_GAME in window.title()
        assert window.winfo_children()
    finally:
        root.destroy()


def test_no_third_party_runtime_import_under_the_project_source():
    """The runtime is the standard library plus tkinter, and nothing else.

    Asserted against the code itself rather than against packaging metadata, so the
    invariant survives being installed, vendored or simply run from the checkout.
    """
    import ast
    import sys

    project_roots = ("model", "controller", "view", "games", "chesswithquests")
    offenders = []

    for root in project_roots:
        base = os.path.join(repo_root, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "r", encoding="utf-8") as handle:
                    tree = ast.parse(handle.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported = [alias.name.split(".")[0] for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        if node.level or not node.module:
                            continue
                        imported = [node.module.split(".")[0]]
                    else:
                        continue
                    for top in imported:
                        if top not in sys.stdlib_module_names and top not in project_roots:
                            offenders.append(f"{os.path.relpath(path, repo_root)}: {top}")

    assert not offenders, f"third-party runtime imports found: {sorted(set(offenders))}"
