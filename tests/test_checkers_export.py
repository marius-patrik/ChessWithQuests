"""The draughts letter notation: a game written as the numbers it is played in.

`games/checkers/export/letter.py` holds `ExportLetter`, which writes a move as the departure
square, the rulebook's mark, and the arrival square — `18-22` for a quiet move and `18x25`
for a capture (FMJD Annex 1 article 8.2). `NumberedNotation` beside it is the same naming
offered to the window, so the move history and the transcript are one conversion rather than
two that agree today.

**The record is not a position.** `ExportLetter` refuses `FEN` by name, and
`games/checkers/export/__init__.py` argues why: the algebraic squares are chess's, the numbers
are a coordinate system rather than a position grammar, and a draughts position has no
halfmove clock or castling right to record. Answering `FEN` would be inventing a notation to
satisfy a caller.

**The numbering is the board's**, and the move history is drawn with it.
"""

import pytest

from games.checkers.board import build_board, square_number
from games.checkers.export.letter import ExportLetter, NumberedNotation, move_text
from model.game.manager import UnsupportedExportFormat
from model.game.move import Move
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
