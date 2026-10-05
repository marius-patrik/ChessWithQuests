"""The checkers configuration: English draughts, shipped with the package.

`board.py` declares the rows, columns, the dark squares and the starting placement;
`pieces/`, `rules/`, `quests/`, `clocks/` and `export/` hold one file per entry. Nothing in
it says "checkers" to the engine: it is a board, two piece kinds and eight rules, composed
out loud below, and the engine reads none of them by name.

Composition is explicit. `build_configuration()` is the whole list of what this game is —
there is no registry, nothing is discovered by name, and a rule that is not named here is
not in force. This is the proof the abstraction was for: `chess` and `checkers` are two
directories and one engine, and nothing under `model/`, `controller/` or `view/` changed to
make the second one exist. The configuration imports itself by relative path throughout, so
`cp -r games/checkers games/house` produces a directory that plays *its own* rules rather
than these.

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
`build_exporters()` below declares the two formats this game has — the letter notation and the
metadata header — and there is deliberately no third, because English draughts has no position
record to write and `games/checkers/export/__init__.py` argues why at length.
"""

from typing import Any, List, Optional

from model.game.configuration import Configuration

from .board import build_board
from .clocks.fischer import Fischer
from .export.letter import ExportLetter, NumberedNotation
from .export.metadata import ExportMetadata
from .pieces.king import King
from .pieces.man import Man
from .quests import build_quests
from .rules import build_rules

#: The name this configuration is loaded by.
NAME: str = "checkers"


def build_metadata() -> ExportMetadata:
    """Build the header record draughts games are written with.

    Nothing is declared here. A draughts header says who played, when, and how the game
    ended, and every one of those three is derived from the game at write time — so a
    declared value could only ever contradict what actually happened. Declaring an event name
    is what a configuration knows about itself before it is played, and this one is only ever
    loaded as `checkers`.

    Returns:
        ExportMetadata: A header record that declares nothing and derives all of it.
    """
    return ExportMetadata()


def build_exporters(metadata: Optional[ExportMetadata] = None) -> List[Any]:
    """Build the export writers draughts offers, in the order they are preferred.

    Order is the preference: `GameManager.default_format` takes the first format the first
    writer declares, and `save_log` names its file from that. The letter notation leads, so a
    draughts game written without being asked for a notation is written as square numbers and
    saved as `.letter` — which follows from the declaration here rather than from any list
    anywhere else.

    Each writer lives in `export/`, imported relatively, because a configuration is a directory
    that can be copied into a variant and an absolute `games.checkers.…` import would leave
    the copy writing with the original's writers. Which notations exist is draughts' answer;
    `notes/object_model.md` section 7 registers the arrangement and the engine keeps only the
    protocol.

    The header record is one of them and is handed back to the caller, because a record is
    both a format in its own right and the thing a transcript writer would compose its header
    from. Passing it to `build_configuration` as `metadata` is what puts the same object in
    both places.

    Adding a notation is one file in `export/` and one line here.

    Args:
        metadata: The header record to offer as a format. Defaults to a freshly built one.

    Returns:
        List[Any]: One writer per draughts notation: the letter notation and the header.
    """
    return [
        ExportLetter(),
        metadata if metadata is not None else build_metadata(),
    ]


def build_configuration() -> Configuration:
    """Assemble the checkers configuration.

    Returns:
        Configuration: The checkers board, and the pieces, rules, quests, clocks and
        exporters it brings with it, together with the naming it gives a move — which is what
        the window draws the move history with, and what a copy of this directory brings with
        it — and the header record its games are described by.
    """
    metadata = build_metadata()
    return Configuration(
        name=NAME,
        path="",
        board=build_board(),
        pieces=[Man, King],
        rules=build_rules(),
        quests=build_quests(),
        clocks=[Fischer()],
        exporters=build_exporters(metadata),
        metadata=metadata,
        notation=NumberedNotation(),
        board_factory=build_board,
    )
