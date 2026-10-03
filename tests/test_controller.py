import pytest
from controller.controller import GameController
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


def test_a_click_plays_the_move_the_rules_offered_not_a_rebuilt_one():
    """A rule may attach more than a destination to a move, and the click path must keep it.

    A draughts capture is a chain of hops carried on the Move. The controller used to build a
    fresh `Move` from the two clicked squares, which had no hops, so the legality check
    refused it and a capture was impossible to play through the window.
    """
    from model.game.configuration import load_configuration
    from model.game.manager import GameManager

    controller = GameController(GameManager(configuration=load_configuration("checkers")))
    for start, end in [((2, 1), (3, 0)), ((5, 0), (4, 1)), ((1, 0), (2, 1)), ((4, 1), (3, 2))]:
        controller.select_square(start)
        assert controller.handle_square_click(end)["action"] == "moved"

    captures = [
        move for move in controller.game_manager.get_valid_moves() if move.move_type == "capture"
    ]
    assert captures, "no capture is on offer"
    chain = captures[0]
    assert getattr(chain, "hops", None), "the offered capture carries no hops"

    controller.select_square(chain.start_pos)
    result = controller.handle_square_click(chain.end_pos)

    assert result["action"] == "moved"
    assert result["success"] is True


def test_find_move_returns_none_for_a_square_pair_that_is_not_a_move():
    controller = GameController()
    manager = controller.game_manager

    assert manager.move_validator.find_move((0, 0), (7, 7), manager.board) is None
    assert manager.move_validator.find_move((-1, 0), (0, 0), manager.board) is None
