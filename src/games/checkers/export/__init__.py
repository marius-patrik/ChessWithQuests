"""The checkers export: what a draughts game is written as, and what it is not.

Two formats belong to this game and both ship here:

- **Letter notation** — the moves as the square numbers draughts actually uses, one to
  thirty-two, with the long form `18-22` and the short `18x25` when a move takes something.
  `letter.py`.
- **The metadata header** — who played, when, and how the game ended, as `[Name "Value"]`
  pairs derived from the game. `metadata.py`.

What this game deliberately has **no** format for is a position record. There is no FEN for
English draughts: the algebraic naming `e4` is chess's, the square numbers are a coordinate
system and not a position grammar, and a draughts position has no halfmove clock or castling
right to record. Writing one anyway would be inventing a notation in order to satisfy a
writer, which is the opposite of what the writers are for. `ExportLetter` therefore *refuses*
`FEN` by name rather than answering it: `GameManager.writer_for("FEN")` for this configuration
raises `UnsupportedExportFormat`, and a draughts game that has no position record is a
statement about the game rather than a gap in the writer list.

The numbering the letters write in is not declared here either. It is the board's, counted
from the squares the game is played on, and `letter.py` asks `games/checkers/board.py` for it
rather than keeping a second table that could disagree with the perft gate's.

Which notations a game can write is the configuration's answer, so the engine holds only the
`ExportWriter` protocol both of these answer and `notes/object_model.md` section 7 places the
writers beside the configuration that uses them. `build_exporters()` below composes this
directory, so adding a notation is one file in it and nothing else: a writer this directory
holds is offered whether or not `PREFERRED` names it.

**`PREFERRED` is an order, not a roster.** The letter notation leads, so a draughts game
written without being asked for a notation is written as square numbers and saved as `.letter`.
That is a preference about which writer is first, and it is allowed to do nothing else — a
writer `PREFERRED` does not name is still composed and still offered, last. A name in
`PREFERRED` that this directory does not declare is a refusal instead.
"""

import sys
from typing import Any, List, Optional, Tuple, Type

from model.game.configuration import compose_section
from model.misc.export_writers import ExportWriter

from .letter import ExportLetter
from .metadata import ExportMetadata

#: The writers in the order they are preferred, by class rather than by name. The letter
#: notation leads, so a draughts game written without being asked for a notation is written as
#: square numbers and saved as `.letter`, and the header follows it.
PREFERRED: Tuple[Type[ExportWriter], ...] = (ExportLetter, ExportMetadata)


def build_exporters(notes: Optional[List[str]] = None) -> List[Any]:
    """Build the export writers draughts offers, in the order they are preferred.

    Args:
        notes: A list to record one line in per file that declares no writer, so the settings
            form can name it. Defaults to None, which discards them.

    Returns:
        List[Any]: One writer per `ExportWriter` subclass the files in `export/` declare. Every
        one of them is here; `PREFERRED` decides only which leads, and a writer the preference
        does not name follows it.

    Raises:
        ConfigurationSourceError: If a name in `PREFERRED` is a writer this directory does not
            declare, which is the preference and the directory disagreeing.
    """
    return compose_section(sys.modules[__name__], notes, PREFERRED)
