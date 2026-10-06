"""The five ways a chess game ends without a winner.

Each is a rule that proposes; none of them imposes. Precedence makes two firing at once
deterministic, and every one of them is switchable, because "at what value" is
configuration and "whether at all" is the player's.
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

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
    """End the game in a draw once a position has occurred three times.

    A position is counted when every rule has been told what happened, not when this rule is.
    `on_move_made` runs in the middle of that announcement — the rules are notified in
    composition order, and this configuration's `draws.py` is notified before its
    `en_passant.py` — so what the set is offering about the position just reached is not yet in
    the set when this rule would read it. The part of a position that is on the board is
    therefore read at once and the part that is in the rules is read at the first moment it is
    answerable; see `_settle`.
    """

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
        self.state["pending"] = []
        self.recorded = None

    def permits_move(self, position: Any, move: Move) -> bool:
        """Count what the last move produced, and allow this move as this rule always does.

        This is where the counting happens, and it is here rather than in `on_move_made`
        because validation is the first moment after a move on which every rule has been told
        what happened. It is also a moment this rule is guaranteed to be asked at: every move
        anybody plays is validated first, so a position cannot go uncounted for want of a
        question — which matters because nothing in the shipped game asks whether the game is
        over until it is.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: True. This rule forbids nothing; it only counts.
        """
        self._settle()
        return True

    def _settle(self) -> None:
        """Count every position set aside that the rule set has now finished telling us about.

        A rule that offers a square holds the offer for one ply and withdraws it on the next
        move of any kind, so its answer is final from the moment the move producing it has been
        announced until the next move is announced — and reading it anywhere else reads the
        wrong ply's offer. This rule is notified inside that window but before the offering
        rule has been, so the placement is set aside when the move is announced and the offer
        is read here, from a set that has been told everything.

        Returns:
            None
        """
        pending = self.state.get("pending") or []
        if not pending:
            return
        offers = offered_squares(self.rules)
        self.state["pending"] = []
        seen = self.state.setdefault("seen", {})
        for placement in pending:
            key = with_offers(placement, offers)
            self.recorded = key
            seen[key] = seen.get(key, 0) + 1

    def record(self, position: Any, active_color: Optional[int] = None) -> int:
        """Record a position once and report how often it has occurred.

        Recording is idempotent for the position being judged, so asking whether the game is
        over cannot itself push a position over the limit. Everything set aside by the last
        move is counted first, which is what makes the position being judged the one just
        counted rather than a second occurrence of it.

        Args:
            position: The board as it stands.
            active_color: Whose turn it is in this position. Defaults to the colour this
                rule was last told is to move, which is right whenever the position is the
                one the game is actually in.

        Returns:
            int: How many times this position has occurred in this game.
        """
        self._settle()
        key = position_key(
            position, self.active_color if active_color is None else active_color, self.rules
        )
        if key == self.recorded:
            return self.state.setdefault("seen", {}).get(key, 1)
        self.recorded = key
        seen = self.state.setdefault("seen", {})
        seen[key] = seen.get(key, 0) + 1
        return seen[key]

    def on_move_made(self, position: Any, move: Move) -> None:
        """Set aside the position the move produced.

        The position a move produces is judged with the *next* player to move, not the one
        who just moved. `active_color` still names the player who moved, because a game
        flips it after telling the rules what happened, so keying on it recorded every
        position under a turn order no other record of that position would ever use, and no
        position could be seen twice.

        What is set aside is the placement alone. The rules are notified in composition order
        and this one is notified before any rule that offers a square, so the offer for this
        position is not in the set yet and is read later, by `_settle`, from a set that has
        been told everything.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        mover = move.piece.getColor() if move.piece is not None else self.active_color
        self.state.setdefault("pending", []).append(placement_key(position, opponent(mover)))

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


def offered_squares(rules: Iterable[Any]) -> List[Tuple[int, int]]:
    """Return every square the rule set is offering, in an order that does not depend on it.

    Args:
        rules: The rules in force, in the order the configuration declared them. Every rule
            answers this — it is declared on the parent — so there is nothing to skip.

    Returns:
        List[Tuple[int, int]]: The squares being offered, each once, sorted. Sorted because
        the rules are declared in file-name order, which is a tie-break for two rules
        proposing an outcome and says nothing about which of two simultaneous offers identifies
        a position first.
    """
    squares: Set[Tuple[int, int]] = set()
    for rule in rules:
        square = rule.target_square()
        if square is not None:
            squares.add((square[0], square[1]))
    return sorted(squares)


def with_offers(placement: str, offers: Sequence[Tuple[int, int]]) -> str:
    """Complete a placement key with what the rule set is offering.

    Args:
        placement: The key built from the board alone.
        offers: The squares the rule set is offering, already reduced by `offered_squares`.

    Returns:
        str: The placement key with one field per offer. A set offering nothing returns the
        placement key unchanged, so a configuration whose rules make no offers is described by
        exactly the key it was described by before.
    """
    return placement + "".join(f"|offer:{row}:{col}" for row, col in offers)


def placement_key(position: Any, active_color: int) -> str:
    """Build the part of a position's identity that is on the board.

    Everything here can be read at the moment a move is announced, which is what makes it the
    half of `position_key` a rule can read for itself: what the rule set is offering is only
    answerable once the whole set has been told, and the two halves are read at different
    moments for that reason.

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


def position_key(position: Any, active_color: int, rules: Iterable[Any] = ()) -> str:
    """Build the identity of a position for repetition purposes.

    The rulebook's test is "the same player to move, the same pieces on the same squares, and
    the same moves available to every piece". The first two are on the board and the third is
    not: what a rule is offering lives in that rule's state and nowhere else, so it is read by
    asking the set rather than by reading the board. Every rule answers `target_square`, which
    is the question "what square are you offering", and a rule that offers nothing answers
    None — so the key covers whatever this set is offering, and a set that offers nothing is
    described by exactly the key it was described by before.

    For a capture in passing the offer is recorded after every two-square advance whether or
    not a capture is available to anybody, the same convention the position record writes and
    for the same reason: an answer that depended on which pieces happened to be standing where
    would depend on the rules in force rather than on the position. **The cost is that the
    key is conservative in the safe direction.** Two placements reached with an offer standing
    and without one are two positions here, where the rulebook would sometimes call them one
    — the offer it cannot take up is not a move — so a repetition can go uncounted rather than
    a repetition be claimed that the rulebook does not allow. That is the right way round for a
    draw, and it is the same trade-off `export/fen.py` records for the same field.

    **The offer belongs to the ply it was made on, and is read at the right moment.** A rule
    that offers a square withdraws the offer on the next move of any kind, so its answer is
    final only between one move being announced and the next one tried; read inside the
    announcement it answers for the wrong ply. A caller that reads the key while rules are
    being notified will therefore get the previous ply's offer — which is why
    `ThreefoldRepetitionRule` reads `placement_key` when the move is announced and the offers
    afterwards.

    Args:
        position: The board as it stands.
        active_color: Whose turn it is.
        rules: The rules in force, asked what they are offering. Defaults to no rules at all,
            which is a set offering nothing and keys the placement alone.

    Returns:
        str: A key covering the placement, whose turn it is, the moved flag of the pieces whose
        movement that flag governs, and one field per square the rule set is offering.
    """
    return with_offers(placement_key(position, active_color), offered_squares(rules))


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
