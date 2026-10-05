"""What the checkers configuration declares, and what a played draughts game writes.

`games/checkers/__init__.py` composes two writers — the letter notation and the header — and
the naming the window draws the move history with. Which notations exist is the
configuration's answer: `GameManager.default_format` takes the first, `save_log` names its file
from it, and `Configuration.metadata` is how the header reaches the writers that ask for one.

**A finished game is played rather than assembled.** The record is walked move by move against
the moves the manager actually made, because a record pasted into a test is a record that can
be pasted in wrongly. **The refusal of `FEN` is a claim about the game, not a gap**:
`games/checkers/export/__init__.py` argues that English draughts has no position record and
that writing one to satisfy a writer would be inventing a notation.

**A configuration is a directory, so a copy of it brings its own writers with it.** That is
what the last test here is for: the module a writer class came from is the proof, exactly as it
is for the board's pieces.

**The numbering is the board's**, so every test here that mentions a square number uses
`tests/test_draughts_perft.py`'s independent derivation of the same arrangement to say which
square it means.
"""

import pathlib
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import pytest

from games.checkers.board import build_board, square_number
from games.checkers.export.letter import ExportLetter, NumberedNotation, move_text
from games.checkers.export.metadata import (
    BLACK_WON,
    DRAWN,
    TAG_ROSTER,
    WHITE_WON,
    ExportMetadata,
)
from model.game.configuration import load_configuration
from model.game.manager import GameManager, UnsupportedExportFormat
from model.game.move import Move
from model.game.rule import Result
from tests.test_draughts_perft import coordinates, square_of

# --- the numbering, which is the board's and the perft gate's at once


def test_the_board_numbers_its_squares_the_way_draughts_does():
    """One to four is White's back row, twenty-nine to thirty-two the crown row.

    Both ends and the count, because a numbering that starts at one and ends at thirty-two is
    not the same thing as the standard arrangement.

    Returns:
        None
    """
    assert square_number(0, 1) == 1
    assert square_number(0, 7) == 4
    assert square_number(7, 0) == 29
    assert square_number(7, 6) == 32

    numbered = {
        square_number(row, col) for row in range(8) for col in range(8) if (row + col) % 2 == 1
    }
    assert numbered == set(range(1, 33))


def test_the_board_numbering_is_the_numbering_the_perft_gate_derives():
    """Two independent derivations of the arrangement, asserted equal for all thirty-two squares.

    `tests/test_draughts_perft.py` derives the numbering from the geometry of the dark squares
    on purpose, so that the published counts it is gated against cannot be restated in terms
    of whatever the game happens to implement. This is the assertion that keeps the production
    numbering from drifting away from it.

    Returns:
        None
    """
    for square in range(1, 33):
        assert square_number(*coordinates(square)) == square
        assert square_of(*coordinates(square)) == square


def test_a_light_square_has_no_number_and_says_so():
    """A square no piece can stand on has no name in this game's numbering.

    Returns:
        None
    """
    with pytest.raises(ValueError, match="light square"):
        square_number(0, 0)

    with pytest.raises(ValueError, match="not on"):
        square_number(8, 1)


# --- the board's own column labels


def test_a_draughts_board_names_its_columns_with_square_numbers():
    """The window draws what the board says, so this is what a draughts player reads along the
    bottom edge: the numbers of the squares that column holds, not 1 to 8.

    Returns:
        None
    """
    board = build_board()

    assert board.file_label(0) == "5"
    assert board.file_label(1) == "1"
    assert board.file_label(7) == "4"
    assert [board.file_label(col) for col in range(8)] != [str(col + 1) for col in range(8)]


def test_the_column_labels_are_the_squares_the_board_actually_numbers():
    """Every label is a real square number of that column, and the first one from White's side.

    Returns:
        None
    """
    board = build_board()

    for col in range(board.cols):
        numbers = [square_number(row, col) for row in range(board.rows) if (row + col) % 2 == 1]
        assert board.file_label(col) == str(numbers[0])


# --- the letter notation


def test_a_quiet_move_is_written_with_a_hyphen_and_a_capture_with_a_cross():
    """The rulebook's two marks, asserted separately so neither is assumed.

    Returns:
        None
    """
    quiet = Move(coordinates(18), coordinates(22))
    capture = Move(coordinates(18), coordinates(25), captured_piece=object())

    assert move_text(quiet) == "18-22"
    assert move_text(capture) == "18x25"


