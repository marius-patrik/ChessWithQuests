import pytest
from model.game.move import Move, Tah
from model.game.board import Board
from model.pieces.pawn import Pawn
from model.pieces.queen import Queen


def test_move_initialization_and_properties():
    pawn = Pawn(1)
    move = Move((1, 0), (2, 0), piece=pawn, move_type="normal")
    assert move.start_pos == (1, 0)
    assert move.end_pos == (2, 0)
    assert move.piece is pawn
    assert move.move_type == "normal"
    assert move.vychozi_pozice == (1, 0)
    assert move.cilova_pozice == (2, 0)
    assert move.figurka is pawn
    assert move.typ_tahu == "normal"


def test_move_validate():
    move = Move((1, 0), (2, 0))
    assert move.validate() is True

    invalid_move_same = Move((1, 0), (1, 0))
    assert invalid_move_same.validate() is False

    invalid_move_bounds = Move((1, 0), (8, 0))
    assert invalid_move_bounds.validate() is False


def test_move_execute_on_board():
    board = Board()
    move = Move((1, 0), (2, 0))
    assert move.validate(board) is True
    assert move.execute(board) is True
    assert board.get_piece_at((1, 0)) is None
    assert board.get_piece_at((2, 0)).getName() == "Pawn"


def test_move_execute_promotion():
    board = Board(setup_pieces=False)
    pawn = Pawn(1)
    queen = Queen(1)
    board.set_piece_at((6, 0), pawn)

    move = Move((6, 0), (7, 0), piece=pawn, move_type="promotion", promotion_piece=queen)
    assert move.execute(board) is True
    assert board.get_piece_at((7, 0)) is queen


def test_tah_alias():
    tah = Tah((1, 0), (3, 0))
    assert tah.over_platnost() is True
