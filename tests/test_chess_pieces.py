"""The chess pieces, and what the chess configuration declares about them.

A piece's movement is machinery the engine owns; its glyph and its FEN letter are facts about
chess, so they are declared here and read through the parent. Nothing here is chess-specific
except the values themselves.
"""

import pytest
from games.chess.board import DIMENSIONS, build_board, starting_placement
from games.chess.clocks.fischer import Fischer
from games.chess.pieces.bishop import Bishop
from games.chess.pieces.horse import Horse, Knight
from games.chess.pieces.king import King
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen
from games.chess.pieces.rook import Rook
from games.chess.pieces.tower import Tower
from model.pieces.piece import Piece

CHESS_PIECES = (Pawn, Knight, Bishop, Rook, Queen, King)


def test_a_chess_board_is_eight_by_eight_and_fully_occupied_at_the_start():
    board = build_board()

    assert DIMENSIONS == (8, 8)
    assert board.dimensions == (8, 8)

    occupied = [square for row in board.board for square in row if square is not None]
    assert len(occupied) == 32

    # A back rank carries two rooks, two knights and two bishops, one queen and one king.
    expected = {Pawn: 8, Rook: 2, Knight: 2, Bishop: 2, Queen: 1, King: 1}
    for cls, count in expected.items():
        white = [p for p in occupied if isinstance(p, cls) and p.getColor() == 1]
        black = [p for p in occupied if isinstance(p, cls) and p.getColor() == -1]
        assert len(white) == count, f"{cls.__name__}: {len(white)} White pieces"
        assert len(black) == count, f"{cls.__name__}: {len(black)} Black pieces"


def test_the_starting_position_is_the_orthodox_one():
    board = build_board()

    # White's back rank reads R N B Q K B N R from the a-file.
    back = [board.get_piece_at((0, col)).getType() for col in range(8)]
    assert back == ["rook", "horse", "bishop", "queen", "king", "bishop", "horse", "rook"]

    # Pawns face each other on the second rank from either side.
    assert all(board.get_piece_at((1, col)).getType() == "pawn" for col in range(8))
    assert all(board.get_piece_at((6, col)).getType() == "pawn" for col in range(8))
    assert board.get_piece_at((0, 4)).getColor() == 1
    assert board.get_piece_at((7, 4)).getColor() == -1


def test_every_chess_piece_declares_a_glyph_for_both_colours():
    for cls in CHESS_PIECES:
        white, black = cls(1).getSymbol(), cls(-1).getSymbol()
        assert white, f"{cls.__name__} has no White glyph"
        assert black, f"{cls.__name__} has no Black glyph"
        assert white != black, f"{cls.__name__} draws both sides alike"


def test_the_glyphs_are_the_orthodox_chess_pieces():
    assert King(1).getSymbol() == "♔"
    assert Queen(1).getSymbol() == "♕"
    assert Rook(1).getSymbol() == "♖"
    assert Bishop(1).getSymbol() == "♗"
    assert Knight(1).getSymbol() == "♘"
    assert Pawn(1).getSymbol() == "♙"
    assert King(-1).getSymbol() == "♚"


def test_every_chess_piece_declares_its_fen_letter():
    expected = {Pawn: "P", Knight: "N", Bishop: "B", Rook: "R", Queen: "Q", King: "K"}
    for cls, letter in expected.items():
        assert cls(1).getFen() == letter
        assert cls(-1).getFen() == letter


def test_the_engine_declares_no_chess_and_asks_pieces_for_what_they_do_not_know():
    """The parent carries the questions; a piece that declares nothing answers nothing."""
    plain = Piece(color=1, piece_type="widget", vectors=[(1, 0)])

    assert plain.getSymbol() is None
    assert plain.getFen() is None
    assert plain.hasMoved() is False


def test_the_czech_aliases_are_the_same_piece():
    """`Tower` is Czech for the rook, and `Horse` is Czech for the knight."""
    assert Tower is Rook
    assert Knight is Horse
    assert Tower(1).getFen() == "R"
    assert Knight(1).getFen() == "N"


def test_a_chess_clock_adds_its_increment_only_after_a_move():
    clock = Fischer(initial_seconds=600, increment_seconds=5)

    assert clock.get_time(1) == 600
    assert clock.get_time(-1) == 600

    clock.tick(1, 30)
    assert clock.get_time(1) == 570

    # The increment is a reward for having moved, not a refund for the time spent.
    clock.credit(1)
    assert clock.get_time(1) == 575
    assert clock.get_time(-1) == 600

    clock.reset()
    assert clock.get_time(1) == 600


def test_a_clock_never_reports_a_player_as_having_time_they_do_not_have():
    clock = Fischer(initial_seconds=10, increment_seconds=0)

    clock.tick(1, 9999)
    assert clock.get_time(1) == 0
    assert clock.is_expired(1) is True
    assert clock.is_expired(-1) is False


@pytest.mark.parametrize("rows,cols", [(8, 7), (8, 9), (3, 8), (1, 8)])
def test_a_board_too_small_for_chess_has_no_chess_starting_position(rows, cols):
    with pytest.raises(ValueError):
        starting_placement(rows, cols)
