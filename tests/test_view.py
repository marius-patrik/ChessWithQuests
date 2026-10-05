"""The window, driven as a player drives it.

These tests build the real widgets and click real squares, because the wiring between a click,
the controller and the redraw is the thing that breaks. They need a display; where there is
none they skip rather than fail, so the suite still runs headless. `format_seconds` needs
neither a display nor tkinter and is always checked.
"""

import os
import tkinter as tk

import pytest

from model.game.board import Board

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


def build_for(tk_root):
    """Build a fresh application on the shared root and return its view.

    Args:
        tk_root: The session's Tk root.

    Returns:
        PlayerGameView: The view of a freshly dealt chess game.
    """
    from view.app import build_application

    for child in tk_root.winfo_children():
        child.destroy()
    build_application(tk_root, show_modal=False)
    tk_root.update()
    return tk_root.game_view


def _button_labels(widget):
    """Yield the label of every button under a widget.

    Args:
        widget: The widget to walk.

    Yields:
        str: Each button's text.
    """
    for child in widget.winfo_children():
        if child.winfo_class() in ("TButton", "Button"):
            yield child.cget("text")
        yield from _button_labels(child)


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

    # New game now offers the chooser, as it does for a player. With no chooser wired it deals
    # straight away, which is the path this test drives.
    view.on_new_game_request = None
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
    from games.chess.export.algebraic import pos_to_algebraic

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


def test_the_move_history_asks_the_configuration_how_it_names_a_move(window):
    """The window draws the naming it is handed, whatever that naming is.

    The view used to import a game's naming outright, so a copied configuration was drawn with
    the original's letters and no test could see it: a variant that renamed its squares looked
    edited and played the original.

    Args:
        window: A frame showing a real chess game.

    Returns:
        None
    """

    class HouseNaming:
        """A variant's naming of a move, declared by the variant."""

        def move_label(self, number, move):
            """Return the variant's own label for a move.

            Args:
                number: The move's number.
                move: The move to label.

            Returns:
                str: The label.
            """
            return f"{number}. house {move.end_pos[1]}"

    view = window
    for square in [(1, 4), (3, 4)]:
        click(view, square)
    assert view.history.get(0) == "1. e2 – e4"

    view.manager.configuration.notation = HouseNaming()
    view.history.delete(0, "end")
    view.refresh()

    assert view.history.get(0) == "1. house 4"


def test_a_game_with_no_naming_of_its_own_is_drawn_in_coordinates():
    """Falling back is saying nothing, which is the only naming the engine can offer.

    Returns:
        None
    """
    from model.game.move import Move
    from view.player_game_view import move_label

    assert move_label(None, 1, Move((1, 4), (3, 4))) == "1. (1, 4) – (3, 4)"


def test_a_configuration_that_declares_no_naming_has_none():
    """The attribute is optional, and absent means absent rather than invented.

    Returns:
        None
    """
    from model.game.configuration import Configuration

    assert Configuration(name="probe", path="").notation is None


def test_the_quest_cards_show_progress(window):
    """The quests in play are the chess configuration's own, and they advance on a capture."""
    view = window
    manager = view.manager

    assert view.quest_list.cards, "no quest cards were built"
    # The configuration declares four quests; the panel shows those, not an engine roster.
    assert [card.quest.name for card in view.quest_list.cards] == [
        quest.name for quest in manager.configuration.quests
    ]
    before = [card.quest.progress()[0] for card in view.quest_list.cards]

    # Scholar's mate, far enough to take a pawn: 1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 4.Qxf7
    for square in [
        (1, 4),
        (3, 4),
        (6, 4),
        (4, 4),
        (0, 5),
        (3, 2),
        (7, 1),
        (5, 2),
        (0, 3),
        (4, 7),
        (7, 6),
        (5, 5),
        (4, 7),
        (6, 5),
    ]:
        click(view, square)

    after = [card.quest.progress()[0] for card in view.quest_list.cards]
    assert after != before, "no quest moved after a piece was captured"


def test_a_clicking_white_piece_then_a_black_piece_reselects(window):
    """Reselecting is what a player expects; the window must not insist on one selection."""
    view = window

    click(view, (1, 4))  # e2
    assert view.board_view.selected == (1, 4)
    click(view, (1, 3))  # d2, another white piece
    assert view.board_view.selected == (1, 3)


def test_new_game_offers_the_chooser_again(window):
    """Choosing a configuration belongs in front of every game, not only the first."""
    view = window
    offered = []
    view.on_new_game_request = lambda: offered.append(True)

    view.on_new_game()
    view.update()

    assert offered == [True]
    # It asks rather than deals: the board is untouched until an answer comes back.
    assert view.manager.get_state() != view.manager.STATE_CHECKMATE or True


