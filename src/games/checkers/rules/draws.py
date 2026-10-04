"""The ways a game of draughts ends without a winner, and the rulebook's own words for each.

Each is a rule that proposes; none imposes. Precedence makes two firing at once
deterministic, and every one of them is switchable, because at what value a game is drawn is
configuration and whether it is drawn at all is the player's.

The fifty-move rule of draughts is not the fifty-move rule of chess. A draughts game is drawn
after so many plies without *progress*, and progress is two things: taking a piece, or moving
a man. Moving a king is not progress, because a king can only ever retrace ground it has
already covered, so fifty moves of shuffling kings have advanced nothing. A man that steps
  onto the far row is progress even though it is crowned on arrival, because it got there.
  The default is the rulebook's eighty plies: rule 1.32.2 draws the game where neither player
  has advanced an uncrowned man nor had a piece taken "during their own previous 40 moves",
  which is forty moves each. The field is configurable so a club playing a longer count can set
  one.

  **These are the rulebook's three draws and no others.** Article 1.32 lists them: agreement
  (1.32), the same position for the third time (1.32.1), and forty moves by each side without
  advancing a man or removing a piece (1.32.2). There is no fourth. This configuration used to
  carry one — a draw once neither side had a man left — which no draughts rulebook has and which
  was not even true of the endgame it was meant to describe, since two kings really can be beaten
  by one. It was removed rather than switched off, because a rule the rulebook does not have is
  not a variant somebody plays; it is a mistake, and the notes record that it was here.

  **One divergence remains, and it is deliberate.** Rule 1.32.1 is a *claim*: a player
  demonstrates to the referee that their next move would create the position for the third time.
  This engine has no referee and no claim to make, so the rule proposes the draw itself. The
  chess configuration's repetition rule diverges in the same way and for the same reason, and
  both are recorded in `notes/object_model.md`.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import KIND_DRAW, Result, Rule
from .capture import is_capture
from .geometric import kinds_of

#: Precedence of each draw, so two firing at once is deterministic.
REPETITION_PRECEDENCE = 80
FIFTY_MOVE_PRECEDENCE = 60
AGREEMENT_PRECEDENCE = 50


class FiftyMoveRule(Rule):
    """End the game in a draw after so many plies without a capture and without a man moving."""

    default_name = "Fifty-move rule"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: How many plies without progress end the game, and which piece kinds
            count as progress. The default of eighty plies is the rulebook's forty moves by
            each side.
        """
        return [
            Field("plies", "integer", "Plies without progress", 80, minimum=2),
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
        # Assign, not setdefault: `attach` is what a new game calls, and a rule that
        # only defaults its state on first sight carries the last game's counter into
        # the next one.
        self.state["plies"] = 0

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
        if self.state.get("plies", 0) < int(self.value.get("plies", 80)):
            return None
        return Result(KIND_DRAW, precedence=FIFTY_MOVE_PRECEDENCE, reason="fifty-move rule")


class ThreefoldRepetitionRule(Rule):
    """End the game in a draw when one position has occurred three times.

    Rulebook rule 1.32.1: a player may demonstrate "that with their next move they would create
    the same position for the third time during the game". The rulebook makes that a claim, so a
    player has to notice it and ask; this engine has no claim to make and proposes the draw
    itself, which is what the chess configuration's own repetition rule does. The same
    divergence is recorded in `notes/object_model.md` for that rule.
    """

    default_name = "Threefold repetition"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: How many times a position must occur before the game is drawn. The
            default is the rulebook's three.
        """
        return [Field("occurrences", "integer", "Occurrences before a draw", 3, minimum=2)]

    def attach(self) -> None:
        """Forget every position seen in a previous game.

        A rule cannot record the position a game starts in: `attach` is handed the game, not the
        board, so it has nothing to record. The starting position is instead counted when it is
        first asked about.

        Returns:
            None
        """
        self.state["seen"] = {}

    def record(self, position: Any, active_color: int) -> int:
        """Count a position and report how many times it has now occurred.

        Asking whether the game is over must not itself create the repetition, so the position
        being judged is left as it stands.

        Args:
            position: The board as it stands.
            active_color: Whose turn it is, which is part of a position's identity.

        Returns:
            int: How many times this position has occurred.
        """
        seen = self.state.setdefault("seen", {})
        key = position_key(position, active_color)
        if key in seen:
            return seen[key]
        seen[key] = 1
        return 1

    def on_move_made(self, position: Any, move: Move) -> None:
        """Record the position the move produced.

        The position a move produces is judged with the *next* player to move, not the one who
        just moved, so that two records of one position are keyed the same way.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        mover = move.piece.getColor() if move.piece is not None else self.active_color
        self.record(position, -mover)

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw once a position has occurred often enough.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None.
        """
        limit = int(self.value.get("occurrences", 3))
        if self.record(position, self.active_color) < limit:
            return None
        return Result(KIND_DRAW, precedence=REPETITION_PRECEDENCE, reason="threefold repetition")


def position_key(position: Any, active_color: int) -> str:
    """Build the identity of a position for repetition purposes.

    Nothing in draughts remembers anything between positions: there is no castling and no
    en passant, so a position is its pieces and whose turn it is.

    Args:
        position: The board as it stands.
        active_color: Whose turn it is.

    Returns:
        str: A key covering the placement and the side to move.
    """
    parts = [str(active_color)]
    for row in range(position.rows):
        for col in range(position.cols):
            piece = position.get_piece_at((row, col))
            if piece is None:
                parts.append(".")
                continue
            parts.append(f"{piece.getType()}{'w' if piece.getColor() == 1 else 'b'}")
    return "|".join(parts)


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
