import pytest
from model.game.board import Board
from model.pieces.pawn import Pawn
from model.pieces.queen import Queen


def test_board_dimensions_and_setup():
    board = Board()
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
