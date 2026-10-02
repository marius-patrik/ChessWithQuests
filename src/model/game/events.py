"""What the game tells a rule or a quest when something happened.

Rules and quests are the two code-driven layers, and neither may reach into the game to
find out what is going on. These value objects are what they are handed instead: one
description of a move that was made, and one of a game that ended. Every flag a rule or a
quest could want is a field here, so adding one is adding a field rather than reaching
deeper into the engine.
"""

from typing import Any, Dict, List, Optional, Tuple

#: Outcome kinds. A `Result` from the rule layer and a quest's own view of a finished game
#: both speak in these terms, so they cannot drift apart.
OUTCOME_WIN = "win"
OUTCOME_LOSS = "loss"
OUTCOME_DRAW = "draw"


class MoveEvent:
    """One move that has been played, and what it did.

    Every flag defaults to false or None so a caller that knows less than the full picture
    can still describe what it knows. A rule or a quest that needs a fact the caller did not
    supply then has nothing to act on rather than a wrong answer.
    """

    def __init__(
        self,
        move: Any,
        position: Any,
        color: int,
        piece_type: str = "",
        captured_piece_type: Optional[str] = None,
        is_check: bool = False,
        in_check: bool = False,
        is_castling: bool = False,
        is_en_passant: bool = False,
        is_promotion: bool = False,
        index: int = 0,
    ):
        """Describe a move that has been played.

        Args:
            move: The `Move` that was executed.
            position: The board as it stands after the move.
            color: Colour of the player who made the move.
            piece_type: Piece type descriptor of the piece that moved.
            captured_piece_type: Piece type descriptor of what was captured, if anything.
            is_check: True when the move left the opponent in check.
            in_check: True when the player who moved was in check before moving.
            is_castling: True for a castling move.
            is_en_passant: True for an en passant capture.
            is_promotion: True for a move that promoted a piece.
            index: Zero-based position of this move in the game.
        """
        self.move = move
        self.position = position
        self.color = color
        self.piece_type = piece_type
        self.captured_piece_type = captured_piece_type
        self.is_check = is_check
        self.in_check = in_check
        self.is_castling = is_castling
        self.is_en_passant = is_en_passant
        self.is_promotion = is_promotion
        self.index = index

    @property
    def is_capture(self) -> bool:
        """Whether the move captured a piece.

        Returns:
            bool: True when something was captured.
        """
        return self.captured_piece_type is not None

    @property
    def start(self) -> Tuple[int, int]:
        """The square the move started from.

        Returns:
            Tuple[int, int]: The starting coordinates.
        """
        return tuple(self.move.start_pos)

    @property
    def end(self) -> Tuple[int, int]:
        """The square the move ended on.

        Returns:
            Tuple[int, int]: The destination coordinates.
        """
        return tuple(self.move.end_pos)

    def __repr__(self) -> str:
        """Return a debugging representation naming the move.

        Returns:
            str: The colours, squares and flags of the move.
        """
        return (
            f"MoveEvent(#{self.index} color={self.color} {self.start}->{self.end} "
            f"capture={self.captured_piece_type!r} check={self.is_check})"
        )


class ResultEvent:
    """A game that has ended, and everything needed to judge it."""

    def __init__(
        self,
        outcome: str,
        winner: Optional[int] = None,
        reason: str = "",
        history: Optional[List[MoveEvent]] = None,
        position: Any = None,
        players: Optional[Dict[int, Any]] = None,
    ):
        """Describe a game that has ended.

        Args:
            outcome: One of `OUTCOME_WIN`, `OUTCOME_LOSS` or `OUTCOME_DRAW`.
            winner: Colour of the winner, or None for a draw.
            reason: Why the game ended, for example `checkmate` or `resignation`.
            history: Every move event of the game, in order.
            position: The board as it stood at the end.
            players: The players by colour, keyed by colour value.
        """
        self.outcome = outcome
        self.winner = winner
        self.reason = reason
        self.history: List[MoveEvent] = list(history) if history else []
        self.position = position
        self.players: Dict[int, Any] = players if players is not None else {}

    def captures_by(self, color: int) -> int:
        """Count how many pieces a colour captured over the whole game.

        Args:
            color: Colour to count for.

        Returns:
            int: The number of moves by that colour that captured something.
        """
        return sum(1 for event in self.history if event.color == color and event.is_capture)

    def captures_against(self, color: int) -> int:
        """Count how many pieces a colour lost over the whole game.

        Args:
            color: Colour to count for.

        Returns:
            int: The number of moves by the opponent that captured something.
        """
        return sum(1 for event in self.history if event.color != color and event.is_capture)

    def moves_by(self, color: int) -> int:
        """Count how many moves a colour played.

        Args:
            color: Colour to count for.

        Returns:
            int: The number of moves that colour made.
        """
        return sum(1 for event in self.history if event.color == color)

    def __repr__(self) -> str:
        """Return a debugging representation naming the outcome.

        Returns:
            str: The outcome, winner, reason and length of the game.
        """
        return (
            f"ResultEvent(outcome={self.outcome!r}, winner={self.winner!r}, "
            f"reason={self.reason!r}, moves={len(self.history)})"
        )
