"""The chess position record, written by a writer that belongs to chess.

FEN is chess's notation, so the writer that produces it lives here rather than in the engine.
Which notations a game can write is the configuration's answer — `notes/object_model.md`
section 7 places each format's writer beside the configuration that uses it, and the engine
keeps only the `ExportWriter` protocol every one of them answers. Adding a notation is a file
in this directory and one line in `games/chess/__init__.py`, and no engine change.

The writer holds no piece knowledge at all. A piece declares the character it is written as,
and a piece that declares none has no place in a position record, which is said out loud
rather than guessed at: the table this replaced wrote an unrecognised piece as a pawn, so a
game with an unfamiliar piece produced a well-formed record that lied about the position and
nothing in the record could reveal it.
"""

from typing import Any, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter


class ExportFEN(ExportWriter):
    """Writes a board as a Forsyth-Edwards position record."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("FEN",)

    @staticmethod
    def _fen_letter(piece: Any) -> str:
        """Return the character a piece declares for a position record.

        Args:
            piece: The piece being written.

        Returns:
            str: The piece's declared letter, in lower case.

        Raises:
            ValueError: If the piece declares no character. A piece with nothing to say about
                a position record has no position record, and writing it as something else
                would be a lie about the position.
        """
        get_fen = getattr(piece, "getFen", None)
        letter = get_fen() if callable(get_fen) else None
        if not letter:
            get_type = getattr(piece, "getType", None)
            name = get_type() if callable(get_type) else None
            raise ValueError(
                f"a piece of type {name!r} declares no character for a position record, "
                "so this position cannot be written"
            )
        return str(letter).lower()

    def to_fen(self, board: Any, active_color: int = 1) -> str:
        """Convert board state to Forsyth-Edwards Notation (FEN) string.

        Args:
            board: Board instance. Its rows and cols decide how many ranks and files the
                record carries, so a board of any size serialises.
            active_color: Active side color (1 for White, -1 for Black).

        Returns:
            str: The position record.

        Raises:
            ValueError: If a piece on the board declares no character for a position record.
                Nothing is guessed: an undeclared piece has no place in a position record,
                and a record that quietly called it a pawn would be wrong in a way no reader
                could see.
        """
        ranks = []
        for r in range(board.rows - 1, -1, -1):
            empty = 0
            rank_str = ""
            for c in range(board.cols):
                piece = board.get_piece_at((r, c))
                if piece is None:
                    empty += 1
                else:
                    if empty > 0:
                        rank_str += str(empty)
                        empty = 0
                    char = self._fen_letter(piece)
                    rank_str += (
                        char.upper()
                        if (piece.getColor() == 1 or piece.getColor() == "white")
                        else char.lower()
                    )
            if empty > 0:
                rank_str += str(empty)
            ranks.append(rank_str)

        board_fen = "/".join(ranks)
        turn = "w" if active_color == 1 else "b"
        return f"{board_fen} {turn} - - 0 1"

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the board as a position record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `board`, and optionally `active_color`.

        Returns:
            str: The board as a position record.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a board with nothing on it.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_fen(kwargs["board"], kwargs.get("active_color", 1))
