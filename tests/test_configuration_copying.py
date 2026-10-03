"""A configuration is a directory that can be copied.

`SCRATCHPAD.md` section 2: `cp -r games/chess games/house`, change what differs, and a
variant exists. Duplication is the extension mechanism, so a copy that quietly loaded the
*original* configuration's files would leave a variant that looks edited and plays the
original — the worst failure mode available, because nothing errors and nothing warns.

These tests copy the shipped chess configuration into a throwaway `games/` root, edit what
differs, load it by name, and hold the loaded configuration to the copy's own files.
"""

import os
import pathlib
import re
import shutil
import textwrap

import pytest

from model.game.board import Board
from model.game.configuration import load_configuration
from model.game.games import games_root

#: The copied board. Ten by ten, with one of the copy's own pieces on it.
COPY_BOARD = textwrap.dedent('''
    """The house board: ten by ten, which chess is not."""

    from model.game.board import Board

    DIMENSIONS = (10, 10)

    def build_board(rows=DIMENSIONS[0], cols=DIMENSIONS[1]):
        """Build the house board, holding a piece the copy declares for itself.

        Args:
            rows: Ranks the board has.
            cols: Files the board has.

        Returns:
            Board: A ten by ten board.
        """
        from .pieces.knight import Knight

        return Board((rows, cols), placement=[((0, 0), Knight(1))])
    ''')


@pytest.fixture
def copied_chess(tmp_path):
    """Copy the shipped chess configuration into a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        str: The path of the `games/` root holding the copy, which is also what
        `load_configuration` is pointed at.
    """
    games = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / "chess",
        games / "house",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (games / "house" / "board.py").write_text(COPY_BOARD, encoding="utf-8")
    return str(games)


def _loaded_piece_class(configuration):
    """Return the class of a piece standing on the loaded board.

    Args:
        configuration: The loaded configuration.

    Returns:
        type: The class of the piece at the board's first square.
    """
    return type(configuration.board.get_piece_at((0, 0)))


def test_a_copied_configuration_builds_its_own_board(copied_chess):
    """The copy's board is the board that gets loaded, whatever size the copy declares.

    This is the exact failure the audit reported: with an absolute import the copy's
    `__init__.py` reached back into `games.chess.board`, so setting `DIMENSIONS = (10, 10)` in
    the copy changed nothing and the loaded board was still eight by eight, with no error and
    no warning.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_chess)

    assert configuration.board.dimensions == (10, 10)
    assert (configuration.board.rows, configuration.board.cols) == (10, 10)


def test_a_copied_configuration_places_the_copies_own_pieces(copied_chess):
    """The pieces on a copied board are the copy's, not the original's.

    The module a class came from is the proof: a class loaded through `games.chess` says so,
    and a class loaded through the copy says `_configuration_…` instead.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_chess)
    piece_class = _loaded_piece_class(configuration)

    assert piece_class.__name__ == "Knight"
    assert piece_class.__module__.startswith("_configuration_")
    assert piece_class.__module__.endswith("house.pieces.knight")


def test_a_copied_configuration_declares_its_own_piece_catalogue(copied_chess):
    """`Configuration.pieces` must be the copy's piece classes, not the original's.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_chess)

    assert configuration.pieces
    for piece_class in configuration.pieces:
        assert piece_class.__module__.startswith("_configuration_"), piece_class.__name__


def test_a_copied_configuration_composes_from_its_own_directories(copied_chess):
    """Everything the copy's `__init__.py` names comes out of the copy.

    The clock is the clean witness: `games/chess/clocks/fischer.py` imports nothing but the
    engine's timer, so a clock whose module is the original's can only have been reached by
    an absolute import.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_chess)

    assert type(configuration.clocks[0]).__module__.startswith("_configuration_")
    assert configuration.name == "house"
    assert configuration.path.endswith(os.path.join("games", "house"))


def test_the_shipped_chess_configuration_still_loads_itself():
    """Converting to relative imports must not break the configuration that ships.

    Returns:
        None
    """
    configuration = load_configuration("chess")

    assert configuration.board.dimensions == (8, 8)
    assert configuration.board.get_piece_at((0, 0)).getName() == "Rook"
    assert configuration.pieces
    assert configuration.rules
    assert configuration.quests
    assert configuration.exporters


def test_the_shipped_configuration_imports_under_its_own_package_name_too():
    """A configuration is importable as a package as well as loadable by path.

    `load_configuration` loads every configuration from its file location under a synthetic
    name, so loading alone proves nothing about the ordinary import. Relative imports have to
    work under both.

    Returns:
        None
    """
    import games.chess

    configuration = games.chess.build_configuration()

    assert configuration.board.dimensions == (8, 8)
    assert type(configuration.board.get_piece_at((0, 0))).__module__.startswith(
        "games.chess.pieces"
    )


