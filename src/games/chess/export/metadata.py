"""The game's own header record, written as a writer that belongs to chess.

The diagram's `ChessNotationWriter` box enumerates *Field - Field - Extra* among the formats
it writes (`notes/reference_diagram.md`, section "The `ChessNotationWriter` format list"), and
`PRD.md` FR-48 gives that name its one honest sentence: *the game transcript header, derived
from real state*. Those two are the same format. A header is a row of named fields and their
values, followed by whatever extra fields the game has to add, and PGN writes it as
`[Field "Value"]` pairs — so the notation is what a PGN header is, and the class that writes it
is `ExportMetadata`.

**This is what the diagram says and all the diagram says.** The box is prose, not a grammar:
it names the format and nothing else, and there is no code anywhere in the repository that
implemented it. The reading taken here is FR-48's, and it is recorded rather than assumed:

- the format is a **list of fields**, each a name and a value, in a fixed order;
- the **two fields the format is named for** are the roster every PGN header must carry — the
  names of the two sides — and the **extra** fields are the rest of the roster and anything the
  game adds, appended after them;
- the delimiter is the PGN tag pair `[Name "Value"]`, one per line, which is the delimiter the
  surrounding format already uses and the only one this repository had an implementation of.

Choosing PGN's tag pair rather than inventing a third delimiter is the whole decision. A
grammar of this repository's own invention would be a format nothing could read back and
nothing would have asked for; PGN's is a published one, it is what a PGN header already is, and
`ExportPGN` composes this writer rather than keeping a second copy of the roster.

It used to be an engine class, `model/misc/metadata.py`, and the move is what its defaults and
its one writing method already said: the seven-tag roster with `White`, `Black` and `Round`, and
`format_pgn_headers()`. None of that is chess, so none of it was ever the engine's to hold — and
`SCRATCHPAD.md` §4.1 records that it stayed in the engine only because `GameManager` built it
with no arguments and `Configuration` had nowhere to put one.

**What it writes is derived, and nothing in it is invented.** The players come from the players
the game was played by, the date from the day the game started, and the result from the outcome
the rules reached. A tag with nothing to say carries `?`, which is how the seven-tag roster
itself says *not supplied* — it is a statement about the game rather than a name somebody made
up. `Result` carries `*` for the same reason and because `*` is what the roster prescribes for
a game that has not finished. The header used to announce `Player 1`, `Player 2` and this
product's name in `Site`, which were three strings about nobody in particular.
"""

from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.game.rule import DECISIVE_KINDS, KIND_DRAW
from model.misc.export_writers import ExportWriter

#: The fields a header must carry, in the order the roster prescribes.
TAG_ROSTER: Tuple[str, ...] = ("Event", "Site", "Date", "Round", "White", "Black", "Result")

#: What a field says when the game has nothing to say for it. The roster's own marker.
UNKNOWN: str = "?"

#: What `Result` says while the game is still being played. The roster's own marker.
UNFINISHED: str = "*"


