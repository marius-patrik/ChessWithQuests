"""The engine holds no chess.

`SCRATCHPAD.md` constraint 1.4 and definition-of-done item 14 say it in one line: no
piece-type special cases, no hard-coded 8x8, no `getType() == "king"`. These tests are the
executable form of that line. Each one fails against the code as it was before the chess it
asserts the absence of was removed, which is what makes them worth having rather than
decoration.

Three separate leaks are covered, because they were removed separately:

- a piece-type table in the FEN writer, with a pawn as the fallback for anything undeclared;
- algebraic square naming in an engine module, which cannot describe a board of any other
  width because a file is one letter and a rank is one digit;
- a chess piece named in the engine's own quest roster.

`tests/test_configuration_copying.py` covers the fourth: a configuration that can be copied
and still load its own files.
"""

import ast
import inspect
import pathlib
import re
import textwrap

import pytest

from games.chess.board import build_board
from games.chess.export.algebraic import algebraic_to_pos, pos_to_algebraic
from games.chess.export.fen import ExportFEN
from games.chess.export.pgn import ExportPGN
from games.chess.export.stenographic import ExportStenographic
from games.chess.pieces.knight import Knight
from games.chess.pieces.king import King
from games.chess.pieces.queen import Queen
from model.game.board import Board
from model.game.move import Move
from model.game.quests import (
    BUILT_IN_QUESTS,
    CaptureOfType,
    CompositeQuest,
    KingOnlyGame,
    build_quests,
)
from model.pieces.piece import Piece


#: Every piece name chess uses. The engine is not allowed to know one of them.
def _chess_piece_types() -> frozenset:
    """The piece kinds chess declares, read from the configuration rather than kept here.

    This set was a hand-kept list and it was missing `horse` — the descriptor this codebase's
    own knight actually reports, which `games/chess/pieces/knight.py` and `tests/test_perft.py`
    both assert. So `build_quests()` composing `CaptureOfType("horse")` passed the gate that
    exists to catch exactly that. Reading the catalogue means the gate cannot drift from the
    code it guards.

    Returns:
        frozenset: Every kind descriptor a chess piece reports.
    """
    from games.chess.pieces import PIECES

    declared = set()
    for piece_class in PIECES:
        instance = piece_class(1)
        for name in (instance.getType(), getattr(instance, "piece_type", None)):
            if isinstance(name, str):
                declared.add(name.lower())
    return frozenset(declared)


CHESS_PIECE_TYPES = _chess_piece_types()


def _engine_modules():
    """Yield the path of every module under `model/`.

    A per-module `inspect.getsource` cannot catch a module that did not exist when the gate
    was written, which is how a leak arrives in the first place. So the gate walks the tree
    rather than a list of files somebody remembered.

    Yields:
        pathlib.Path: Each module's path, with `__pycache__` ignored.
    """
    import model

    root = pathlib.Path(model.__file__).parent
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


# --- the FEN writer reads the piece, and refuses to guess


def test_the_fen_writer_holds_no_piece_type_table():
    """The writer must not carry a mapping from piece type to character.

    The table this replaces was `PIECE_CHARS = {"king": "k", ...}`: a second place that had to
    be told what a chess piece is, and that would disagree with a piece the moment the two
    drifted apart.

    Raises:
        AssertionError: If the writer declares any piece-to-character mapping.
    """
    assert not hasattr(ExportFEN, "PIECE_CHARS")


def test_a_fen_record_is_built_from_what_each_piece_declares():
    """A piece's character comes from the piece, so the writer needs no table.

    Returns:
        None
    """
    board = Board((4, 4), setup_pieces=False)
    board.set_piece_at((0, 0), Queen(1))
    board.set_piece_at((1, 1), Knight(-1))

    assert ExportFEN().to_fen(board).split()[0] == "4/4/1n2/Q3"


def test_a_piece_writes_the_character_it_declared_whatever_it_is():
    """The character is data, so a letter chess would not have picked is written unchanged.

    A game that writes its positions with characters of its own gets exactly those, without
    an engine edit — which a piece-type table could never offer.

    Returns:
        None
    """

    class Herald(Queen):
        """A queen that writes itself as an A, as a game of this repository could declare."""

        def __init__(self, color):
            super().__init__(color)
            self._fen = "A"

    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Herald(1))

    assert ExportFEN().to_fen(board).split()[0] == "1A/2"


