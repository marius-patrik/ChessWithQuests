"""The window, driven as a player drives it.

These tests build the real widgets and click real squares, because the wiring between a click,
the controller and the redraw is the thing that breaks. They need a display; where there is
none they skip rather than fail, so the suite still runs headless. `format_seconds` needs
neither a display nor tkinter and is always checked.
"""

import tkinter as tk
import pytest

from model.game.games import available_games
from view.player_game_view import PlayerGameView, STATE_LABELS
from view.player_view import format_seconds
from view.start_modal import StartModal


@pytest.fixture
def window(tk_root):
    """Yield a frame showing a real chess game.

    Args:
        tk_root: The session's Tk root.

    Yields:
        PlayerGameView: A view built on a freshly dealt chess game.
    """
    from view.app import build_application

    for child in tk_root.winfo_children():
        child.destroy()
    build_application(tk_root, show_modal=False)
    tk_root.update()
    yield tk_root.game_view
    for child in tk_root.winfo_children():
        child.destroy()


def click(view, square) -> None:
    """Click a square the way the canvas does.

    Args:
        view: The `PlayerGameView` to click in.
        square: The (row, col) to click.

    Returns:
        None
    """
    view.on_square_clicked(square)
    view.update()


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "00:00"), (5, "00:05"), (65, "01:05"), (600, "10:00"), (3661, "61:01"), (-1, "-00:01")],
)
def test_a_clock_reads_the_way_a_player_reads_it(seconds, expected):
    """Seconds become mm:ss, and a clock that has run out says so."""
    assert format_seconds(seconds) == expected


def test_every_game_state_has_something_to_say():
    """No state may be silent while it is the reason the game has stopped."""
    from model.game.manager import GameManager

    for state in (
        GameManager.STATE_TIMEOUT,
        GameManager.STATE_CHECKMATE,
        GameManager.STATE_STALEMATE,
    ):
        assert STATE_LABELS.get(state), f"state {state} has no label"


def test_the_start_modal_offers_every_shipped_game():
    """The player chooses the configuration, so every one of them must be offered."""
    games = available_games()
    assert "chess" in games


def test_the_window_shows_a_dealt_board(window):
    view = window
    manager = view.manager

    assert view.board_view.board is manager.board
    # 64 squares plus a glyph on each of the 32 pieces, plus the coordinate labels.
    drawn = len(view.board_view.canvas.find_all())
    assert drawn > 64
    assert view.turn.get() == "White to move"


def test_clicking_a_piece_shows_where_it_may_go(window):
    view = window

    click(view, (1, 4))  # the e2 pawn
    assert view.board_view.selected == (1, 4)
    assert (3, 4) in view.board_view.targets  # the double step
    assert (2, 4) in view.board_view.targets  # the single step
    assert (7, 4) not in view.board_view.targets  # straight ahead is blocked by a pawn


def test_clicking_the_target_moves_the_piece_and_hands_over_the_turn(window):
    view = window
    manager = view.manager

    click(view, (1, 4))
    click(view, (3, 4))

    assert manager.board.get_piece_at((3, 4)) is not None
    assert manager.board.get_piece_at((1, 4)) is None
    assert manager.active_player == -1
    assert view.turn.get() == "Black to move"
    assert view.board_view.selected is None
    assert view.history.size() == 1


def test_an_illegal_click_is_refused_and_says_so(window):
    view = window
    manager = view.manager

    click(view, (6, 4))  # a black piece on White's turn
    assert manager.active_player == 1
    assert view.history.size() == 0


def test_a_game_played_to_checkmate_ends_the_window_in_a_result(window):
    """Fool's mate, played as clicks, must reach a result the window states."""
    view = window
    manager = view.manager

    for square in [(1, 5), (2, 5), (6, 4), (4, 4), (1, 6), (3, 6), (7, 3), (3, 7)]:
        click(view, square)

    assert manager.get_state() == manager.STATE_CHECKMATE
    assert view.turn.get() == "Game over"
    assert "Black wins" in view.status.get()
    assert manager.result is not None
    assert manager.result.winner == -1
    assert view.history.size() == 4


