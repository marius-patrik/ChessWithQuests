"""The chess configuration: the default game, shipped with the package.

`board.py` declares the rows, columns and starting placement; `pieces/`, `rules/`,
`quests/`, `clocks/` and `export/` hold one file per entry. It is the default configuration
and cannot be edited or deleted: a variant starts by duplicating it.

Composition is out loud and it is the directory. `build_configuration()` below says what this
game is, and `rules/` and `quests/` are composed out of the files they hold: a rule written
into `rules/` is in force because it is a file in `rules/`. There is no registry and no
plugin loader, so what is in force is what the tree holds and nothing else.

Every import below is relative, and that is load-bearing rather than stylistic. This directory
is a copyable unit: `cp -r games/chess games/house` and a variant exists. An absolute
`games.chess.…` import inside a copy would still reach back here, so the copy would load this
board, these pieces and these rules while looking like it had loaded its own — silently, with
no error and no warning. `model/game/configuration.py` loads a configuration as a package in
its own right for the same reason, `compose_section` composes the section it is handed rather
than a section it looked up by name, and `rules/` and `pieces/` import relatively for the same
reason: the rules a copy composes, and the pieces its promotions produce, are the copy's.
"""

from typing import Any, List, Optional

from model.game.configuration import Configuration
from model.game.games import DEFAULT_GAME
from model.game.quest import Quest
from model.game.rule import Rule

from . import quests as quest_files
from .board import build_board
from .clocks.fischer import Fischer
from .export.algebraic import AlgebraicNotation, ExportAlgebraic
from .export.fen import ExportFEN
from .export.metadata import ExportMetadata
from .export.pgn import ExportPGN
from .export.stenographic import ExportStenographic
from .pieces import build_pieces
from .rules import build_rules


def build_metadata() -> ExportMetadata:
    """Build the header record chess's games are written with.

    Only what a game knows before it is played goes in here: the name of the event. Who was
    playing, when it began and how it ended are all derived from the game at write time, so
    nothing declared here can disagree with what happened.

    Returns:
        ExportMetadata: A header record naming this configuration's event.
    """
    return ExportMetadata({"Event": DEFAULT_GAME})


def build_exporters(metadata: Optional[ExportMetadata] = None) -> List[Any]:
    """Build the export writers chess offers, in the order they are preferred.

    Order is the preference: `GameManager.default_format` takes the first format the first
    writer declares, and `save_log` names its file from that. PGN leads, so a chess game
    written without being asked for a notation is written as PGN and saved as `.pgn`.

    Each writer lives in `export/`, imported relatively, because a configuration is a
    directory that can be copied into a variant and an absolute `games.chess.…` import would
    leave the copy writing with the original's writers — silently, with no error and no
    warning. Which notations exist is chess's answer; `notes/object_model.md` section 7
    registers the arrangement and the engine keeps only the protocol.

    The header record is one of them and is handed back to the caller, because a record is
    both a format in its own right and the thing the transcript writer composes its header
    from. Passing it to `build_configuration` as `metadata` is what puts the same object in
    both places; called without one, this function builds a fresh record and the configuration
    gets a second, which is why the composition below passes its own.

    Adding a notation is one file in `export/` and one line here.

    Args:
        metadata: The header record to offer as a format. Defaults to a freshly built one.

    Returns:
        List[Any]: One writer per chess notation: the transcript, the algebraic record, the
        header record, the position record, and the coordinate record.
    """
    return [
        ExportPGN(),
        ExportAlgebraic(),
        metadata if metadata is not None else build_metadata(),
        ExportFEN(),
        ExportStenographic(),
    ]


def build_configuration() -> Configuration:
    """Assemble the chess configuration.

    The one list is the sections: `rules/` and `quests/` are composed out of the files they
    hold, so nothing here has to name a rule for it to be in force. Both compositions are
    handed the same list, and it is read afterwards, which is what lets a file in either
    section that declares nothing be reported by name rather than dropped in silence.

    Returns:
        Configuration: The chess board, and the pieces, rules, quests, clocks and exporters
        chess brings with it, together with the naming chess gives a move — which is what
        the window draws the move history with, and what a copy of this directory brings with
        it — and the header record its transcripts are written with.
    """
    metadata = build_metadata()
    uncomposed: List[str] = []
    rules = build_rules(uncomposed)
    quests = build_quests(uncomposed)
    return Configuration(
        name=DEFAULT_GAME,
        path="",
        board=build_board(),
        pieces=build_pieces(),
        rules=rules,
        quests=quests,
        clocks=[Fischer()],
        exporters=build_exporters(metadata),
        metadata=metadata,
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