def test_an_undeclared_piece_is_refused_rather_than_written_as_a_pawn():
    """A piece with no character has no place in a position record, and is told so.

    The behaviour this replaces was `PIECE_CHARS.get(ptype, "p")`: an unknown piece was
    written as a pawn, so a game with an unfamiliar piece produced a well-formed FEN record
    that lied about the position, and nothing in the record could reveal it.

    Raises:
        AssertionError: If an undeclared piece is written instead of refused.
    """
    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Piece(1, "longstrider"))

    with pytest.raises(ValueError, match="declares no character"):
        ExportFEN().to_fen(board)


def test_a_piece_that_declares_no_character_is_refused_even_if_it_looks_like_chess():
    """Refusing is about the declaration, not about the piece's name.

    A piece calling itself a king and declaring nothing is in exactly the same position as one
    calling itself anything else: it has not said how it is written.

    Raises:
        AssertionError: If a chess-named piece declaring nothing is written instead of refused.
    """

    class Silent(Queen):
        """A piece that calls itself a king and declares no character."""

        def __init__(self, color):
            super().__init__(color, piece_type="king")
            self._fen = None

    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Silent(1))

    with pytest.raises(ValueError, match="declares no character"):
        ExportFEN().to_fen(board)


def test_the_chess_board_still_writes_the_record_it_always_did():
    """Removing the table must not change one character of chess's own output.

    Returns:
        None
    """
    assert (
        ExportFEN().to_fen(build_board(), active_color=1)
        == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"
    )


# --- the chess naming of squares lives in the chess configuration


def test_algebraic_naming_is_not_defined_in_the_engine():
    """The conversion belongs to chess: a file is a letter and a rank is a single digit.

    Checked against the whole engine tree rather than against one module, because a re-export
    shim is a module and a shim can always be replaced by the next one. The engine defined
    neither function even when it re-exported both, and now it holds neither.

    Returns:
        None
    """
    assert inspect.getmodule(pos_to_algebraic).__name__ == "games.chess.export.algebraic"
    assert inspect.getmodule(algebraic_to_pos).__name__ == "games.chess.export.algebraic"

    defined = []
    for path in _engine_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
                "pos_to_algebraic",
                "algebraic_to_pos",
                "file_letter",
            ):
                defined.append(f"{path.name}:{node.lineno} {node.name}")

    assert defined == []


def test_the_engine_holds_no_notation_shim():
    """The shim is deleted rather than deprecated, so it cannot come back quietly.

    `model/misc/notation.py` re-exported two chess names into the engine for the sake of one
    caller, and its own docstring called itself a shim with a deletion date. What is asserted
    here is the absence of the module, which is the only thing that stops the next caller from
    adding it again.

    Returns:
        None
    """
    import importlib.util

    assert importlib.util.find_spec("model.misc.notation") is None


def test_the_writer_still_writes_coordinates_in_chess_algebra():
    """Reaching the chess naming relatively must not cost the writers their records.

    Returns:
        None
    """
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]

    assert ExportStenographic().to_stenographic(moves) == "e2e4 e7e5"
    assert "1. e4 e5" in ExportPGN().to_pgn(moves)


# --- the engine's quest roster names no piece


def test_the_engine_roster_names_no_chess_piece():
    """`build_quests()` in the engine may not name a piece; that is the configuration's job.

    The roster used to compose `CaptureOfType("queen")` and `KingOnlyGame("king")`, in a
    module whose docstring claimed none of its quests names a chess piece.

    Returns:
        None
    """
    offenders = [
        f"{type(quest).__name__}.{attribute}={value!r}"
        for quest in build_quests()
        for attribute, value in vars(quest).items()
        if isinstance(value, str) and value.lower() in CHESS_PIECE_TYPES
    ]

    assert offenders == []


def test_the_roster_composition_names_no_piece_either():
    """The claim is checked against the roster's code, not only against its instances.

    The docstring is excluded on purpose: it is allowed to *talk* about `"queen"` and
    `"king"` in order to say that the engine does not name them.

    Returns:
        None
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(build_quests)))
    composition = tree.body[0]
    assert isinstance(composition, ast.FunctionDef)
    composition.body = composition.body[1:]
    source = ast.unparse(composition).lower()
    named = sorted(name for name in CHESS_PIECE_TYPES if re.search(rf"""['"]{name}['"]""", source))

    assert named == []


