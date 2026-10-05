from games.chess.board import build_board
import pytest
from model.game.board import Board
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen


def test_board_dimensions_and_setup():
    board = build_board()
    assert board.dimensions == (8, 8)
    assert board.is_within_bounds(0, 0)
    assert not board.is_within_bounds(-1, 0)
    assert not board.is_within_bounds(8, 8)

    # Check corners have rooks and center has kings/queens
    assert board.get_piece_at((0, 4)).getName() == "King"
    assert board.get_piece_at((7, 4)).getName() == "King"
    assert board.get_piece_at((1, 0)).getName() == "Pawn"
    assert board.get_piece_at((6, 0)).getName() == "Pawn"
    assert board.get_piece_at((3, 3)) is None


def test_board_move_piece():
    board = Board(setup_pieces=False)
    pawn = Pawn(1)
    board.set_piece_at((1, 0), pawn)

    assert board.move_piece((1, 0), (2, 0)) is True
    assert board.get_piece_at((1, 0)) is None
    assert board.get_piece_at((2, 0)) is pawn
    assert pawn.hasMoved() is True


def test_board_capture():
    board = Board(setup_pieces=False)
    white_pawn = Pawn(1)
    black_pawn = Pawn(-1)
    board.set_piece_at((1, 0), white_pawn)
    board.set_piece_at((2, 1), black_pawn)

    assert board.move_piece((1, 0), (2, 1)) is True
    assert board.get_piece_at((2, 1)) is white_pawn
    assert len(board.captured_black) == 1
    assert board.captured_black[0] is black_pawn


def test_board_replace_piece():
    board = Board(setup_pieces=False)
    pawn = Pawn(1)
    board.set_piece_at((6, 0), pawn)
    queen = Queen(1)
    board.replace_piece((6, 0), queen)
    assert board.get_piece_at((6, 0)) is queen


def test_a_board_numbers_its_own_columns():
    """A board knows how many columns it has and nothing about what they are called.

    The window draws whatever this returns, so this is where a configuration's naming is
    declared — and where it is not, the naming is the column's own number rather than a
    default some other game would recognise.
    """
    board = Board((5, 7), setup_pieces=False)

    assert [board.file_label(col) for col in range(board.cols)] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
    ]


def test_the_chess_board_names_its_files_with_letters():
    """Chess declares the naming, so the letters come from the chess configuration."""
    from games.chess.export.algebraic import pos_to_algebraic

    board = build_board()

    assert board.file_label(0) == "a"
    assert board.file_label(4) == "e"
    assert board.file_label(7) == "h"
    # One naming, written once: the label under a square and the square's own algebraic name
    # are the same letter.
    assert board.file_label(4) == pos_to_algebraic((0, 4))[0]


def test_a_snapshot_is_a_position_of_its_own_and_not_the_board_being_played_on():
    """The pieces are copied too, which is the whole of what makes a snapshot worth taking.

    A rule finds a piece by walking the board and comparing identity, so a snapshot that
    shared its pieces would answer questions about the game in progress — and the moved flag
    is part of a position's identity, so it is part of what is copied.
    """
    board = Board((4, 4), setup_pieces=False)
    pawn = Pawn(1)
    board.set_piece_at((1, 1), pawn)

    snapshot = board.snapshot()
    board.move_piece((1, 1), (2, 1))

    assert snapshot is not board
    assert snapshot.get_piece_at((1, 1)) is not None
    assert snapshot.get_piece_at((2, 1)) is None
    assert snapshot.get_piece_at((1, 1)).hasMoved() is False
    assert pawn.hasMoved() is True


def test_a_snapshot_keeps_the_board_it_was_taken_from():
    """A board that names its own files must still name them when it is copied.

    A snapshot is a `Board`, and the engine hands it to writers and rules that ask it
    questions about itself — its dimensions, its bounds and its own naming of a square.
    Copying must not quietly reduce any of them to the base class.
    """
    from games.chess.board import ChessBoard

    board = build_board()
    snapshot = board.snapshot()

    assert isinstance(snapshot, ChessBoard)
    assert snapshot.dimensions == board.dimensions
    assert snapshot.file_label(4) == "e"
