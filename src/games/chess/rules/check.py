"""Check, checkmate and stalemate.

The three are one family because they are one question asked at three levels: is the royal
piece attacked, and does the player have any legal move at all.
"""

from typing import Any, List, Optional

from model.game.rule import KIND_WIN, Result, Rule
from .attacks import find_piece, has_legal_move, is_attacked, opponent

#: Precedence of each proposal, so two rules firing at once is deterministic.
CHECKMATE_PRECEDENCE = 100
STALEMATE_PRECEDENCE = 90


def royal_square(position: Any, color: int, royal_kind: str = "king") -> Optional[tuple]:
    """Find a colour's royal piece.

    Args:
        position: The board to read.
        color: Colour to look for.
        royal_kind: The declared royal piece kind.

    Returns:
        Optional[tuple]: The square the royal piece stands on, or None.
    """
    return find_piece(position, royal_kind, color)


def in_check(position: Any, color: int, royal_kind: str = "king") -> bool:
    """Report whether a colour's royal piece is attacked.

    Args:
        position: The board to read.
        color: Colour to test.
        royal_kind: The declared royal piece kind.

    Returns:
        bool: True when the royal piece is attacked, or when there is no royal piece to
        attack.
    """
    square = royal_square(position, color, royal_kind)
    if square is None:
        return False
    return is_attacked(position, square, opponent(color))


class CheckRule(Rule):
    """Report that the player to move is in check, while the game continues."""

    default_name = "Check"

    def value_fields(self) -> List:
        """Declare the configured value this rule exists to carry.

        Returns:
            List: The royal piece kind, so this rule can be judged on its own.
        """
        from model.game.field import Field

        return [Field("royal_kind", "text", "Royal piece kind", "king")]

    def status(self, position: Any) -> Optional[str]:
        """Report `Check` while the player to move is in check.

        Args:
            position: The board as it stands.

        Returns:
            Optional[str]: `Check`, or None when nothing is wrong.
        """
        kind = self.value.get("royal_kind")
        if kind and in_check(position, self.active_color, kind):
            return "Check"
        return None


class CheckmateRule(Rule):
    """End the game when the player to move is in check and cannot answer."""

    default_name = "Checkmate"

    def value_fields(self) -> List:
        """Declare the configured value this rule exists to carry.

        Returns:
            List: The royal piece kind.
        """
        from model.game.field import Field

        return [Field("royal_kind", "text", "Royal piece kind", "king")]

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a win for the opponent when the position is mate.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A win for the opponent, or None when the game continues.
        """
        kind = self.value.get("royal_kind")
        color = self.active_color
        if not kind or not in_check(position, color, kind):
            return None
        if has_legal_move(position, color, self.rules):
            return None
        return Result(
            KIND_WIN,
            precedence=CHECKMATE_PRECEDENCE,
            winner=opponent(color),
            reason="checkmate",
        )


class StalemateRule(Rule):
    """End the game in a draw when the player to move has no legal move and is not in check."""

    default_name = "Stalemate"

    def value_fields(self) -> List:
        """Declare the configured value this rule exists to carry.

        Returns:
            List: The royal piece kind.
        """
        from model.game.field import Field

        return [Field("royal_kind", "text", "Royal piece kind", "king")]

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a draw when the player to move is stuck without being in check.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A draw, or None when the game continues.
        """
        kind = self.value.get("royal_kind")
        color = self.active_color
        if not kind or in_check(position, color, kind):
            return None
        if has_legal_move(position, color, self.rules):
            return None
        return Result("draw", precedence=STALEMATE_PRECEDENCE, reason="stalemate")