def test_the_letter_writer_declares_one_notation_and_writes_it():
    """A writer writes the notations it declares, and reaches them however they are spelled.

    Returns:
        None
    """
    writer = ExportLetter()
    moves = [Move(coordinates(11), coordinates(15)), Move(coordinates(20), coordinates(24))]

    assert writer.formats() == ("Letter",)
    assert writer.export("Letter", moves=moves) == "1. 11-15 20-24"
    assert writer.export("letter", moves=moves) == "1. 11-15 20-24"
    assert writer.export(" Letter ", moves=moves) == "1. 11-15 20-24"


def test_a_capture_chain_is_one_move_written_once():
    """A chain of three jumps is one move the player made, so the record carries one entry for
    it, from where it started to where it ended.

    Returns:
        None
    """
    from games.checkers.moves import HopMove

    chain = HopMove(
        start_pos=coordinates(18),
        end_pos=coordinates(30),
        hops=(coordinates(22), coordinates(26), coordinates(30)),
        captures=(coordinates(23), coordinates(25), coordinates(27)),
        move_type="capture",
    )

    assert move_text(chain) == "18x30"
    assert ExportLetter().to_letter([chain]) == "1. 18x30"


def test_the_letter_record_numbers_its_turns_and_pairs_them():
    """Written the way a draughts score sheet is written: one number, then that turn's two moves.

    Returns:
        None
    """
    moves = [
        Move(coordinates(11), coordinates(15)),
        Move(coordinates(20), coordinates(24)),
        Move(coordinates(16), coordinates(19)),
    ]

    assert ExportLetter().to_letter(moves) == "1. 11-15 20-24 2. 16-19"


def test_the_letter_record_is_not_the_transcript_and_holds_no_position():
    """One move, three questions: the letter writer answers the first and refuses the others.

    Returns:
        None
    """
    writer = ExportLetter()
    moves = [Move(coordinates(11), coordinates(15))]

    assert writer.export("Letter", moves=moves) == "1. 11-15"

    with pytest.raises(UnsupportedExportFormat, match="Letter"):
        writer.export("FEN", board=build_board())

    with pytest.raises(UnsupportedExportFormat, match="Letter"):
        writer.export("Field-Field-Extra", moves=moves)


def test_a_game_with_no_moves_still_writes_an_empty_record():
    """A record of no moves is genuinely empty, which is not the same as refusing.

    Returns:
        None
    """
    assert ExportLetter().export("Letter", moves=[]) == ""


def test_the_draughts_naming_of_a_move_is_the_move_the_record_writes():
    """The move history and the transcript are one conversion, not two that agree today.

    Returns:
        None
    """
    notation = NumberedNotation()
    quiet = Move(coordinates(18), coordinates(22))
    capture = Move(coordinates(18), coordinates(25), captured_piece=object())

    assert notation.move_label(1, quiet) == "1. 18-22"
    assert notation.move_label(2, capture) == "2. 18x25"
    assert notation.square_name(coordinates(18)) == "18"


class _Person:
    """A stand-in for the `User` a `Player` is linked to."""

    def __init__(self, name="", username=""):
        """Record the two attributes a name is read from.

        Args:
            name: The person's name.
            username: The person's handle.
        """
        self.name = name
        self.username = username


class _Side:
    """A stand-in for the `Player` that owns one side of a game."""

    def __init__(self, color, user=None):
        """Record which side this is and who played it.

        Args:
            color: The side, as 1 or -1.
            user: The person playing it, or None for nobody this program knows.
        """
        self.color = color
        self.user = user

    def getColor(self):
        """Return the side.

        Returns:
            int: The side this player holds.
        """
        return self.color

    def getUser(self):
        """Return the person playing this side.

        Returns:
            _Person: The linked person, or None.
        """
        return self.user


def _sides(white: Optional[str] = "Ada", black: Optional[str] = "Grace") -> List[Any]:
    """Return the two sides of a game, with the names asked for.

    Args:
        white: The first side's name, or None for nobody this program knows.
        black: The second side's name, or None for nobody this program knows.

    Returns:
        List[Any]: Two stand-in sides, in the order the manager holds them.
    """
    return [
        _Side(1, _Person(name=white) if white else None),
        _Side(-1, _Person(name=black) if black else None),
    ]


# --- the metadata header