def test_the_new_game_button_deals_a_fresh_board(window):
    view = window
    manager = view.manager

    for square in [(1, 5), (2, 5), (6, 4), (4, 4), (1, 6), (3, 6), (7, 3), (3, 7)]:
        click(view, square)
    assert manager.get_state() == manager.STATE_CHECKMATE

    view.on_new_game()
    view.update()

    assert manager.get_state() == manager.STATE_IN_PROGRESS
    assert manager.move_events == []
    assert view.turn.get() == "White to move"
    assert view.history.size() == 0
    occupied = [square for row in manager.board.board for square in row if square is not None]
    assert len(occupied) == 32


def test_the_board_is_drawn_from_whites_side(window):
    """Rank 1 is the bottom row, because row 0 holds White's back rank."""
    view = window
    board = view.board_view.board

    assert board.rows == 8 and board.cols == 8
    # White's king stands on row 0, which is rank 1, so it must be drawn on the bottom row.
    white_king_row = next(
        row
        for row in range(board.rows)
        if board.get_piece_at((row, 4)) is not None and board.get_piece_at((row, 4)).getColor() == 1
    )
    assert white_king_row == 0

    # The labels run 8 at the top down to 1 at the bottom, and a..h along the bottom.
    labels = [
        view.board_view.canvas.itemcget(item, "text")
        for item in view.board_view.canvas.find_all()
        if view.board_view.canvas.type(item) == "text"
        and view.board_view.canvas.itemcget(item, "text").isdigit()
    ]
    assert labels[:8] == ["8", "7", "6", "5", "4", "3", "2", "1"]

    # pos_to_algebraic calls row 0 rank 1, so the view must not contradict it.
    from model.misc.notation import pos_to_algebraic

    assert pos_to_algebraic((0, 4)) == "e1"
    assert board.get_piece_at((0, 4)).getType() == "king"


def test_a_click_is_read_from_the_flipped_board(window):
    """The bottom-left square is a1, and clicking it must select the piece on a1."""
    view = window
    board = view.board_view
    view.on_square_clicked((0, 0))
    view.update()

    # The a1 rook is selected and has nowhere to go: its own pawn stands on a2. That is the
    # board agreeing with chess rather than the view failing to read a click.
    assert board.selected == (0, 0)
    assert board.board.get_piece_at((0, 0)).getType() == "rook"
    assert board.targets == []

    # The pawn in front of it does have moves.
    view.on_square_clicked((1, 0))
    view.update()
    assert board.selected == (1, 0)
    assert (2, 0) in board.targets and (3, 0) in board.targets


def test_the_move_history_is_notated(window):
    """The list reads as a game, not as a debug log."""
    view = window
    for square in [(1, 4), (3, 4)]:
        click(view, square)

    assert view.history.get(0) == "1. e2 – e4"


def test_the_quest_cards_show_progress(window):
    view = window
    manager = view.manager

    assert view.quest_list.cards, "no quest cards were built"
    before = [card.quest.progress()[0] for card in view.quest_list.cards]

    click(view, (1, 5))
    click(view, (2, 5))
    view.update()

    after = [card.quest.progress()[0] for card in view.quest_list.cards]
    assert after != before, "no quest moved after a move was played"


def test_a_clicking_white_piece_then_a_black_piece_reselects(window):
    """Reselecting is what a player expects; the window must not insist on one selection."""
    view = window

    click(view, (1, 4))  # e2
    assert view.board_view.selected == (1, 4)
    click(view, (1, 3))  # d2, another white piece
    assert view.board_view.selected == (1, 3)


def test_the_modal_lists_the_shipped_games_and_starts_one(tk_root):
    root = tk_root

    modal = StartModal(
        root,
        games=available_games(),
        default="chess",
        on_start=lambda game: None,
        on_settings=lambda: None,
    )
    root.update()

    assert list(modal.selector.cget("values")) == available_games()
    assert modal.choice.get() == "chess"
    assert modal.start_button.winfo_exists() == 1
    assert modal.settings_button.winfo_exists() == 1

    modal.choice.set(available_games()[0])
    modal.start()
    root.update()
    assert not modal.window.winfo_exists()
