import pytest
from games.chess.rules import build_rules
from model.game.board import Board
from model.game.move import Move
from model.game.validator import MoveValidator
from model.pieces.king import King
from model.pieces.queen import Queen
from model.pieces.rook import Rook
from model.pieces.pawn import Pawn


def test_validator_initialization():
    board = Board()
    validator = MoveValidator(board, rules=build_rules())
    assert validator.find_royal(1) == (0, 4)
    assert validator.find_royal(-1) == (7, 4)


def test_royal_piece_is_declared_by_a_rule_not_a_type_name():
    """A validator with no rules in force has no royal piece, so nothing is ever in check."""
    board = Board()
    assert MoveValidator(board).find_royal(1) is None
    assert MoveValidator(board).is_check(1) is False
    assert MoveValidator(board).royal_kinds() == []
    assert MoveValidator(board, rules=build_rules()).royal_kinds() == ["king"]


def test_validator_pawn_moves():
    board = Board()
    validator = MoveValidator(board)
    # White pawn at (1, 0) can move to (2, 0) and (3, 0)
    valid_moves = validator.get_valid_moves((1, 0))
    assert (2, 0) in valid_moves
    assert (3, 0) in valid_moves


def test_validator_check_detection():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board, rules=build_rules())
    white_king = King(1)
    black_rook = Rook(-1)

    board.set_piece_at((0, 4), white_king)
    board.set_piece_at((7, 4), black_rook)

    assert validator.is_check(1) is True
    assert validator.is_check(-1) is False


def test_validator_checkmate():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board, rules=build_rules())
    # Corner checkmate scenario: King in corner attacked by Queen, Queen backed by Rook
    white_king = King(1)
    black_queen = Queen(-1)
    black_rook = Rook(-1)

    board.set_piece_at((0, 0), white_king)
    board.set_piece_at((0, 1), black_queen)
    board.set_piece_at((1, 1), black_rook)

    assert validator.is_checkmate(1) is True


def test_validator_stalemate():
    board = Board(setup_pieces=False)
    validator = MoveValidator(board, rules=build_rules())
    # King at (0, 0) not in check, but all surrounding squares attacked
    white_king = King(1)
    black_queen = Queen(-1)
    black_king = King(-1)

    board.set_piece_at((0, 0), white_king)
    board.set_piece_at((1, 2), black_queen)
    board.set_piece_at((2, 0), black_king)

    assert validator.is_check(1) is False
    assert validator.is_stalemate(1) is True


def test_validator_simulate_move():
    board = Board()
    validator = MoveValidator(board)
    move = Move((1, 0), (2, 0))
    validator.set_move(move)
    saved_state = validator.simulate_move()
    assert len(saved_state) == 2
    assert board.get_piece_at((2, 0)).getName() == "Pawn"
