"""The five ways a chess game ends without a winner.

Each is a rule that proposes; none of them imposes. Precedence makes two firing at once
deterministic, and every one of them is switchable, because "at what value" is
configuration and "whether at all" is the player's.
"""

from typing import Any, Dict, List, Optional, Tuple

from model.game.field import Field
from model.game.move import Move
from model.game.rule import KIND_DRAW, Result, Rule
from .attacks import kinds_of, opponent, square_color

#: Precedence of each draw, so two firing at once is deterministic.
STALEMATE_PRECEDENCE = 90
INSUFFICIENT_MATERIAL_PRECEDENCE = 80
THREEFOLD_PRECEDENCE = 70
FIFTY_MOVE_PRECEDENCE = 60
AGREEMENT_PRECEDENCE = 50


class InsufficientMaterialRule(Rule):
    """End the game in a draw when neither side can possibly checkmate."""

    default_name = "Insufficient material"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: The piece kinds that can mate on their own or in company, and the
            pairings that cannot.
        """
        return [
            Field(
                "mating_kinds", "choice", "Can mate alone", "rook,queen", choices=("rook", "queen")
            ),
            Field(
                "minor_kinds",
                "choice",
                "Cannot mate alone",
                "knight,bishop",
                choices=("knight", "bishop"),
            ),
            Field("royal_kind", "text", "Royal piece kind", "king"),
        ]

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw when no legal sequence of moves can produce a mate.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None when somebody can still mate.
        """
        royal = self.value.get("royal_kind")
        majors = {_canon(kind) for kind in _split(self.value.get("mating_kinds"))}
        minors = {_canon(kind) for kind in _split(self.value.get("minor_kinds"))}

        for color in (1, -1):
            counts = kinds_of(position, color)
            if counts.get(royal, 0) != 1:
                return None
            if any(counts.get(kind, 0) for kind in majors):
                return None
            non_royal = {kind: n for kind, n in counts.items() if kind != royal and n}
            if sum(non_royal.values()) == 0:
                continue
            if set(non_royal) <= set(minors) and sum(non_royal.values()) == 1:
                continue
            if set(non_royal) == {"bishop"} and sum(non_royal.values()) == 2:
                if _same_colour_bishops(position, color, royal):
                    continue
            return None

        return Result(
            KIND_DRAW, precedence=INSUFFICIENT_MATERIAL_PRECEDENCE, reason="insufficient material"
        )


class FiftyMoveRule(Rule):
    """End the game in a draw after so many moves with no capture and no advance."""

    default_name = "Fifty-move rule"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: How many half-moves without progress end the game, and which piece
            kinds count as progress.
        """
        return [
            Field("plies", "integer", "Half-moves without progress", 100, minimum=2),
            Field("progress_kinds", "text", "Kinds that reset the clock", "pawn"),
        ]

    def attach(self) -> None:
        """Start the clock at zero.

        Returns:
            None
        """
        # Assign, not setdefault: `attach` is what a new game calls, and a rule that
        # only defaults its state on first sight carries the last game's counter into
        # the next one.
        self.state["plies"] = 0

    def on_move_made(self, position: Any, move: Move) -> None:
        """Count the move, resetting the count when it made progress.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        # The piece that moved, not whatever now stands on the destination: a pawn that has just
        # promoted is a queen by the time anyone looks, and the counter failed to reset.
        piece = move.piece or position.get_piece_at(move.end_pos)
        progress = [_canon(kind) for kind in _split(self.value.get("progress_kinds"))]
        captured = move.captured_piece is not None or (
            move.capture_from is not None and position.get_piece_at(move.capture_from) is None
        )
        if (piece is not None and piece.getType() in progress) or captured:
            self.state["plies"] = 0
            return
        self.state["plies"] = self.state.get("plies", 0) + 1

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw once the move count without progress is reached.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None.
        """
        limit = self.value.get("plies", 100)
        if self.state.get("plies", 0) < limit:
            return None
        return Result(KIND_DRAW, precedence=FIFTY_MOVE_PRECEDENCE, reason="fifty-move rule")


class ThreefoldRepetitionRule(Rule):
    """End the game in a draw once a position has occurred three times."""

    default_name = "Threefold repetition"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: How many occurrences end the game.
        """
        return [Field("occurrences", "integer", "Occurrences", 3, minimum=2)]

    def attach(self) -> None:
        """Forget every position seen in a previous game.

        A rule cannot record the position a game starts in: `attach` is handed the game, not
        the board, so it has nothing to record. The starting position is instead counted when
        it is first asked about, and the count is off by one until then.

        Returns:
            None
        """
        self.state["seen"] = {}
        self.recorded = None

    def record(self, position: Any, active_color: Optional[int] = None) -> int:
        """Record a position once and report how often it has occurred.

        Recording is idempotent for the position being judged, so asking whether the game is
        over cannot itself push a position over the limit.

        Args:
            position: The board as it stands.
            active_color: Whose turn it is in this position. Defaults to the colour this
                rule was last told is to move, which is right whenever the position is the
                one the game is actually in.

        Returns:
            int: How many times this position has occurred in this game.
        """
        key = position_key(position, self.active_color if active_color is None else active_color)
        if key == self.recorded:
            return self.state.setdefault("seen", {}).get(key, 1)
        self.recorded = key
        seen = self.state.setdefault("seen", {})
        seen[key] = seen.get(key, 0) + 1
        return seen[key]

    def on_move_made(self, position: Any, move: Move) -> None:
        """Record the position the move produced.

        The position a move produces is judged with the *next* player to move, not the one
        who just moved. `active_color` still names the player who moved, because a game
        flips it after telling the rules what happened, so keying on it recorded every
        position under a turn order no other record of that position would ever use, and no
        position could be seen twice.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        mover = move.piece.getColor() if move.piece is not None else self.active_color
        self.record(position, opponent(mover))

    recorded: Optional[str] = None

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw when the current position has occurred often enough.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None.
        """
        limit = self.value.get("occurrences", 3)
        if self.record(position, self.active_color) < limit:
            return None
        return Result(KIND_DRAW, precedence=THREEFOLD_PRECEDENCE, reason="threefold repetition")