def test_the_header_says_who_played_when_and_how_the_game_ended():
    """Every field comes from the game, and the order is the roster's.

    Returns:
        None
    """
    began = datetime(2026, 3, 4, 17, 30)
    won = Result(kind="win", winner=1, reason="immobilised")
    values = ExportMetadata().header_values(players=_sides(), result=won, date=began)

    assert list(values) == list(TAG_ROSTER)
    assert values["White"] == "Ada"
    assert values["Black"] == "Grace"
    assert values["Date"] == "2026.03.04"
    assert values["Result"] == WHITE_WON


def test_a_draughts_result_is_written_the_way_a_score_sheet_writes_it():
    """Two points for a win and one each for a draw, which is not chess's `1-0`.

    Returns:
        None
    """
    won = Result(kind="win", winner=1, reason="immobilised")
    lost = Result(kind="loss", winner=-1, reason="immobilised")
    drawn = Result(kind="draw", reason="agreement")

    assert ExportMetadata().header_values(result=won)["Result"] == "2-1"
    assert ExportMetadata().header_values(result=lost)["Result"] == "1-2"
    assert ExportMetadata().header_values(result=drawn)["Result"] == DRAWN
    assert (WHITE_WON, BLACK_WON) == ("2-1", "1-2")


def test_a_field_the_game_has_nothing_to_say_about_is_left_out():
    """There is no `?` and no `Player 1`: a field with nothing behind it is not written.

    This is the one place draughts' header differs from chess'. A PGN header is the seven-tag
    roster and obliges a record to carry `Event`, `Site` and `Round` whatever the program
    knows, so `?` is PGN's own way of saying *not supplied*. No published roster obliges a
    draughts record to carry a tag it has nothing for, so this writer leaves it out.

    Returns:
        None
    """
    unfinished = ExportMetadata().header_values(players=_sides(black=None))

    assert "Black" not in unfinished
    assert "Result" not in unfinished
    assert "?" not in ExportMetadata().to_field_field_extra()

    for value in ExportMetadata().header_values(players=_sides()).values():
        assert "Player 1" not in value
        assert "Player 2" not in value
        assert "ChessWithQuests" not in value


def test_a_handle_is_used_when_a_player_has_no_name():
    """A user is a person whether or not anybody filled in their name.

    Returns:
        None
    """
    sides = [_Side(1, _Person(username="ada")), _Side(-1, _Person(name="  ", username="grace"))]

    assert ExportMetadata().header_values(players=sides)["Black"] == "grace"


def test_a_declared_field_is_the_field_that_is_written():
    """What a configuration knows about itself before the game is played is declared, and
    wins over anything derived.

    Returns:
        None
    """
    writer = ExportMetadata({"Event": "Club Championship", "Variant": "flying kings"})
    tags = writer.to_field_field_extra(players=_sides(), date=datetime(2026, 3, 4)).splitlines()
    names = [line.split(" ")[0] for line in tags]

    assert writer.get_header("Event") == "Club Championship"
    assert names == ["[Date", "[White", "[Black", "[Event", "[Variant"]
    assert tags[-2:] == ['[Event "Club Championship"]', '[Variant "flying kings"]']


def test_the_header_writer_declares_the_notation_the_diagram_draws():
    """*Field - Field - Extra* is the diagram's name for a header, and the declared spelling.

    Returns:
        None
    """
    writer = ExportMetadata()

    assert writer.formats() == ("Field-Field-Extra",)
    assert writer._writes("field-field-extra") is True
    assert '[White "Ada"]' in writer.export("field-field-extra", players=_sides())

    with pytest.raises(UnsupportedExportFormat, match="Field-Field-Extra"):
        writer.export("Letter")


# --- what the configuration declares


def test_the_checkers_configuration_offers_two_notations_and_leads_with_the_record():
    """The two this game has, in the order that makes the record the default.

    Order matters twice over: `default_format` takes the first, and `save_log` names its file
    from it, so a draughts game written without being asked for a notation is a `.letter`.

    Returns:
        None
    """
    from games.checkers import build_configuration

    configuration = build_configuration()
    offered = [name for writer in configuration.exporters for name in writer.formats()]

    assert offered == ["Letter", "Field-Field-Extra"]
    assert configuration.metadata in configuration.exporters
    assert isinstance(configuration.notation, NumberedNotation)


