"""The draughts header: who played, when, and how it ended.

The diagram enumerates *Field - Field - Extra* among the formats a notation writer produces
(`notes/reference_diagram.md`, "The `ChessNotationWriter` format list"), and `PRD.md` FR-48
gives that name its one sentence: *the game transcript header, derived from real state*. Both
configurations ship a writer for it, in their own directory, and this is draughts' one.

**It is derived, and what it writes comes from the game.** The two names come from the users
who played, the date from the day the game began, and the result from the outcome the rules
reached — asked of the engine's own `Result`, which is a kind and a winner, because a token
is a spelling and a spelling belongs to the format.

**There is no placeholder string here, and there is no `?`.** This is the one place draughts'
header differs from chess', and the difference is the format rather than the writer. A PGN
header is the seven-tag roster, which *obliges* a record to carry `Event`, `Site` and `Round`
whatever the program knows; `?` is therefore PGN's own way of saying *not supplied*, a claim
about the game rather than a name somebody invented. No published roster obliges an English
draughts record to carry a tag it has nothing for, so this writer leaves a field out instead
of giving it a string. Nothing in a draughts header is therefore ever `Player 1`, `Player 2`
or this product's own name — the three strings the old engine header announced, one of which
was a site nobody was at.

**The result is written the way a draughts score sheet writes it**: two points for a win and
one each for a draw, so `2-1`, `1-2` and `2-2`. That is this game's own convention and not
chess's `1-0`, and the writer spells it out rather than inheriting the other game's values. A
game that has not finished has no result, so its header carries no `Result` field rather than
a marker.

`ExportPGN` composes chess's header writer rather than keeping a second copy of its roster.
This game has no transcript writer — there is no PGN for it — so nothing composes this one,
and it is offered as a format of its own, which is what the diagram's format list says it is.

The naming comes from relative imports, so a copy of this directory writes its own header: an
absolute `games.checkers.…` import would reach back into the original, which is the failure
`tests/test_configuration_copying.py` exists to catch.
"""

from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.game.rule import DECISIVE_KINDS, KIND_DRAW
from model.misc.export_writers import ExportWriter

#: The fields a draughts header carries, in the order it carries them.
TAG_ROSTER: Tuple[str, ...] = ("Date", "White", "Black", "Result")

#: What a score sheet says when the first-named side won.
WHITE_WON: str = "2-1"

#: What a score sheet says when the second-named side won.
BLACK_WON: str = "1-2"

#: What a score sheet says when neither side won: a point each.
DRAWN: str = "2-2"


class ExportMetadata(ExportWriter):
    """Writes the fields a draughts game is described by: who played, when, and how it ended."""

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """Declare the fields this game's header carries that nothing else can say.

        Only what a game knows about itself before it is played goes here. Everything the game
        itself supplies — who was playing, when it began, how it ended — is derived at write
        time and is not declared, so a declared value can never disagree with what actually
        happened.

        Args:
            headers: Fields to declare, by name. Each wins over anything derived.
        """
        self.headers: Dict[str, str] = dict(headers) if headers else {}

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes, under the name the
            diagram gives it. It is the same format chess writes as `Field-Field-Extra` and
            for the same reason: a header is a header, and which fields it carries is the
            roster this game brings with it rather than a second format name.
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
        """Return how a score sheet spells the outcome the rules reached.

        The engine's outcome is a kind, a winner and a reason written for the status line; a
        score sheet's is two numbers. Converting between them is the header's business,
        because the spelling belongs to the format.

        Args:
            result: The game's outcome, or None while the game is still going.

        Returns:
            Optional[str]: `2-1`, `1-2` or `2-2`, or None when there is no outcome yet or the
            outcome names no winner on either side.
        """
        if result is None:
            return None
        kind = getattr(result, "kind", None)
        if kind == KIND_DRAW:
            return DRAWN
        if kind in DECISIVE_KINDS and getattr(result, "winner", None) in (1, -1):
            return WHITE_WON if result.winner == 1 else BLACK_WON
        return None

    def header_values(
        self,
        players: Optional[Iterable[Any]] = None,
        result: Any = None,
        date: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """Return every field this game's header carries, derived and declared alike.

        A field the game can say something about is written from what the game did. A field
        the game has nothing to say about is **left out** rather than filled in, so a header
        never carries a name or a result that nobody supplied.

        Args:
            players: The players the game was played by, one per side.
            result: The game's outcome, or None while it is still going.
            date: When the game began.

        Returns:
            Dict[str, str]: The roster's fields that have something to say, in roster order,
            plus whatever extra fields were declared.
        """
        sides = list(players or ())
        derived: Dict[str, Optional[str]] = {
            "White": self._player_name(sides, 1),
            "Black": self._player_name(sides, -1),
            "Result": self._result_token(result),
            "Date": date.strftime("%Y.%m.%d") if isinstance(date, datetime) else None,
        }
        merged: Dict[str, str] = {}
        for tag in TAG_ROSTER:
            value = derived.get(tag) or self.headers.get(tag)
            if value is not None:
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
            str: The header: the fields this game can state, one tag pair per line.
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


__all__ = [
    "BLACK_WON",
    "DRAWN",
    "TAG_ROSTER",
    "WHITE_WON",
    "ExportMetadata",
]
