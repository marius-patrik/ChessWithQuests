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
from games.chess.pieces.horse import Horse
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
from model.misc.export_writers import ChessNotationWriter
from model.pieces.piece import Piece

#: Every piece name chess uses. The engine is not allowed to know one of them.
CHESS_PIECE_TYPES = frozenset(
    {"king", "queen", "rook", "bishop", "knight", "horse", "pawn", "tower"}
)


# --- the FEN writer reads the piece, and refuses to guess


def test_the_fen_writer_holds_no_piece_type_table():
    """The writer must not carry a mapping from piece type to character.

    The table this replaces was `PIECE_CHARS = {"king": "k", ...}`: a second place that had to
    be told what a chess piece is, and that would disagree with a piece the moment the two
    drifted apart.

    Raises:
        AssertionError: If the writer declares any piece-to-character mapping.
    """
    assert not hasattr(ChessNotationWriter, "PIECE_CHARS")


def test_a_fen_record_is_built_from_what_each_piece_declares():
    """A piece's character comes from the piece, so the writer needs no table.

    Returns:
        None
    """
    board = Board((4, 4), setup_pieces=False)
    board.set_piece_at((0, 0), Queen(1))
    board.set_piece_at((1, 1), Horse(-1))

    assert ChessNotationWriter().to_fen(board).split()[0] == "4/4/1n2/Q3"


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

    assert ChessNotationWriter().to_fen(board).split()[0] == "1A/2"


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
        ChessNotationWriter().to_fen(board)


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
        ChessNotationWriter().to_fen(board)


def test_the_chess_board_still_writes_the_record_it_always_did():
    """Removing the table must not change one character of chess's own output.

    Returns:
        None
    """
    assert (
        ChessNotationWriter().to_fen(build_board(), active_color=1)
        == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"
    )


# --- the chess naming of squares lives in the chess configuration


def test_algebraic_naming_is_not_defined_in_the_engine():
    """The conversion belongs to chess: a file is a letter and a rank is a single digit.

    `model/misc/notation.py` re-exports both names for the two callers outside the
    configuration layer, but it must not define them.

    Returns:
        None
    """
    import model.misc.notation as shim

    engine_source = pathlib.Path(shim.__file__).read_text(encoding="utf-8")

    assert "def pos_to_algebraic" not in engine_source
    assert "def algebraic_to_pos" not in engine_source
    assert inspect.getmodule(shim.pos_to_algebraic).__name__ == "games.chess.export.algebraic"
    assert inspect.getmodule(algebraic_to_pos).__name__ == "games.chess.export.algebraic"


def test_the_engine_shim_serves_the_callers_that_have_not_moved_yet():
    """`view/player_game_view.py` still imports the old path, so the old path must work.

    The shim is the price of not editing a file another agent owns, and its own docstring says
    it is a shim and when to delete it.

    Returns:
        None
    """
    import model.misc.notation as shim

    assert shim.pos_to_algebraic is pos_to_algebraic
    assert shim.algebraic_to_pos is algebraic_to_pos


def test_the_writer_still_writes_coordinates_in_chess_algebra():
    """Reaching the chess configuration on demand must not cost the writer its records.

    Returns:
        None
    """
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]

    assert ChessNotationWriter().to_stenographic(moves) == "e2e4 e7e5"
    assert "1. e4 e5" in ChessNotationWriter().to_pgn(moves)


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
