"""Which piece kind is royal.

Whether a position has a king is a rule, not a lookup by type name. Declaring it here means
the validator never has to know what a king is — and a configuration with no such rule simply
has no royal piece, which is a game that has not been heard of.
"""

from typing import Any, List

from model.game.field import Field
from model.game.rule import Rule


class RoyalPieceKind(Rule):
    """Declare which piece kind may be put in check."""

    default_name = "Royal piece"

    def value_fields(self) -> List[Field]:
        """Declare the configured value this rule exists to carry.

        Returns:
            List[Field]: The royal kind. The engine reads a rule that declares a value of
            this name; it does not read the value's contents.
        """
        return [Field("royal_kind", "text", "Royal piece kind", "king")]
