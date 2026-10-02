"""Loss on time.

Flag fall ends the game — but only when the opponent could actually have made something of
it. A player whose opponent has no mating material left and no time on the clock has drawn,
not lost.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.rule import KIND_DRAW, KIND_WIN, Result, Rule
from games.chess.rules.draws import _split
from games.chess.rules.attacks import kinds_of, opponent

#: Precedence, so a flag fall and a mate on the same position resolve deterministically.
FLAG_PRECEDENCE = 95


class FlagFallRule(Rule):
    """End the game when a player's clock reaches zero and the opponent can still mate."""

    default_name = "Flag fall"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: The royal piece kind and the kinds that can still deliver a mate.
        """
        return [
            Field("royal_kind", "text", "Royal piece kind", "king"),
            Field("mating_kinds", "text", "Mating material", "rook,queen,bishop,knight"),
        ]

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a result for whichever colour has run out of time.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A loss for the flagged player when the opponent still has
            mating material, a draw when not, or None while every clock is running.
        """
        if self.clock is None:
            return None

        for color in (1, -1):
            if self.clock.get_time(color) > 0:
                continue
            other = opponent(color)
            if self._has_mating_material(position, other):
                return Result(
                    KIND_WIN,
                    precedence=FLAG_PRECEDENCE,
                    winner=other,
                    reason="flag fall",
                )
            return Result(
                KIND_DRAW, precedence=FLAG_PRECEDENCE, reason="flag fall, no mating material"
            )
        return None

    def _has_mating_material(self, position: Any, color: int) -> bool:
        """Report whether a colour still has something that could deliver mate.

        Args:
            position: The board as it stands.
            color: Colour to inspect.

        Returns:
            bool: True when the colour still holds a piece that can mate, given that the
            opponent's clock has run out.
        """
        royal = self.value.get("royal_kind")
        if (
            self.value.get("king_takes_own_piece")
            and royal
            and kinds_of(position, color).get(royal, 0) > 1
        ):
            return True
        counts = kinds_of(position, color)
        return any(counts.get(kind, 0) for kind in _split(self.value.get("mating_kinds")))
