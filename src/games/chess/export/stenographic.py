"""The chess coordinate record, written by a writer that belongs to chess.

The stenographic record is a coordinate pair per move — the squares each move starts on and
ends on, in chess's own algebraic naming. The naming is chess's, so it is imported relatively
from `algebraic.py` beside this file: an absolute `games.chess.…` import would load the
original's naming when this directory is copied into a variant, which is exactly the failure
`tests/test_configuration_copying.py` exists to catch.

The public name of the notation is `Stenographic`, in that spelling. It used to be declared
`"Stenographic"` and dispatched as `"STENOGRAPHIC"`, so the two disagreed and the dispatch was
a second, private spelling of a name callers could already see. This writer declares one
spelling and answers the notation however the caller spells it — `GameManager.writer_for`
matches without regard to case, and `tests/test_game_loop.py` asks for `Stenographic` by name.
"""

from typing import Any, List, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter

from .algebraic import pos_to_algebraic


class ExportStenographic(ExportWriter):
    """Writes a game's moves as a record of coordinate pairs."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("Stenographic",)

    def to_stenographic(self, moves: List[Any]) -> str:
        """Write a list of moves as coordinate pairs.

        Args:
            moves: List of Move instances with start_pos and end_pos.

        Returns:
            str: Space-delimited string of concatenated coordinate pairs.
        """
        tokens = []
        for m in moves:
            start = pos_to_algebraic(m.start_pos)
            end = pos_to_algebraic(m.end_pos)
            tokens.append(f"{start}{end}")
        return " ".join(tokens)

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as a coordinate record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`.

        Returns:
            str: The moves as coordinate pairs.

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
        return self.to_stenographic(kwargs.get("moves", []))
