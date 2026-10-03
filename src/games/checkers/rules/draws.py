"""The three ways a game of draughts ends without a winner.

Each is a rule that proposes; none imposes. Precedence makes two firing at once
deterministic, and every one of them is switchable, because at what value a game is drawn is
configuration and whether it is drawn at all is the player's.

The fifty-move rule of draughts is not the fifty-move rule of chess. A draughts game is drawn
after so many plies without *progress*, and progress is two things: taking a piece, or moving
a man. Moving a king is not progress, because a king can only ever retrace ground it has
already covered, so fifty moves of shuffling kings have advanced nothing. A man that steps
onto the far row is progress even though it is crowned on arrival, because it got there.
The default of a hundred plies is fifty moves by each side; the WCDF rulebook draws at
forty moves by each side, which is eighty plies, and the field is configurable so a club
playing to the rulebook can set it.

**Insufficient material is not an English draughts rule and is not quite true.** The rulebook
draws by agreement, by threefold repetition, and by the rule above, and nothing else; there
is no "neither side has a man left" condition, because two kings really can be beaten by one
and a kings-only game really is won. What this rule does is end any position in which
neither side can still crown something, which is a claim about *material* rather than about
the game: it assumes that once neither side can gain a piece, neither side can finish. That
assumption is false for the two-kings-against-one endgame and true for most of the rest, so
the rule is on by default because it is what was asked for and off by one field for anybody
who would rather play those endgames out. It is the first thing to switch off if the endgame
draws feel wrong.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import KIND_DRAW, Result, Rule
from .capture import is_capture
from .geometric import kinds_of

#: Precedence of each draw, so two firing at once is deterministic.
INSUFFICIENT_MATERIAL_PRECEDENCE = 80
FIFTY_MOVE_PRECEDENCE = 60
AGREEMENT_PRECEDENCE = 50


class FiftyMoveRule(Rule):
    """End the game in a draw after so many plies without a capture and without a man moving."""

    default_name = "Fifty-move rule"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: How many plies without progress end the game, and which piece kinds
            count as progress. The default of a hundred plies is fifty moves by each side.
        """
        return [
            Field("plies", "integer", "Plies without progress", 100, minimum=2),
            Field("progress_kinds", "text", "Kinds that reset the count", "man"),
        ]

    def attach(self) -> None:
        """Start the count at zero.

        The count is only ever forgotten when the whole game is, which is what resetting the
        runtime state does. Attaching is also called when a rule set is handed to a game
        mid-game, and a count wiped there would be a count restarted in the middle of a
        drawn-out game.

        Returns:
            None
        """
        self.state.setdefault("plies", 0)

    def reset_count(self) -> None:
        """Start the count again from zero, for a new game.

        Returns:
            None
        """
        self.state["plies"] = 0

    def on_move_made(self, position: Any, move: Move) -> None:
        """Count the move, resetting the count when it made progress.

        The piece read is the one that moved rather than whatever stands on the destination
        afterwards: a man that has just been crowned is a king by the time anyone looks, and
        a count that could not tell the difference would never reset on a crowning step.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        piece = move.piece
        kinds = [kind.strip() for kind in str(self.value.get("progress_kinds", "")).split(",")]
        kinds = [kind for kind in kinds if kind]
        moved = piece.getType() in kinds if piece is not None else False
        if moved or is_capture(move):
            self.state["plies"] = 0
            return
        self.state["plies"] = self.state.get("plies", 0) + 1

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw once the count of plies without progress is reached.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None.
        """
        if self.state.get("plies", 0) < int(self.value.get("plies", 100)):
            return None
        return Result(KIND_DRAW, precedence=FIFTY_MOVE_PRECEDENCE, reason="fifty-move rule")


class InsufficientMaterialRule(Rule):
    """End the game in a draw once neither side has a man left that could be crowned."""

    default_name = "Insufficient material"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: The piece kinds whose absence on both sides ends the game. The
            default is the man, because a side with kings only can never gain anything: a king
            cannot be crowned, so it can only ever be taken, and two sides that can only lose
            pieces have no way to end it.
        """
        return [
            Field("man_kind", "text", "Kind that can still be crowned", "man"),
        ]

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw when neither side has a man left.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None when somebody can still crown something.
        """
        man_kind = self.value.get("man_kind", "man")
        for color in (1, -1):
            if kinds_of(position, color).get(man_kind, 0):
                return None
        return Result(
            KIND_DRAW,
            precedence=INSUFFICIENT_MATERIAL_PRECEDENCE,
            reason="insufficient material",
        )


class MutualAgreementRule(Rule):
    """End the game in a draw when both players agree to one."""

    default_name = "Draw by agreement"

    def attach(self) -> None:
        """Clear any offer left over from a previous game.

        Returns:
            None
        """
        self.state.setdefault("offered", False)
        self.state.setdefault("accepted", False)

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
        self.state["accepted"] = False

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
