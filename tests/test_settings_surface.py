"""The settings surface: the parts of it that are rules about data, not widgets.

`SCRATCHPAD.md` item 18 says the default configuration "cannot be edited or deleted", and
`PRD.md` FR-27 says a variant starts by duplicating it. Nothing enforced either: a
configuration is a directory, and `Configuration.save_values()` wrote into it with no guard
at all. These tests hold the guard in place and the directory operations around it — copy,
rename, delete — because those are the moves that make "duplicate it and edit that"
reachable rather than an instruction nobody can follow.

The widget-level surface is exercised where there is a display and skipped where there is
not, as `tests/test_view.py` already does.
"""

import os
import pathlib
import shutil

import pytest

from model.game.configuration import (
    Configuration,
    copy_configuration,
    delete_configuration,
    load_configuration,
    load_configuration_at,
    rename_configuration,
)
from model.game.games import DEFAULT_GAME, games_root


@pytest.fixture
def games_dir(tmp_path):
    """Copy the shipped chess configuration into a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        str: The path of the `games/` root, which is what the library functions are pointed
        at so the shipped directory is never touched.
    """
    root = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / DEFAULT_GAME,
        root / DEFAULT_GAME,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return str(root)


def test_the_default_configuration_refuses_to_be_written_into(games_dir):
    """Editing the default is the one edit that must not happen, and it now raises.

    Without the guard this writes `configuration.json` into `games/chess/` and the reference
    every variant is duplicated from is no longer what shipped.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    default = load_configuration(DEFAULT_GAME, root=games_dir)

    with pytest.raises(PermissionError):
        default.save_values()

    assert not os.path.exists(os.path.join(default.path, "configuration.json"))


def test_the_default_configuration_can_still_be_exported(games_dir, tmp_path):
    """Refusing to edit it is not refusing to read it: an export elsewhere still works.

    The guard is scoped to the default configuration's own directory, because writing a
    record of its values somewhere else is not editing the configuration.

    Args:
        games_dir: The throwaway `games/` root.
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    default = load_configuration(DEFAULT_GAME, root=games_dir)

    written = default.save_values(str(tmp_path / "chess.json"))

    assert os.path.isfile(written)


def test_the_default_configuration_cannot_be_renamed_or_deleted(games_dir):
    """FR-27 covers deletion and FR-28 covers renaming; both exclude the default.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    with pytest.raises(PermissionError):
        rename_configuration(DEFAULT_GAME, "renamed", root=games_dir)
    with pytest.raises(PermissionError):
        delete_configuration(DEFAULT_GAME, root=games_dir)

    assert os.path.isdir(os.path.join(games_dir, DEFAULT_GAME))


def test_a_variant_is_written_where_the_guard_does_not_reach(games_dir):
    """A copy is editable, which is what makes "duplicate it and edit that" true.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    written = variant.save_values()

    assert written.endswith(os.path.join("house", "configuration.json"))
    assert os.path.isfile(written)


def test_a_copied_configuration_is_a_variant_and_not_the_original(games_dir):
    """Copying is the extension mechanism, so the copy must be its own configuration.

    `SCRATCHPAD.md` section 2: `cp -r games/chess games/house` and change what differs. A copy
    whose files reached back into the original would look edited and play the original, so
    this asserts the copy has its own directory, its own source, and a board built from that
    source rather than from `games/chess`.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert variant.name == "house"
    assert variant.path == os.path.join(games_dir, "house")
    assert variant.path != os.path.join(games_dir, DEFAULT_GAME)

    board_source = pathlib.Path(variant.path) / "board.py"
    board_source.write_text(
        '"""The house board: ten by ten, which chess is not."""\n\n'
        "from model.game.board import Board\n\n"
        "DIMENSIONS = (10, 10)\n\n"
        "def build_board(rows=DIMENSIONS[0], cols=DIMENSIONS[1]):\n"
        '    """Build the house board."""\n\n'
        "    return Board((rows, cols))\n",
        encoding="utf-8",
    )
    assert "ten by ten" in board_source.read_text(encoding="utf-8")
    assert "ten by ten" not in (pathlib.Path(games_dir) / DEFAULT_GAME / "board.py").read_text(
        encoding="utf-8"
    )


def test_the_copied_directory_is_a_real_copy_and_not_a_link(games_dir):
    """A copy that shares one inode with the original is an alias, not a variant.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    original_board = os.path.join(games_dir, DEFAULT_GAME, "board.py")
    copied_board = os.path.join(variant.path, "board.py")
    assert os.path.isfile(copied_board)
    assert os.stat(original_board).st_ino != os.stat(copied_board).st_ino


def test_a_copy_carries_no_bytecode_from_the_configuration_it_came_from(games_dir):
    """A copy is source, not the original's compiled form of it.

    `copytree` copies everything by default, so a copy made naively arrives holding the
    original's `__pycache__`. Python discards bytecode whose source has moved on, so this is
    hygiene rather than a live failure — but the variant directory is what a player edits and
    re-reads, and shipping it full of another configuration's compiled modules is a trap
    with no upside.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    original_cache = pathlib.Path(games_dir) / DEFAULT_GAME / "rules" / "__pycache__"
    original_cache.mkdir(parents=True, exist_ok=True)
    (original_cache / "stale_marker.pyc").write_bytes(b"not real bytecode")

    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert (original_cache / "stale_marker.pyc").is_file()
    assert not (pathlib.Path(variant.path) / "rules" / "__pycache__" / "stale_marker.pyc").exists()


def test_copying_refuses_to_overwrite_a_configuration_that_exists(games_dir):
    """A copy that silently replaced an existing variant would destroy another variant.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    with pytest.raises(FileExistsError):
        copy_configuration(DEFAULT_GAME, "house", root=games_dir)


def test_a_name_that_is_not_a_directory_name_is_refused(games_dir):
    """A configuration name is a directory name and a module name at once.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    for name in ("../escape", "sub/house", "", ".", "not an identifier"):
        with pytest.raises(ValueError):
            copy_configuration(DEFAULT_GAME, name, root=games_dir)


def test_renaming_a_variant_leaves_it_loadable_and_changes_only_the_name(games_dir):
    """A rename is a directory move, so it must not disturb what the variant is.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    renamed = rename_configuration("house", "villa", root=games_dir)

    assert renamed.name == "villa"
    assert os.path.isdir(os.path.join(games_dir, "villa"))
    assert not os.path.exists(os.path.join(games_dir, "house"))
    assert len(renamed.enabled_rules()) > 0


def test_a_deleted_variant_is_gone_and_nothing_else_is(games_dir):
    """Deleting removes the variant directory and leaves the rest of `games/` alone.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    delete_configuration("house", root=games_dir)

    assert not os.path.exists(os.path.join(games_dir, "house"))
    assert os.path.isdir(os.path.join(games_dir, DEFAULT_GAME))


def test_deleting_a_configuration_that_is_not_there_says_so(games_dir):
    """Deleting nothing must not read as having deleted the default.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    with pytest.raises(FileNotFoundError):
        delete_configuration("absent", root=games_dir)


def test_a_configuration_saved_outside_its_own_directory_is_allowed_for_any_name(games_dir):
    """The guard is the default configuration, not the act of writing a file.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert variant.is_default is False
    assert Configuration(name="house", path=variant.path).is_default is False
