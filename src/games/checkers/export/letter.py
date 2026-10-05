"""The draughts letter notation: a game written in the numbers it is played in.

A draughts player does not say `e4`, because this game has no `e4`. This game says 18, and it
says 22, and the whole of its notation is those two numbers and the mark between them:

    18-22     a move that takes nothing, from 18 to 22
    18x25     a move that takes something, from 18 to 25

The hyphen and the cross are the rulebook's own (`FMJD` Annex 1 article 8.2.2 and 8.2.3: the
starting square, then the arrival square, separated by a hyphen for a simple move and by a
cross for a capture), and this writer writes nothing else. There is no piece letter, because
a draughts move names its own piece by naming the square it stood on; there is no promotion
suffix, because a man that reaches the far row is crowned and keeps playing rather than
becoming a piece with another name; there is no check or mate, because this game has no
check. The one thing that is *not* written that a draughts record can carry is the route of a
capture chain: the rulebook's convention names the arrival square, and a chain that arrives on
the same square by two routes is two moves that read alike. That is a defect of the
notation rather than of this writer, it is recorded here rather than fixed here, and it is
the kind of thing `PDN`'s disambiguating long form exists for.

**The numbering is the board's.** `square_number` in `games/checkers/board.py` counts the
played squares in board order, and this module imports it relatively rather than repeating
it. A second table of draughts numbers would be a second thing to keep right, and the
perft gate in `tests/test_draughts_perft.py` already holds this one against the published
counts that are written in the same numbering.

`NumberedNotation` is the same naming offered to the window, so the move history and the
transcript are one conversion rather than two that agree today. Chess offers its naming as
`AlgebraicNotation` for the same reason, and `notes/object_model.md` section 7 registers the
seam both of them fill.

A quiet move and a capture are the whole of the grammar. That is why this writer needs to
know nothing about pieces, kings, or positions: the numbers carry all of it.
"""

from typing import Any, List, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter

from ..board import square_number

#: What a move that takes nothing is written with.
QUIET = "-"

#: What a move that takes something is written with.
CAPTURE = "x"


def square_label(position: Tuple[int, int]) -> str:
    """Return the name this game gives one square.

    Args:
        position: Tuple of (row, col) 0-indexed coordinates.

    Returns:
        str: The square's number as a string, for example `18`.
    """
    return str(square_number(position[0], position[1]))


def move_text(move: Any) -> str:
    """Write one move in this game's notation.

    The mark is the move's own: a move that took something is written with a cross and one
    that took nothing with a hyphen. The piece is not asked about, because the two squares
    already say which piece moved.

    Args:
        move: The `Move` to write.

    Returns:
        str: The move as draughts writes it, for example `18-22` or `18x25`.
    """
    taken = getattr(move, "captured_piece", None) is not None or bool(getattr(move, "captures", ()))
    mark = CAPTURE if taken else QUIET
    return f"{square_label(move.start_pos)}{mark}{square_label(move.end_pos)}"


class NumberedNotation:
    """The draughts naming of a move, offered to whoever has to draw it.

    A configuration declares one of these and the window asks it rather than computing a
    naming of its own, which is what keeps the move history and the transcript agreeing: both
    are the same conversion, and a variant that renames its squares gets its own naming in
    both places without either the view or the engine naming a game.
    """

    def square_name(self, position: Tuple[int, int]) -> str:
        """Return the name of one square.

        Args:
            position: Tuple of (row, col) 0-indexed coordinates.

        Returns:
            str: The square's number as a string, for example `18`.
        """
        return square_label(position)

    def move_label(self, number: int, move: Any) -> str:
        """Return the text the move history lists a move as.

        Args:
            number: The move's number in the game, counted from one.
            move: The `Move` to label.

        Returns:
            str: The number, and the move written exactly as the transcript writes it.
        """
        return f"{number}. {move_text(move)}"


class ExportLetter(ExportWriter):
    """Writes a game's moves as a draughts game record."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        The declared spelling is `Letter`, which is the diagram's own word for the notation
        whose squares are named by a letter and a number (`notes/reference_diagram.md`, "The
        `ChessNotationWriter` format list"). Chess declares the same format as `Algebraic`,
        because that is the name its module and its naming already carry; here the squares are
        numbered rather than lettered, and the diagram's word is the one nothing else in this
        directory contradicts.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("Letter",)

    def to_letter(self, moves: List[Any]) -> str:
        """Write a list of moves as a draughts game record.

        Args:
            moves: The played `Move` instances, in the order they were played.

        Returns:
            str: The moves numbered by turn and paired, two to a turn and one where the game
            ended after the first player's move.
        """
        played = list(moves or [])
        turns: List[str] = []
        for index in range(0, len(played), 2):
            number = (index // 2) + 1
            written = move_text(played[index])
            if index + 1 < len(played):
                written = f"{written} {move_text(played[index + 1])}"
            turns.append(f"{number}. {written}")
        return " ".join(turns)

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as a draughts game record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`.

        Returns:
            str: The game as a record of square numbers.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a game with nothing to say.
                It also refuses `FEN`, because there is no position record for this game to
                write — see this package's docstring for why that is a fact about English
                draughts rather than a gap in this writer.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_letter(kwargs.get("moves", []))


__all__ = [
    "CAPTURE",
    "QUIET",
    "ExportLetter",
    "NumberedNotation",
    "move_text",
    "square_label",
]