def test_a_draughts_game_written_without_being_asked_for_a_notation_is_a_letter_record():
    """And the file it is saved to is named for that, which is the extension following from
    the declaration rather than from a list written beside the writer.

    Returns:
        None
    """
    configuration = load_configuration("checkers")
    game = GameManager(configuration=configuration)

    assert game.default_format() == "Letter"
    assert game.notation.formats() == ("Letter",)


def test_the_configuration_hands_the_manager_the_same_header_it_offers_as_a_format():
    """Otherwise a game would be written with a header the configuration does not export.

    Returns:
        None
    """
    from games.checkers import build_configuration

    configuration = build_configuration()

    assert configuration.metadata is not None
    assert configuration.metadata in configuration.exporters
    assert type(configuration.metadata).__module__ == "games.checkers.export.metadata"


# --- a whole game, played rather than assembled


def test_a_finished_draughts_game_exports_in_both_its_notations():
    """A game played to a result through the manager, written out by both of its writers.

    The moves are the manager's own, so the square numbers in the record are the numbers of
    the squares the pieces actually stood on. The move list is walked position by position
    rather than compared against a written-out record, because a record pasted into a test is
    a record that can be pasted in wrongly.

    Returns:
        None
    """
    game = GameManager(configuration=load_configuration("checkers"))
    while game.get_result() is None:
        offered = game.move_validator.get_all_valid_moves(game.active_player, game.board)
        assert offered, "a side with no move has lost, so the game is over"
        move = sorted(offered, key=lambda candidate: (candidate.start_pos, candidate.end_pos))[0]
        assert game.make_move(move)
    result = game.finish_game()

    assert result is not None
    assert game.move_events

    written = [move_text(event.move) for event in game.move_events]
    record = game.transcript("Letter")
    for text in written:
        assert text in record

    took_something = [
        event.move
        for event in game.move_events
        if getattr(event.move, "captures", ()) or event.move.captured_piece is not None
    ]
    assert took_something, "a game this long takes something; the cross would go untested"

    quiet = [
        move_text(event.move) for event in game.move_events if event.move not in took_something
    ]
    assert all("x" not in text and "-" in text for text in quiet)
    assert all(text.count("x") == 1 for text in written if text not in quiet)

    header = game.transcript("Field-Field-Extra")
    assert '[Result "' in header
    assert header.count("[") == len(TAG_ROSTER)


def test_a_draughts_game_refuses_a_position_record_by_name():
    """There is no FEN for English draughts, so asking for one is answered rather than fudged.

    Returns:
        None
    """
    game = GameManager(configuration=load_configuration("checkers"))

    with pytest.raises(UnsupportedExportFormat, match="checkers exports"):
        game.transcript("FEN")


def test_a_saved_draughts_game_is_named_for_the_notation_it_was_written_in(tmp_path, monkeypatch):
    """`save_log` names the file from the declared format, so the extension is a consequence.

    Returns:
        None
    """
    game = GameManager(configuration=load_configuration("checkers"))
    game.make_move(
        sorted(
            game.move_validator.get_all_valid_moves(game.active_player, game.board),
            key=lambda candidate: (candidate.start_pos, candidate.end_pos),
        )[0]
    )

    # No path: the default is `logs/game-<moves>.<format>`, and the extension is the part
    # this test is about. A caller who names a file gets the name they asked for.
    monkeypatch.chdir(tmp_path)
    path = Path(game.save_log())

    assert path.suffix == ".letter"
    assert path.read_text(encoding="utf-8") == game.transcript("Letter")


def test_a_copied_checkers_configuration_writes_with_its_own_writers_and_its_own_naming(tmp_path):
    """A copy of the directory brings its own writers, its own naming and its own board with it.

    Everything here is imported relatively, so the proof that it is relative is the module a
    class came from: a writer loaded through `games.checkers` would say so, and one loaded
    through the copy says `_configuration_…` instead. An absolute
    `from games.checkers.export.letter import ExportLetter` in the copy's `build_exporters()`
    would load, look edited, and write the original's notation.

    Returns:
        None
    """
    import shutil

    from model.game.games import games_root

    games = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / "checkers",
        games / "house",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    configuration = load_configuration("house", root=str(games))

    assert configuration.exporters
    for writer in configuration.exporters:
        module = type(writer).__module__
        assert module.startswith("_configuration_"), type(writer).__name__
        assert ".export." in module, type(writer).__name__

    assert type(configuration.notation).__module__.startswith("_configuration_")
    assert type(configuration.board).__module__.startswith("_configuration_")
