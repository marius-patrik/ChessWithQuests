import pytest
from controller.window_controller import WindowController
from controller.controller import GameController


def test_window_controller_initialization():
    wc = WindowController()
    assert wc.title == "ChessWithQuests"
    assert (wc.width, wc.height) == (800, 600)
    assert not wc.is_running
    assert wc.status_message == "Welcome to ChessWithQuests"


def test_window_lifecycle():
    wc = WindowController()
    wc.start()
    assert wc.is_running is True
    assert wc.status_message == "Game Started"

    wc.stop()
    assert wc.is_running is False
    assert wc.status_message == "Game Stopped"


def test_window_controller_dialog_and_status():
    wc = WindowController()
    wc.set_status("Check!")
    assert wc.status_message == "Check!"

    wc.show_dialog("Do you accept the draw?")
    assert wc.active_dialog == "Do you accept the draw?"
    wc.close_dialog()
    assert wc.active_dialog is None


def test_window_controller_square_clicks_and_timer():
    wc = WindowController()
    wc.start()

    # Click white pawn at (1, 4)
    res1 = wc.on_square_clicked((1, 4))
    assert res1["action"] == "selected"
    assert "Square selected" in wc.status_message

    # Move to (3, 4)
    res2 = wc.on_square_clicked((3, 4))
    assert res2["action"] == "moved"
    assert "Move played" in wc.status_message

    # Tick timer
    initial_time = wc.game_controller.game_manager.casovac.get_time(-1)
    wc.tick_timer()  # Black's turn now
    assert wc.game_controller.game_manager.casovac.get_time(-1) == initial_time - 1
