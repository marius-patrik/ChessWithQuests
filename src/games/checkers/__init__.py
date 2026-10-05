"""The checkers configuration: English draughts, shipped with the package.

`board.py` declares the rows, columns, the dark squares and the starting placement;
`pieces/`, `rules/`, `quests/`, `clocks/` and `export/` hold one file per entry. Nothing in
it says "checkers" to the engine: it is a board, two piece kinds and eight rules, composed
out loud below, and the engine reads none of them by name.

Composition is out loud and it is the directory. `build_configuration()` below says what this
game is, and `pieces/`, `rules/`, `quests/`, `clocks/` and `export/` are each composed out of
the files they hold: a rule written into `rules/` is in force, and a piece written into
`pieces/` is in the catalogue, because each is a file in that directory. There is no registry
and no plugin loader, so what is in force is what the tree holds and nothing else. This is the proof the
abstraction was for: `chess` and `checkers` are two directories and one engine, and nothing
under `model/`, `controller/` or `view/` changed to make the second one exist. The
configuration imports itself by relative path throughout and `compose_section` composes the
section it is handed, so `cp -r games/checkers games/house` produces a directory that plays
*its own* rules rather than these.

Three things are worth stating here rather than leaving to be discovered:

- **There is no royal piece.** A king in this game is a man that has been crowned, and it is
  taken like any other piece, so nothing declares a royal kind and the engine's check
  machinery correctly finds nothing to do.
- **The king steps one square, as the rulebook says.** WCDF rule 1.17 gives a king's ordinary
    move as one square diagonally in any of the four directions, and rule 1.21 gives its
    capturing move as a man's in any direction. The flying king of international, Brazilian,
    Czech and Dutch draughts is the same piece with one number changed — `max_steps=None`
    instead of `max_steps=1` in `pieces/king.py` — and `tests/test_draughts_perft.py` records
    why the published perft counts cannot tell the two apart.
- **No man is removed.** A man that reaches the far row is crowned and keeps playing; the
  only ways out of the game are losing every piece, being unable to move, and the draws.

The game also says how it is written and how it is named, both of which are its own answers:
`export/` holds the two formats this game has — the letter notation and the metadata header —
and there is deliberately no third, because English draughts has no position record to write and
`games/checkers/export/__init__.py` argues why at length.
"""

from typing import Any, Iterable, List, Optional

from model.game.configuration import Configuration

from . import clocks as clock_files
from . import export as export_files
from . import pieces as piece_files
from . import quests as quest_files
from . import rules as rule_files
from .board import build_board
from .export.letter import NumberedNotation
from .export.metadata import ExportMetadata

#: The name this configuration is loaded by.
NAME: str = "checkers"


def build_metadata(exporters: Iterable[Any]) -> Optional[ExportMetadata]:
    """Return the header record among the composed writers, declaring nothing on it.

    The record is one of the writers `export/` composes, and this returns that same object
    rather than a second one built here: a record is both a format in its own right and the
    thing `GameManager` hands to every writer as `metadata`, and two records would be two that
    could drift apart.

    Nothing is declared on it. A draughts header says who played, when, and how the game
    ended, and every one of those three is derived from the game at write time — so a declared
    value could only ever contradict what actually happened. Declaring an event name is what a
    configuration knows about itself before it is played, and this one is only ever loaded as
    `checkers`.

    Args:
        exporters: The writers `export/` composed.

    Returns:
        Optional[ExportMetadata]: The header writer, untouched, or None when the composed
        writers hold no header record — a configuration that describes its games in prose
        alone, and one the engine already supports by declaring no metadata.
    """
    for writer in exporters:
        if isinstance(writer, ExportMetadata):
            return writer
    return None


def build_configuration() -> Configuration:
    """Assemble the checkers configuration.

    Nothing here names a piece, a rule, a quest, a clock or a writer. The one list is the
    sections: each is composed out of the files its own directory holds, so nothing in this
    function has to name an entry for it to be in force. Every composition is handed the same
    list and it is read afterwards, which is what lets a file in *any* section that declares
    nothing be reported by name rather than dropped in silence.

    The header record is the one thing read back out rather than composed: `export/` composes
    it like any other writer, and `build_metadata` finds that object among them, so the record
    the manager is handed is the record the writers offer.

    Returns:
        Configuration: The checkers board, and the pieces, rules, quests, clocks and
        exporters it brings with it, together with the naming it gives a move — which is what
        the window draws the move history with, and what a copy of this directory brings with
        it — and the header record its games are described by.
    """
    uncomposed: List[str] = []
    exporters = export_files.build_exporters(uncomposed)
    return Configuration(
        name=NAME,
        path="",
        board=build_board(),
        pieces=piece_files.build_pieces(uncomposed),
        rules=rule_files.build_rules(uncomposed),
        quests=quest_files.build_quests(uncomposed),
        clocks=clock_files.build_clocks(uncomposed),
        exporters=exporters,
        metadata=build_metadata(exporters),
        notation=NumberedNotation(),
        board_factory=build_board,
        uncomposed=uncomposed,
    )
