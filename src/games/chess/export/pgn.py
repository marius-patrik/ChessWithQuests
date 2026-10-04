"""The chess game transcript, written as PGN text by a writer that belongs to chess.

PGN is chess's notation, so the writer that produces it lives here rather than in the engine.
The header comes from the `ExportMetadata` the manager hands down and the movetext from the
game's own moves, so the writer decides nothing about either: it is the format's arrangement
of what it is given, and `notes/object_model.md` section 7 places it beside the configuration
that uses it.

**The header is not built here.** A header is a format of its own — *Field - Field - Extra*,
which the diagram enumerates beside PGN — so this writer composes that writer rather than
holding a second copy of the roster. It passes on the fields it is given and adds no tag of
its own, which is what stops the two from drifting apart: a header written on its own and a
header inside a PGN are the same text produced by the same code.

There is no fallback header any more. The `'[Event "Casual Game"]\n[Result "*"]'` this replaces
was three facts invented at write time — an event nobody was playing, a site nobody was at —
and it was what a PGN was written as whenever the caller had no metadata to hand, which is
what `GameManager` did on every transcript. A writer handed a game and nothing else still
writes a header, and it is derived from that game.

The movetext is still destination squares rather than Standard Algebraic Notation. That is
real SAN's remaining half — piece disambiguation, promotion notation and check and mate
suffixes — and it is `SCRATCHPAD.md` §4.5 item 19's other half. It is recorded here rather
than fixed here, because a writer that grew SAN would be two notations in one class, which is
the thing the split into one writer per notation exists to prevent.
"""

from datetime import datetime
from typing import Any, List, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter

from .algebraic import pos_to_algebraic
from .metadata import ExportMetadata


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

    def to_pgn(
        self,
        moves: List[Any],
        metadata: Optional[ExportMetadata] = None,
        players: Optional[List[Any]] = None,
        result: Any = None,
        date: Optional[datetime] = None,
    ) -> str:
        """Export game moves and metadata to Portable Game Notation (PGN) text.

        Args:
            moves: List of played Move instances.
            metadata: The header writer the configuration declared. Optional, so the writer
                can be handed a game and nothing else — in which case a header is derived from
                that game rather than being left out.
            players: The players the game was played by, which is where the header's two names
                come from.
            result: The game's outcome, which is where the header's result comes from.
            date: When the game began, which is where the header's date comes from.

        Returns:
            str: The PGN text: the header, a blank line, and the moves.
        """
        header = metadata if metadata is not None else ExportMetadata()
        tags = header.header_values(players=players, result=result, date=date)
        headers = header.format_tags(tags)
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
        return f"{headers}\n\n{moves_text} {tags['Result']}".strip()

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as PGN text.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`, and optionally `metadata`, `players`, `result` and `date`.

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
        return self.to_pgn(
            kwargs.get("moves", []),
            kwargs.get("metadata"),
            kwargs.get("players"),
            kwargs.get("result"),
            kwargs.get("date"),
        )
