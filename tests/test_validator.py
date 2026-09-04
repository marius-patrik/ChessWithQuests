import pytest
from model.game.board import Board
from model.game.move import Move
from model.game.validator import MoveValidator, RevizorTahu
from model.pieces.king import King
from model.pieces.queen import Queen
from model.pieces.rook import Rook
from model.pieces.pawn import Pawn


def test_validator_initialization():
    board = Board()
    validator = MoveValidator(board)
    assert validator.find_king(1) == (0, 4)
    assert validator.find_king(-1) == (7, 4)


def test_validator_pawn_moves():
    board = Board()
    validator = MoveValidator(board)
    # White pawn at (1, 0) can move to (2, 0) and (3, 0)
    valid_moves = validator.get_valid_moves((1, 0))
    assert (2, 0) in valid_moves
    assert (3, 0) in valid_moves


def test_validator_check_detection():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board)
    white_king = King(1)
    black_rook = Rook(-1)

    board.set_piece_at((0, 4), white_king)
    board.set_piece_at((7, 4), black_rook)

    assert validator.is_check(1) is True
    assert validator.check_Sach(1) is True
    assert validator.is_check(-1) is False


def test_validator_checkmate():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board)
    # Corner checkmate scenario: King in corner attacked by Queen, Queen backed by Rook
    white_king = King(1)
    black_queen = Queen(-1)
    black_rook = Rook(-1)

    board.set_piece_at((0, 0), white_king)
    board.set_piece_at((0, 1), black_queen)
    board.set_piece_at((1, 1), black_rook)

    assert validator.is_checkmate(1) is True
    assert validator.check_Mat(1) is True


def test_validator_stalemate():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board)
    # King at (0, 0) not in check, but all surrounding squares attacked
    white_king = King(1)
    black_queen = Queen(-1)
    black_king = King(-1)

    board.set_piece_at((0, 0), white_king)
    board.set_piece_at((1, 2), black_queen)
    board.set_piece_at((2, 0), black_king)

    assert validator.is_check(1) is False
    assert validator.is_stalemate(1) is True
    assert validator.check_Pat(1) is True


def test_validator_simulate_move():
    board = Board()
    validator = MoveValidator(board)
    move = Move((1, 0), (2, 0))
    validator.set_move(move)
    saved_state = validator.simulate_move()
    assert len(saved_state) == 2
    assert board.get_piece_at((2, 0)).getName() == "Pawn"


def test_revizor_alias():
    revizor = RevizorTahu()
    assert isinstance(revizor, MoveValidator)
