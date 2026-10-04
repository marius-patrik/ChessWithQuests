"""Algebraic coordinate conversion: the chess naming of the squares.

`e4` is a chess name for a square, and it belongs to chess. The engine deals in `(row, col)`
pairs, and this is the one place that knows a column is a letter and a row is counted from
White's side. A game whose board is not eight files wide has no such naming, so it writes
nothing here — which is what "a game with no FEN representation has no FEN exporter" means in
`notes/object_model.md`.

Only the letters `a` to `h` and the single-digit ranks of a chess board are handled. That is
deliberate rather than merely convenient: `algebraic_to_pos` reads the rank as
`int(algebraic[1])`, which is the whole reason this conversion cannot describe a board of any
other width, and pretending otherwise would move the defect rather than remove it.

`AlgebraicNotation` is the same naming offered as something the window may ask. It is how a
move is labelled in the move history, and it is declared by the configuration rather than
imported by the view: a window that reached into `games/chess` for a naming would draw a
copied configuration's game with the original's letters, and nothing would say so.

`ExportAlgebraic` writes a whole game in that naming, as a notation of its own. The diagram's
`ChessNotationWriter` box lists *letter* among the formats it writes (`notes/reference_diagram.md`
section "The `ChessNotationWriter` format list"), and a naming offered to the window is not a
record anybody can save. The declared spelling is `Algebraic` rather than the diagram's *letter*
because that is the name this directory, this class and the configuration's `notation` already
carry; *letter* is what chess calls the same thing, and the two are one format rather than two.

The record it writes is the algebraic one, which is not the Standard Algebraic Notation PGN
carries and not the coordinate pair the stenographic record carries. One move is its two parts
in this order: what moved, and where it went.

    <piece letter?> x? <destination>[=<promoted piece>]
    <piece letter> is absent for a pawn, which is the piece that needs no letter.
    x          marks a move that took something.
    O-O        and O-O-O are castling, which names no square at all.
    =<letter>  names the piece a promotion produced.

So `1. e4 e5 2. Nf3 Nc6 3. exd5 O-O` is a record of the same game SAN would write, and it is a
different record: there is no check or mate suffix and no disambiguation between two identical
pieces that can both reach the square, because neither belongs to the algebraic notation and both
belong to PGN's. Those are `SCRATCHPAD.md` §4.5 item 19's other half, and leaving them out here
is what keeps this format from quietly becoming PGN written badly.
"""

from typing import Any, List, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter


def file_letter(col: int) -> str:
    """Return the letter chess names a file by.

    A board is told the name of each of its columns rather than computing one: the engine's
    `Board.file_label` numbers them, and this is what chess's board answers instead. Keeping
    the letter here rather than in the board is what stops the naming being written twice.

    Args:
        col: The file's 0-indexed number.

    Returns:
        str: The file's letter, so column 0 is `a`.
    """
    return chr(ord("a") + col)


def pos_to_algebraic(position: Tuple[int, int]) -> str:
    """Convert a (row, col) coordinate tuple to chess algebraic notation (e.g. (0, 4) -> 'e1').

    Args:
        position: Tuple of (row, col) 0-indexed coordinates. Row 0 is White's first rank.

    Returns:
        str: Algebraic string notation (e.g. 'e4').
    """
    row, col = position
    return f"{file_letter(col)}{row + 1}"


def algebraic_to_pos(algebraic: str) -> Tuple[int, int]:
    """Convert an algebraic notation coordinate string to a 0-indexed (row, col) tuple.

    Args:
        algebraic: Coordinate string (e.g. 'e4', 'a1').

    Returns:
        Tuple[int, int]: Tuple of (row, col) 0-indexed coordinates.
    """
    col = ord(algebraic[0].lower()) - ord("a")
    row = int(algebraic[1]) - 1
    return (row, col)


class AlgebraicNotation:
    """The chess naming of a move, offered to whoever has to draw it.

    A configuration declares one of these and the window asks it rather than computing a
    naming of its own. That is what keeps the move history and the transcript agreeing: both
    are the same conversion, and a variant that renames its squares gets its own naming in
    both places without either the view or the engine naming a game.
    """

    def square_label(self, position: Tuple[int, int]) -> str:
        """Return the name of one square.

        Args:
            position: Tuple of (row, col) 0-indexed coordinates.

        Returns:
            str: The square's algebraic name, e.g. `e4`.
        """
        return pos_to_algebraic(position)

    def move_label(self, number: int, move: Any) -> str:
        """Return the text the move history lists a move as.

        Args:
            number: The move's number in the game, counted from one.
            move: The `Move` to label.

        Returns:
            str: The number, and the move's two squares as chess names them.
        """
        return (
            f"{number}. {self.square_label(move.start_pos)}" f" – {self.square_label(move.end_pos)}"
        )


class ExportAlgebraic(ExportWriter):
    """Writes a game's moves as an algebraic record, one numbered move per turn."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("Algebraic",)

    @staticmethod
    def _piece_letter(piece: Any) -> str:
        """Return the letter chess names a piece by, in the case the record uses.

        The letter is the piece's own, read from the character it declares for a position
        record, so a piece that declares none has no letter here either.

        Args:
            piece: The piece that moved.

        Returns:
            str: The piece's letter in upper case, or an empty string when the piece is a pawn
            — the one piece the algebraic notation names by its destination alone.
        """
        if piece is None or piece.getType() == "pawn":
            return ""
        get_fen = getattr(piece, "getFen", None)
        letter = get_fen() if callable(get_fen) else None
        return str(letter).upper() if letter else ""

    def to_algebraic(self, moves: List[Any]) -> str:
        """Write a list of moves as an algebraic record.

        Args:
            moves: The played `Move` instances, in the order they were played.

        Returns:
            str: The moves numbered by turn and paired, two to a turn and one where the game
            ended after the first player's move.
        """
        played = list(moves or [])

        def token(move: Any) -> str:
            # `Move.move_type` is the engine's word for the move, and castling is the one kind
            # that names no square: it is a king's two-square walk and a rook's, and the record
            # says `O-O` rather than describing either.
            if move.move_type.startswith("castling"):
                return "O-O-O" if "queen" in move.move_type else "O-O"
            capture = "x" if move.captured_piece is not None else ""
            written = f"{self._piece_letter(move.piece)}{capture}{pos_to_algebraic(move.end_pos)}"
            if move.promotion_piece is not None:
                written = f"{written}={self._piece_letter(move.promotion_piece)}"
            return written

        turns: List[str] = []
        for index in range(0, len(played), 2):
            number = (index // 2) + 1
            written = token(played[index])
            if index + 1 < len(played):
                written = f"{written} {token(played[index + 1])}"
            turns.append(f"{number}. {written}")
        return " ".join(turns)

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as an algebraic record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`.

        Returns:
            str: The game as an algebraic record.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a game with nothing to say.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_algebraic(kwargs.get("moves", []))
