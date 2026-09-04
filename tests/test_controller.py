import pytest
from controller.controller import GameController, Controller
from model.game.manager import GameManager


def test_controller_initialization():
    ctrl = GameController()
    assert ctrl.selected_square is None
    assert ctrl.highlighted_moves == []
    assert isinstance(ctrl.game_manager, GameManager)


def test_controller_select_and_move_flow():
    ctrl = GameController()
    # Click 1: Click on White Pawn at (1, 4)
    res1 = ctrl.handle_square_click((1, 4))
    assert res1["action"] == "selected"
    assert res1["selected"] == (1, 4)
    assert (2, 4) in res1["valid_moves"]
    assert (3, 4) in res1["valid_moves"]

    # Click 2: Click on destination (3, 4)
    res2 = ctrl.handle_square_click((3, 4))
    assert res2["action"] == "moved"
    assert res2["success"] is True
    assert ctrl.selected_square is None
    # Next turn is Black's turn (-1)
    assert ctrl.game_manager.active_player == -1


def test_controller_reselect():
    ctrl = GameController()
    # Select e2 pawn
    ctrl.handle_square_click((1, 4))
    assert ctrl.selected_square == (1, 4)

    # Click another white piece (d2 pawn)
    res = ctrl.handle_square_click((1, 3))
    assert res["action"] == "reselected"
    assert ctrl.selected_square == (1, 3)


def test_controller_new_game():
    ctrl = GameController()
    ctrl.handle_square_click((1, 4))
    ctrl.handle_square_click((3, 4))
    assert ctrl.game_manager.active_player == -1

    ctrl.new_game()
    assert ctrl.game_manager.active_player == 1
    assert ctrl.selected_square is None