def test_a_copied_configuration_keeps_its_own_rules(copied_chess):
    """A copy composes the copy's rules, including the ones its promotions produce.

    `games/chess/rules/` used to say `from games.chess.rules.… import …`, so a copy was
    handed the *original's* rule objects — while its board, pieces, clocks and quests were
    its own, and nothing said so. `games/chess/rules/promotion.py` went further and built the
    promoted piece out of `games.chess.pieces`, so a promotion in a copy produced a piece
    class belonging to a configuration that was not being played.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_chess)

    assert configuration.rules
    for rule in configuration.rules:
        module = type(rule).__module__
        assert module.startswith("_configuration_"), type(rule).__name__
        assert ".rules." in module, type(rule).__name__


def test_a_promotion_in_a_copied_configuration_yields_the_copies_piece(copied_chess):
    """The replacement piece belongs to the configuration being played.

    `games/chess/rules/promotion.py` used to build the promoted piece out of
    `games.chess.pieces.…`, so a promotion in a copy produced a piece class belonging to a
    configuration that was not being played. The module a class came from is the proof,
    exactly as it is for the board's pieces: a class loaded through `games.chess` says so,
    and one loaded through the copy says `_configuration_…` instead.

    Args:
        copied_chess: The throwaway `games/` root holding the copy.

    Returns:
        None
    """
    import sys

    from games.chess.pieces.pawn import Pawn

    configuration = load_configuration("house", root=copied_chess)
    rule = next(rule for rule in configuration.rules if type(rule).__name__ == "PromotionRule")
    copy_module = sys.modules[type(rule).__module__]

    promoted = copy_module._make_promotion(Pawn(1), "queen")

    assert type(promoted).__module__.startswith("_configuration_")
    assert type(promoted).__module__.endswith("house.pieces.queen")


def test_a_board_a_configuration_declares_is_not_the_engine_default():
    """The engine's board has no opinion, and a variant's board is whatever it says.

    Returns:
        None
    """
    assert Board.DEFAULT_DIMENSIONS == (8, 8)
    assert Board((10, 10), setup_pieces=False).dimensions == (10, 10)


def test_editing_a_rule_file_is_visible_on_reload_in_the_same_process(tmp_path):
    """The code editor's save must reach the running game, not only a fresh interpreter.

    The loader registered the configuration package under a unique name but never removed the
    previous load's submodules, so `from .rules.check import CheckRule` resolved to the cached
    module and handed back the same class object. A player saved an edit, the editor reported
    "No problems found", and the game — and every later reload — kept the old rule.
    """
    from model.game.configuration import load_configuration_at

    games = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / "chess",
        games / "house",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    source = games / "house" / "rules" / "check.py"

    first = load_configuration_at(str(games / "house"), root=str(games))
    before = [rule.default_name for rule in first.enabled_rules()]

    source.write_text(
        source.read_text(encoding="utf-8").replace(
            'default_name = "Check"', 'default_name = "Checked"', 1
        ),
        encoding="utf-8",
    )

    second = load_configuration_at(str(games / "house"), root=str(games))
    after = [rule.default_name for rule in second.enabled_rules()]

    assert "Checked" in after, "the edit did not reach a reload in this process"
    assert len(after) == len(before)


def test_a_purged_configuration_leaves_nothing_behind_in_sys_modules(tmp_path):
    """Reloading must not accumulate a module per load, nor keep the old one reachable."""
    import sys

    from model.game.configuration import load_configuration_at

    games = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / "chess",
        games / "house",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    for _attempt in range(3):
        load_configuration_at(str(games / "house"), root=str(games))

    mine = "_configuration_" + re.sub(r"\W", "_", str((games / "house").resolve()))

    # Three loads of the same directory must not leave three copies: the package name is
    # derived from the path, so a reload replaces it rather than adding beside it. Only this
    # test's own copy is counted — other tests have loaded their copies and left those behind.
    # The package itself, plus one module per file it imported. Three loads must not make
    # three sets: the name is derived from the path, so a reload replaces rather than adds.
    loaded = sorted(name for name in sys.modules if name == mine or name.startswith(mine + "."))

    assert mine in loaded, "the configuration registered nothing"
    assert (
        len([name for name in loaded if "." not in name[len(mine) :]]) == 1
    ), f"three loads registered {len(loaded)} modules for one directory"
    assert (
        len([name for name in loaded if name.endswith(".board")]) == 1
    ), "board.py was loaded more than once"