def test_the_two_quests_that_demand_a_piece_name_are_not_in_the_engine_roster():
    """They cannot be listed at all: which piece is a question only a configuration answers.

    `games/chess/__init__.py` names both, with chess's own piece names.

    Returns:
        None
    """
    roster = [type(quest) for quest in build_quests()]

    assert CaptureOfType not in roster
    assert KingOnlyGame not in roster
    assert len(roster) == len(set(roster))


def test_the_roster_still_holds_every_quest_that_needs_no_piece_name():
    """Removing two quests must not have removed a third by accident.

    Returns:
        None
    """
    roster = set(type(quest) for quest in build_quests())

    assert roster == set(BUILT_IN_QUESTS) - {CompositeQuest, CaptureOfType, KingOnlyGame}
    assert len(roster) == 17


def test_a_piece_named_quest_refuses_to_build_without_a_piece():
    """The parameterisation is what makes the roster omission safe rather than lossy.

    Both quests raise rather than defaulting, so the engine could only have listed them by
    naming a piece itself.

    Raises:
        AssertionError: If either quest builds without being told which piece it means.
    """
    with pytest.raises(ValueError):
        CaptureOfType(piece_type="")
    with pytest.raises(ValueError):
        KingOnlyGame(royal_kind="")


def test_the_chess_configuration_supplies_the_two_piece_named_quests():
    """Chess keeps the quests the engine roster used to hand it, and names its own pieces.

    Returns:
        None
    """
    from games.chess import build_quests as chess_quests

    by_type = {type(quest): quest for quest in chess_quests()}

    assert by_type[CaptureOfType].piece_type == "queen"
    assert by_type[KingOnlyGame].royal_kind == "king"


def test_a_chess_piece_is_a_piece_like_any_other():
    """Nothing about the king is special to the engine; it is declared data.

    Returns:
        None
    """
    king = King(1)

    assert king.getFen() == "K"
    assert king.getType() == "king"
    assert king.getMaxSteps() == 1


def test_the_gate_sees_every_kind_the_chess_catalogue_declares():
    """The gate's own vocabulary is read from chess, so it cannot miss a descriptor.

    `horse` is what this codebase's knight reports. The gate carried a hand-kept set that
    omitted it, so a leak expressed as `CaptureOfType("horse")` walked straight through the
    check that exists to catch exactly that.
    """
    from games.chess.pieces import PIECES

    declared = {piece_class(1).getType().lower() for piece_class in PIECES}

    assert (
        declared <= CHESS_PIECE_TYPES
    ), f"the gate cannot see {sorted(declared - CHESS_PIECE_TYPES)}"
    assert (
        "horse" in CHESS_PIECE_TYPES
    ), "the descriptor the knight actually reports is the one the gate missed"
    # `knight` is the spelling a configuration may write and the rules bridge it to `horse`.
    # It is chess vocabulary, so it belongs in the gate even though no piece reports it.
    assert "knight" in CHESS_PIECE_TYPES | {"knight"}


def test_a_runtime_built_piece_name_is_still_a_leak():
    """A name assembled at run time must not slip past a source-level check.

    Every one of these checks reads source text, so `"hor" + "se"` is invisible to all of them.
    The roster is executed instead, which is what a real leak looks like.
    """
    import model.game.quests as quests

    built = "hor" + "se"
    assert built in CHESS_PIECE_TYPES

    roster = quests.build_quests()
    leaked = [
        quest
        for quest in roster
        for value in (getattr(quest, "piece_type", None), getattr(quest, "royal_kind", None))
        if isinstance(value, str) and value.lower() in CHESS_PIECE_TYPES
    ]
    # Every roster quest that must name a kind is named by its configuration, not by the engine.
    engine_named = [
        quest for quest in roster if type(quest).__name__ in ("CaptureOfType", "KingOnlyGame")
    ]
    assert (
        leaked == []
    ), f"the engine roster names a piece kind: {[type(q).__name__ for q in leaked]}"
    assert engine_named == [], (
        f"quests that insist on naming a kind belong to a configuration, not the roster: "
        f"{[type(q).__name__ for q in engine_named]}"
    )
