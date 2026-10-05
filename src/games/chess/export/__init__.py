"""The chess export: one file per notation the diagram's writer box enumerates.

Five notations ship here, one writer each: the transcript as PGN, the moves in the algebraic
naming, the game's own header record, the position as FEN, and the moves as coordinate pairs.
Which notations a game can write is the configuration's answer, so the engine holds only the
protocol every one of them answers and a variant is a directory that composes its own.

Adding a notation is one file in this directory. It is composed because it is a file here, not
because anybody listed it: `build_exporters()` below hands this package to
`model.game.configuration.compose_section`, which builds one writer per `ExportWriter` subclass the
files here declare.

**`PREFERRED` is an order, not a roster.** `GameManager.default_format` takes the first format the
first writer declares and `save_log` names its file from it, so a chess game written without being
asked for a notation is written as PGN and saved as `.pgn`. The preference says so, and it is allowed
to do nothing else: a writer this directory holds and `PREFERRED` does not name is still composed
and still offered, last. What is refused is a name in `PREFERRED` that this directory does not
declare, because a preference for a writer that is not there is how a directory and its declaration
drift apart without anybody noticing.
"""

import sys
from typing import Any, List, Optional, Tuple, Type

from model.game.configuration import compose_section
from model.misc.export_writers import ExportWriter

from .algebraic import ExportAlgebraic
from .fen import ExportFEN
from .metadata import ExportMetadata
from .pgn import ExportPGN
from .stenographic import ExportStenographic

#: The writers in the order they are preferred, by class rather than by name. The transcript
#: leads, so a game written without being asked for a notation is written as PGN and saved as
#: `.pgn`; the rest follow the order the diagram enumerates them in.
PREFERRED: Tuple[Type[ExportWriter], ...] = (
    ExportPGN,
    ExportAlgebraic,
    ExportMetadata,
    ExportFEN,
    ExportStenographic,
)


def build_exporters(notes: Optional[List[str]] = None) -> List[Any]:
    """Build the export writers chess offers, in the order they are preferred.

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