class MutualAgreementRule(Rule):
    """End the game in a draw when both players agree to one."""

    default_name = "Draw by agreement"

    def attach(self) -> None:
        """Clear any offer left over from a previous game.

        Returns:
            None
        """
        self.state["offered"] = False
        self.state["accepted"] = False

    def offer(self) -> None:
        """Offer a draw.

        Returns:
            None
        """
        self.state["offered"] = True

    def accept(self) -> None:
        """Accept an offer that has been made.

        Returns:
            None
        """
        if self.state.get("offered"):
            self.state["accepted"] = True

    def decline(self) -> None:
        """Turn down an offer.

        Returns:
            None
        """
        self.state["offered"] = False

    def status(self, position: Any) -> Optional[str]:
        """Report that a draw has been offered, while the game continues.

        Args:
            position: The board as it stands.

        Returns:
            Optional[str]: `Draw offered`, or None.
        """
        return (
            "Draw offered" if self.state.get("offered") and not self.state.get("accepted") else None
        )

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw once both players have agreed to one.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None.
        """
        if not self.state.get("accepted"):
            return None
        return Result(KIND_DRAW, precedence=AGREEMENT_PRECEDENCE, reason="agreement")


#: The piece kinds whose moved flag changes what they may do. A castle is the only move in
#: chess that a piece loses by having moved, and it takes a king and a rook, so these are the
#: only two kinds whose flag is part of a position's identity.
RIGHTS_BEARING_KINDS: Tuple[str, ...] = ("king", "rook")


def position_key(position: Any, active_color: int) -> str:
    """Build the identity of a position for repetition purposes.

    The rulebook's test is "the same player to move, the same pieces on the same squares, and
    the same moves available to every piece". This covers the first two and, for castling, the
    third. It does not cover a capture in passing: this configuration keeps no en passant target
    on the board for a key to read, so a position reached by a pawn's two-square advance keys
    the same as the same placement reached any other way. Reaching the same placement twice with
    a live offer on the second occasion takes a pawn arriving on that square twice by different
    routes, which no line of play produces, so the omission is recorded in
    `notes/object_model.md` rather than worked around.

    Args:
        position: The board as it stands.
        active_color: Whose turn it is.

    Returns:
        str: A key covering the placement, whose turn it is, and the moved flag of the pieces
        whose movement that flag governs.
    """
    parts = [str(active_color)]
    for r in range(position.rows):
        for c in range(position.cols):
            piece = position.get_piece_at((r, c))
            if piece is None:
                parts.append(".")
                continue
            moved = ""
            if piece.getType() in RIGHTS_BEARING_KINDS:
                # Only these two kinds have legal moves that depend on whether they have moved:
                # a king or a rook that has moved cannot castle. A knight that has been to f3
                # and back is on the same square in the same way as one that has not, so keying
                # on its flag made `1.Nf3 Nf6 2.Ng1 Ng8 3.Nf3 Nf6 4.Ng1 Ng8` look like a game
                # where no position ever repeated, and the draw was never offered.
                moved = "m" if piece.hasMoved() else "n"
            parts.append(f"{piece.getType()}{'w' if piece.getColor() == 1 else 'b'}{moved}")
    return "|".join(parts)


#: The knight's class was renamed to `Knight` on 2026-10-03, and its *configured* kind was
#: not renamed with it: `piece_type` is data this configuration chooses and persists, so a
#: stored value of `horse` still has to mean the knight. Both spellings are therefore accepted,
#: and a setting written for `knight` keeps working either way.
_KIND_ALIASES = {"knight": "horse", "horse": "horse"}


def _canon(kind: str) -> str:
    """Return the piece type descriptor a configured kind name refers to.

    Args:
        kind: The configured kind name.

    Returns:
        str: The descriptor the pieces actually report, or the name unchanged when there is
        no alias for it.
    """
    return _KIND_ALIASES.get(kind, kind)


def _split(value: Any) -> List[str]:
    """Read a comma-separated configuration value as a list.

    Args:
        value: The configured value.

    Returns:
        List[str]: The entries, empty when nothing is configured.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if value:
        return [str(item) for item in value]
    return []


def _same_colour_bishops(position: Any, color: int, royal: str) -> bool:
    """Report whether a colour's bishops are all on one shade of square.

    Args:
        position: The board to read.
        color: Colour to inspect.
        royal: The royal piece kind, which is not a bishop.

    Returns:
        bool: True when the bishops share a shade and so cannot mate between them.
    """
    shades = set()
    for r in range(position.rows):
        for c in range(position.cols):
            piece = position.get_piece_at((r, c))
            if piece is not None and piece.getColor() == color and piece.getType() == "bishop":
                shades.add(square_color(position, (r, c)))
    return len(shades) <= 1
