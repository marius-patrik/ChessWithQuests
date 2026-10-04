"""The chess game transcript, written as PGN text by a writer that belongs to chess.

PGN is chess's notation, so the writer that produces it lives here rather than in the engine.
The header comes from the `MetadataWriter` the manager hands down and the movetext from the
game's own moves, so the writer decides nothing about either: it is the format's arrangement
of what it is given, and `notes/object_model.md` section 7 places it beside the configuration
that uses it.

The record this writes has two recorded defects, which moving it does not fix and does not
hide: the movetext is destination squares rather than Standard Algebraic Notation, and the
header falls back to placeholders when a caller passes no metadata. Both belong to
`SCRATCHPAD.md` §4.1 and to planned PR 19; neither is a reason to keep one writer switching
on a format-name string.
"""

from typing import Any, List, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter
from model.misc.metadata import MetadataWriter

from .algebraic import pos_to_algebraic


class ExportPGN(ExportWriter):
    """Writes a game's moves and its header as PGN text."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("PGN",)

    def to_pgn(self, moves: List[Any], metadata: Optional[MetadataWriter] = None) -> str:
        """Export game moves and metadata to Portable Game Notation (PGN) text.

        Args:
            moves: List of played Move instances.
            metadata: MetadataWriter instance providing the header tags. Optional, so the
                writer can be handed a game and nothing else.

        Returns:
            str: The PGN text: the header, a blank line, and the moves.
        """
        headers = (
            metadata.format_pgn_headers() if metadata else '[Event "Casual Game"]\n[Result "*"]'
        )
        move_pairs = []
        for i in range(0, len(moves), 2):
            move_num = (i // 2) + 1
            w_end = getattr(moves[i], "end_pos", None)
            w_move = pos_to_algebraic(w_end) if w_end is not None else str(moves[i])
            if i + 1 < len(moves):
                b_end = getattr(moves[i + 1], "end_pos", None)
                b_move = pos_to_algebraic(b_end) if b_end is not None else str(moves[i + 1])
                move_pairs.append(f"{move_num}. {w_move} {b_move}")
            else:
                move_pairs.append(f"{move_num}. {w_move}")

        moves_text = " ".join(move_pairs)
        result = metadata.get_header("Result", "*") if metadata else "*"
        return f"{headers}\n\n{moves_text} {result}".strip()

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as PGN text.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`, and optionally `metadata`.

        Returns:
            str: The game as PGN text.

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
        return self.to_pgn(kwargs.get("moves", []), kwargs.get("metadata"))
