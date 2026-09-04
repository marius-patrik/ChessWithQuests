import pytest
from model.game.manager import GameManager
from model.game.move import Move


def test_game_manager_initialization():
    gm = GameManager()
    assert gm.active_player == 1
    assert len(gm.players) == 2
    assert gm.get_state() == GameManager.STATE_IN_PROGRESS


def test_game_manager_possible_moves():
    gm = GameManager()
    # At game start, White has 16 pawn moves (8 single + 8 double) + 4 knight moves = 20 moves
    moves = gm.possible_moves()
    assert len(moves) == 20


def test_game_manager_make_move_and_switch_turns():
    gm = GameManager()
    move = Move((1, 4), (3, 4))  # e2 -> e4
    assert gm.make_move(move) is True
    assert gm.active_player == -1
    assert gm.current_move is move
    assert len(gm.game_logger.get_moves()) == 1


def test_game_manager_invalid_move():
    gm = GameManager()
    # Cannot move black piece when active player is white
    black_move = Move((6, 4), (4, 4))
    assert gm.make_move(black_move) is False
    assert gm.active_player == 1


def test_game_manager_timeout_state():
    gm = GameManager()
    gm.timer.player_times[0] = 0  # White timed out
    assert gm.get_state() == GameManager.STATE_TIMEOUT
