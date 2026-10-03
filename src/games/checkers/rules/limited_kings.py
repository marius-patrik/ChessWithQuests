"""How many kings a side may hold.

A man that reaches the far row becomes a king, and a side may end up with a great many of
them: in English draughts a man is not removed when it is crowned, it keeps playing as a
king, so twelve men can become twelve kings.

**No draughts rulebook caps that number**, and this rule shipped with a cap of two, which is
not a variant anybody plays — it is a bug that only shows up in a real game. It refuses the
third crowning of a side, silently, in the middle of a game that was otherwise being played
correctly: a man walks onto the crown row and is simply not offered, with nothing to say so,
and the man sits there for ever unable to advance. A random-playout sweep found three such
positions in 2885, all of them a man one step from crowning beside a side that already held
two kings. The default is therefore the largest number a side can reach, `PIECES_PER_SIDE`,
which makes the rule inert for English draughts and available for the variants that do cap
kings.

The cap is a `permits_move` and not a `permits_crowning`, because the rule layer has exactly
five hooks and this is one of them: a crowning move that would take a side over its limit is
simply not permitted. The crowning itself is still offered; it is refused for the side that
would exceed the limit, which is the difference between "this man may not be crowned" and
"this man may not be crowned *yet*".
"""

from typing import Any, List

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule

from ..board import PIECES_PER_SIDE
from .geometric import kinds_of


class LimitedKingsRule(Rule):
    """Refuse a crowning that would take a side over its limit on kings."""

    default_name = "Limited kings"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: How many kings a side may hold, and the kind a man is crowned as.
            The limit is a count, not a switch, and the default is as large as a side can
            ever be, so that a game of English draughts is not silently constrained.
        """
        return [
            Field("max_kings", "integer", "Kings a side may hold", PIECES_PER_SIDE, minimum=0),
            Field("king_kind", "text", "Crowned kind", "king"),
        ]

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a crowning that would leave this side with more kings than it may hold.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for a crowning that takes the mover over the limit, True otherwise.
            A move that crowns nothing is never refused here, and a side already holding as
            many kings as it may is simply left unable to crown until it loses one.
        """
        if move.promotion_piece is None:
            return True

        kind = self.value.get("king_kind", "king")
        if move.promotion_piece.getType() != kind:
            return True

        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None:
            return True

        limit = int(self.value.get("max_kings", PIECES_PER_SIDE))
        held = kinds_of(position, piece.getColor()).get(kind, 0)
        return held < limit