class ExportMetadata(ExportWriter):
    """Writes the fields a finished game is described by: who played, when, and how it ended."""

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """Declare the fields this game's header carries that nothing else can say.

        Only what a game knows about itself before it is played goes here — the name of the
        event it is, where it is being played. Everything the game itself supplies (who was
        playing, when it began, how it ended) is derived at write time and is not declared, so
        a declared value can never disagree with what actually happened.

        Args:
            headers: Fields to declare, by name. Each wins over anything derived, so a
                configuration can record a result it knows and a game that has not finished
                yet does not overwrite it with `*`.
        """
        self.headers: Dict[str, str] = dict(headers) if headers else {}

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("Field-Field-Extra",)

    def set_header(self, key: str, value: str) -> None:
        """Declare a field, or replace the one already declared.

        Args:
            key: The field's name, such as `Event` or `Round`.
            value: What the field says.

        Returns:
            None
        """
        self.headers[str(key)] = str(value)

    def get_header(self, key: str, default: str = "") -> str:
        """Read a declared field.

        Args:
            key: The field's name.
            default: What to answer when the field was never declared.

        Returns:
            str: The declared value, or `default`.
        """
        return self.headers.get(str(key), default)

    @staticmethod
    def _player_name(players: Iterable[Any], color: int) -> Optional[str]:
        """Return the name of whoever played one side.

        The player is asked for its user and the user for its name, because that is the chain
        a name travels along in this program: a `Player` is a side and a `User` is a person.

        Args:
            players: The players the game was played by.
            color: The side being asked about.

        Returns:
            Optional[str]: The user's name, its handle when it has no name, or None when that
            side was played by nobody this program knows.
        """
        for player in players or ():
            if getattr(player, "getColor", None) is None:
                continue
            if player.getColor() != color:
                continue
            user = player.getUser() if hasattr(player, "getUser") else None
            if user is None:
                return None
            for attribute in ("name", "username"):
                value = getattr(user, attribute, None)
                if isinstance(value, str) and value.strip():
                    return value
            return None
        return None

    @staticmethod
    def _result_token(result: Any) -> Optional[str]:
        """Return how the roster spells the outcome the rules reached.

        The engine's outcome is a kind, a winner and a reason written for the status line; the
        roster's is one of three tokens. Converting between them is the header's business,
        because a token is a spelling and a spelling belongs to the format. The winner is a
        colour and is asked for as one, so a win and a loss differ only in whose point of view
        the rules reached them.

        Args:
            result: The game's outcome, or None while the game is still going.

        Returns:
            Optional[str]: `1-0`, `0-1` or `1/2-1/2`, or None when there is no outcome yet or
            the outcome names no winner on either side.
        """
        if result is None:
            return None
        kind = getattr(result, "kind", None)
        if kind == KIND_DRAW:
            return "1/2-1/2"
        if kind in DECISIVE_KINDS and getattr(result, "winner", None) in (1, -1):
            return "1-0" if result.winner == 1 else "0-1"
        return None

    def header_values(
        self,
        players: Optional[Iterable[Any]] = None,
        result: Any = None,
        date: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """Return every field this game's header carries, derived and declared alike.

        A field the game can say something about is written from what the game did. A field
        the game has nothing to say about falls back to what was declared for it, and to the
        roster's own marker when nothing was declared either. So a header never carries a
        name or a result that nobody supplied.

        Args:
            players: The players the game was played by, one per side.
            result: The game's outcome, or None while it is still going.
            date: When the game began.

        Returns:
            Dict[str, str]: Every field of the roster, in roster order, plus whatever extra
            fields were declared.
        """
        sides = list(players or [])
        derived: Dict[str, Optional[str]] = {
            "White": self._player_name(sides, 1),
            "Black": self._player_name(sides, -1),
            "Result": self._result_token(result),
            "Date": date.strftime("%Y.%m.%d") if isinstance(date, datetime) else None,
        }
        merged: Dict[str, str] = {}
        for tag in TAG_ROSTER:
            value = derived.get(tag) or self.headers.get(tag)
            if value is None:
                value = UNFINISHED if tag == "Result" else UNKNOWN
            merged[tag] = str(value)
        for tag, value in self.headers.items():
            if tag not in merged:
                merged[str(tag)] = str(value)
        return merged

    @staticmethod
    def format_tags(tags: Dict[str, str]) -> str:
        """Write fields as tag pairs, one per line.

        Args:
            tags: The fields to write, in the order they are to appear.

        Returns:
            str: One `[Name "Value"]` line per field.
        """
        return "\n".join(f'[{name} "{value}"]' for name, value in tags.items())

    def to_field_field_extra(
        self,
        players: Optional[Iterable[Any]] = None,
        result: Any = None,
        date: Optional[datetime] = None,
    ) -> str:
        """Write the game's header as tag pairs.

        Args:
            players: The players the game was played by, one per side.
            result: The game's outcome, or None while it is still going.
            date: When the game began.

        Returns:
            str: The header: the roster, derived from the game, one tag pair per line.
        """
        return self.format_tags(self.header_values(players=players, result=result, date=date))

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game's header.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `players`, `result` and `date`, all of them optional.

        Returns:
            str: The game's header as tag pairs.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_field_field_extra(
            players=kwargs.get("players"),
            result=kwargs.get("result"),
            date=kwargs.get("date"),
        )
