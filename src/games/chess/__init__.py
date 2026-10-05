"""The chess configuration: the default game, shipped with the package.

`board.py` declares the rows, columns and starting placement; `pieces/`, `rules/`,
`quests/`, `clocks/` and `export/` hold one file per entry. It is the default configuration
and cannot be edited or deleted: a variant starts by duplicating it.

Composition is out loud and it is the directory. `build_configuration()` below says what this
game is, and `pieces/`, `rules/`, `quests/`, `clocks/` and `export/` are each composed out of
the files they hold: a rule written into `rules/` is in force, and a piece written into
`pieces/` is in the catalogue, because each is a file in that directory. There is no registry
and no plugin loader, so what is in force is what the tree holds and nothing else.

Every import below is relative, and that is load-bearing rather than stylistic. This directory
is a copyable unit: `cp -r games/chess games/house` and a variant exists. An absolute
`games.chess.…` import inside a copy would still reach back here, so the copy would load this
board, these pieces and these rules while looking like it had loaded its own — silently, with
no error and no warning. `model/game/configuration.py` loads a configuration as a package in
its own right for the same reason, `compose_section` composes the section it is handed rather
than a section it looked up by name, and `rules/` and `pieces/` import relatively for the same
reason: the rules a copy composes, and the pieces its promotions produce, are the copy's.
"""

from typing import Any, Iterable, List, Optional

from model.game.configuration import Configuration
from model.game.quest import Quest

from . import clocks as clock_files
from . import export as export_files
from . import pieces as piece_files
from . import quests as quest_files
from . import rules as rule_files
from .board import build_board
from .export.algebraic import AlgebraicNotation
from .export.metadata import ExportMetadata

#: This configuration's directory name. A configuration knows what it is called — it is the
#: directory it lives in — and nothing else has to repeat it: the engine names no configuration,
#: and which configuration a game starts in is declared by the configurations root beside them
#: rather than by the configuration itself, because a copy of this directory says exactly what
#: this one says.
CONFIGURATION_NAME = "chess"


def build_metadata(exporters: Iterable[Any]) -> Optional[ExportMetadata]:
    """Return the header record among the composed writers, declaring chess's own fields on it.

    The record is one of the writers `export/` composes, and this returns that same object
    rather than a second one built here: a record is both a format in its own right and the
    thing `GameManager` hands to every writer as `metadata`, and two records would be two that
    could drift apart — one written with the event name and one without. Finding it among the
    composed writers is what puts the same object in both places.

    Only what a game knows before it is played is declared: the name of the event. Who was
    playing, when it began and how it ended are all derived from the game at write time, so
    nothing declared here can disagree with what happened.

    Args:
        exporters: The writers `export/` composed.

    Returns:
        Optional[ExportMetadata]: The header writer with `Event` declared, or None when the
        composed writers hold no header record — a configuration that describes its games in
        prose alone, and one the engine already supports by declaring no metadata.
    """
    for writer in exporters:
        if isinstance(writer, ExportMetadata):
            writer.set_header("Event", CONFIGURATION_NAME)
            return writer
    return None


def build_configuration() -> Configuration:
    """Assemble the chess configuration.

    Nothing here names a piece, a rule, a quest, a clock or a writer. The one list is the
    sections: each is composed out of the files its own directory holds, so nothing in this
    function has to name an entry for it to be in force. Every composition is handed the same
    list and it is read afterwards, which is what lets a file in *any* section that declares
    nothing be reported by name rather than dropped in silence.

    The header record is the one thing read back out rather than composed: `export/` composes
    it like any other writer, and `build_metadata` finds that object among them and declares
    chess's event on it, so the record the manager is handed is the record the writers offer.

    Returns:
        Configuration: The chess board, and the pieces, rules, quests, clocks and exporters
        chess brings with it, together with the naming chess gives a move — which is what
        the window draws the move history with, and what a copy of this directory brings with
        it — and the header record its transcripts are written with.
    """
    uncomposed: List[str] = []
    exporters = export_files.build_exporters(uncomposed)
    return Configuration(
        name=CONFIGURATION_NAME,
        path="",
        board=build_board(),
        pieces=piece_files.build_pieces(uncomposed),
        rules=rule_files.build_rules(uncomposed),
        quests=build_quests(uncomposed),
        clocks=clock_files.build_clocks(uncomposed),
        exporters=exporters,
        metadata=build_metadata(exporters),
        notation=AlgebraicNotation(),
        board_factory=build_board,
        uncomposed=uncomposed,
    )


def build_quests(notes: Optional[List[str]] = None) -> List[Quest]:
    """Build the quests chess offers by default.

    `CaptureOfType` and `KingOnlyGame` are here rather than in `model/game/quests.py`'s
    roster, because both insist on naming a piece type and only chess can say which one. The
    engine holds the classes and the parameters; this is where the answers live.

    Whatever `quests/` holds is composed on top of them, so a quest written there joins this
    configuration without being named here.

    Args:
        notes: A list to record one line in per file that declares no quest. Defaults to None,
            which discards them.

    Returns:
        List[Quest]: A small starter set, all of them switchable from the settings form, plus
        whatever the files in `quests/` declare.
    """
    from model.game.quests import (
        CaptureN,
        CaptureOfType,
        FirstBlood,
        KingOnlyGame,
        MakeCheckN,
        WonBy,
    )

    return [
        FirstBlood(reward=25),
        CaptureN(count=5, reward=50),
        CaptureOfType(piece_type="queen", count=1, reward=45),
        MakeCheckN(count=3, reward=40),
        KingOnlyGame(royal_kind="king", reward=60),
        WonBy(color=1, reward=75),
        *quest_files.build_quests(notes),
    ]
