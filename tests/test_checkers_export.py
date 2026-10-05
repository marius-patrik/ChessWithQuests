"""The draughts header: who played, when, and how it ended.

`games/checkers/export/metadata.py` holds `ExportMetadata`, which writes the game's own facts
as `[Name "Value"]` pairs derived at write time — the two names from the users who played, the
date from the day the game began, the result from the outcome the rules reached.

**There is no placeholder string here and no `?`**, and that is the one place this header
differs from chess's. A PGN header *is* the seven-tag roster and obliges a record to carry
`Event`, `Site` and `Round` whatever the program knows, so `?` is PGN's own way of saying *not
supplied* — a claim rather than an invention. No published roster obliges an English draughts
record to carry a tag it has nothing for, so this writer leaves the field out instead. Its
result is written the way a draughts score sheet writes it, `2-1`, `1-2` or `2-2`, rather than
chess's `1-0`.

**The naming of a square is the board's**, so every test here that mentions one uses
`tests/test_draughts_perft.py`'s independent derivation of the same arrangement to say which
square it means.
"""

from datetime import datetime
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
from model.game.manager import UnsupportedExportFormat
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