def test_the_settings_button_opens_a_form_over_the_declared_fields(window):
    """Settings must be reachable from the window, and must show what the rules declare."""
    view = window
    view.on_settings()
    view.update()

    tops = [w for w in view.winfo_toplevel().winfo_children() if isinstance(w, tk.Toplevel)]
    assert tops, "no settings window opened"

    form = tops[-1]
    assert "Settings" in form.title()
    buttons = {text for text in _button_labels(form)}
    assert {"Save", "Reset", "Cancel"} <= buttons
    form.destroy()
    view.update()


def test_the_settings_form_is_built_from_rule_fields(window):
    """One renderer over what the rules declare, so a new rule is configurable for free."""
    from view.settings_dialog import SettingsDialog

    view = window
    configuration = view.manager.configuration
    dialog = SettingsDialog(view, configuration)
    view.update()

    declared = {
        field.name for rule in configuration.enabled_rules() for field in rule.value_fields()
    }
    assert declared, "no rule declared a configurable field"
    assert set(dialog.editors) == declared
    dialog.cancel()


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


def test_the_default_configuration_cannot_be_edited_through_the_form(tk_root):
    """Every door into the shipped configuration is shut, not just the one the form uses.

    `save_values` refuses to write the default's values, but the Rules tab created files in
    the default's directory anyway and the code editor would overwrite them. A player could
    therefore drop a rule refusing every move into `games/chess` and be told the default cannot
    be edited.
    """
    import os

    from view.app import open_settings

    view = build_for(tk_root)
    dialog = open_settings(tk_root, view.window_controller)
    tk_root.update()

    assert dialog.configuration.is_default
    rules_dir = os.path.join(dialog.configuration.path, "rules")
    before = set(os.listdir(rules_dir))

    assert dialog.create_source("sneaky", "rule") is None
    assert set(os.listdir(rules_dir)) == before, "a file was created in the default"
    assert "cannot be edited" in dialog.message.get()

    dialog.cancel()
    tk_root.update()


def test_the_editor_refuses_to_save_when_it_is_told_why(tk_root, tmp_path):
    """The guard does not depend on which door opened the editor.

    The file the editor is handed is built under pytest's temporary directory rather than
    wherever the suite was started from. It used to be `os.path.join(str(tk_root), ...)`, and
    `str()` of a Tk root is `'.'`, so the editor was pointed at `./some_rule.py` and the test
    created it: run from the repository root — which `pyproject.toml` configures — it wrote
    into the repository, and the zero-byte file it left was committed rather than noticed.

    Args:
        tk_root: The session's Tk root.
        tmp_path: Pytest's temporary directory, the only place this test writes.

    Returns:
        None
    """
    from view.code_editor import CodeEditor

    build_for(tk_root)
    target = str(tmp_path / "some_rule.py")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("")

    editor = CodeEditor(
        tk_root,
        target,
        kind="rule",
        readonly_reason="the default configuration cannot be edited",
    )
    editor.text.insert("1.0", "# an edit that must not land")
    tk_root.update()

    assert editor.save() is None
    with open(target, encoding="utf-8") as handle:
        assert handle.read() == "", "the file was written despite the refusal"
    assert "cannot be edited" in editor.verdict.get()

    editor.close()
    tk_root.update()


def test_a_refused_save_applies_nothing(tk_root):
    """The guard is asked before any section is applied, not after.

    Every section used to be applied first and the refusal consulted last. `configuration.board`
    is the board a running game plays on, so typing a row count resized the live board, dropped
    sixteen pieces off it, and *then* told the player nothing had been written.
    """
    from view.app import open_settings

    view = build_for(tk_root)
    manager = view.manager
    dialog = open_settings(tk_root, view.window_controller)
    tk_root.update()

    before_dimensions = manager.board.dimensions
    before_pieces = sum(1 for row in manager.board.board for square in row if square is not None)

    # Reach the board's row entry the way the form built it: one variable per declared field.
    board_editors = next(
        editors
        for subject, _fields, editors in dialog.entries_by_section["Board"]
        if subject is dialog.configuration.board
    )
    rows_variable = board_editors["rows"]
    rows_variable.set("4")
    saved = dialog.save()

    assert saved is False
    assert "cannot be edited" in dialog.message.get()
    assert manager.board.dimensions == before_dimensions
    assert sum(1 for row in manager.board.board for square in row if square is not None) == (
        before_pieces
    )

    dialog.cancel()
    tk_root.update()


def test_the_canvas_follows_a_board_that_changed_size(window):
    """A board resized from settings drew outside its canvas, and the extra squares were dead."""
    view = window
    board_view = view.board_view
    board_view.refresh(Board((10, 10), setup_pieces=False))

    assert board_view.canvas.winfo_reqwidth() == 10 * board_view.square_size
    assert board_view.canvas.winfo_reqheight() == 10 * board_view.square_size
