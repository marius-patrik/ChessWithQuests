from games.chess.board import build_board
import pytest
from model.game.move import Move
from model.game.board import Board
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen


def test_move_initialization_and_properties():
    pawn = Pawn(1)
    move = Move((1, 0), (2, 0), piece=pawn, move_type="normal")
    assert move.start_pos == (1, 0)
    assert move.end_pos == (2, 0)
    assert move.piece is pawn
    assert move.move_type == "normal"


def test_move_validate():
    move = Move((1, 0), (2, 0))
    assert move.validate() is True

    invalid_move_same = Move((1, 0), (1, 0))
    assert invalid_move_same.validate() is False

    invalid_move_bounds = Move((1, 0), (8, 0))
    assert invalid_move_bounds.validate() is False


def test_move_execute_on_board():
    board = build_board()
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


def test_an_en_passant_victim_reaches_the_capture_lists():
    """The victim does not stand on the destination, so `move_piece` cannot record it.

    An en passant capture was invisible to the board's capture lists: the pawn vanished from
    the board and nothing appeared in the tray, so the player's Taken and Lost panels silently
    disagreed with the position.
    """
    from games.chess.pieces.king import King
    from games.chess.pieces.pawn import Pawn
    from model.game.board import Board

    board = Board((8, 8), setup_pieces=False)
    board.set_piece_at((4, 3), Pawn(1))  # d5, the pawn that captures
    board.set_piece_at((5, 4), Pawn(-1))  # e6, the pawn that advanced e7-e5
    board.set_piece_at((0, 4), King(1))
    board.set_piece_at((7, 4), King(-1))

    capture = Move((4, 3), (5, 4), move_type="en_passant", capture_from=(5, 4))
    assert capture.apply_to_board(board) is not None

    # The lists are named for the colour of the piece taken, not the taker: a White pawn
    # taking a Black one lands in `captured_black`, which is where the panel reads from.
    assert capture.captured_piece is not None
    assert capture.captured_piece.getColor() == -1
    assert board.captured_black == [capture.captured_piece]
    assert board.captured_white == []


def test_undoing_an_en_passant_capture_restores_the_capture_lists():
    """The undo truncates to what it recorded, and the victim comes back."""
    from games.chess.pieces.king import King
    from games.chess.pieces.pawn import Pawn
    from model.game.board import Board

    board = Board((8, 8), setup_pieces=False)
    board.set_piece_at((4, 3), Pawn(1))
    victim = Pawn(-1)
    board.set_piece_at((5, 4), victim)
    board.set_piece_at((0, 4), King(1))
    board.set_piece_at((7, 4), King(-1))

    capture = Move((4, 3), (5, 4), move_type="en_passant", capture_from=(5, 4))
    applied = capture.apply_to_board(board)
    capture.unapply_from_board(board, applied)

    assert board.captured_white == []
    assert board.captured_black == []
    assert board.get_piece_at((5, 4)) is victim
