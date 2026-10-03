"""Crowning: a man that reaches the far row by stepping becomes a king.

The quiet man moves are the engine's own — it walks a piece one square along a declared
diagonal to an empty square, and that is exactly what a man does. What the engine cannot know
is that landing on the far row changes what the piece *is*, so this rule does two things
about that row and nothing else: it offers the crowned version of a step onto it, and it
refuses a step onto it that has not been crowned.

The crowning row is derived from the piece's declared forward diagonal rather than from the
number eight, the same way the engine's chess promotion derives its rank, so the question
works on a board of any size and a man's far row is whichever end it is travelling towards.
Whether a side may hold as many kings as it likes is `limited_kings.py`, not here: crowning
is about what one man becomes, and the cap is about how many of that there may be.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule
from .geometric import crowning_row, crown, origin_of

#: The move type a crowning step carries.
CROWNING_TYPE: str = "crowning"


class CrowningRule(Rule):
    """Offer the crowned version of a step onto the far row, and refuse an uncrowned one."""

    default_name = "Crowning"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: The piece kinds that are crowned on reaching the far row.
        """
        return [Field("crowning_kinds", "text", "Kinds that are crowned", "man")]

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer one crowned move for every step this piece may make onto its far row.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The crowned steps, or nothing when this piece cannot be crowned or
            cannot step onto the far row.
        """
        target_row = crowning_row(position, piece, self.value.get("crowning_kinds"))
        if target_row is None:
            return []

        origin = origin_of(position, piece)
        if origin is None:
            return []

        king = crown(piece)
        if king is None:
            return []

        offered: List[Move] = []
        for dr, dc in piece.getDirections() or []:
            landing = (origin[0] + dr, origin[1] + dc)
            if not position.is_within_bounds(*landing) or landing[0] != target_row:
                continue
            if position.get_piece_at(landing) is not None:
                continue
            offered.append(
                Move(
                    start_pos=origin,
                    end_pos=landing,
                    piece=piece,
                    move_type=CROWNING_TYPE,
                    promotion_piece=king,
                )
            )
        return offered

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a step onto the far row by a piece that has not become a king.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for an undecorated step onto this piece's crowning row, True
            otherwise. A move that already carries a king with it is permitted, and so is any
            move by a kind that is not crowned.
        """
        if move.promotion_piece is not None:
            return True
        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None:
            return True
        if crowning_row(position, piece, self.value.get("crowning_kinds")) != move.end_pos[0]:
            return True
        return False

    def crowning_row(self, position: Any, piece: Any) -> Optional[int]:
        """Return the row on which this piece is crowned, if it can be crowned at all.

        Args:
            position: The board to read.
            piece: The piece asking.

        Returns:
            Optional[int]: The crowning row, or None when this piece is never crowned.
        """
        return crowning_row(position, piece, self.value.get("crowning_kinds"))
