"""Bishop colour confinement.

A bishop never changes the shade of square it started on, so it can only ever reach half the
board. The rule records where each piece of a confined kind first stood and refuses any move
that would change its shade.
"""

from typing import Any, Dict, List

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule
from .attacks import square_color


class BishopColourRule(Rule):
    """Confine each bishop to the shade of square it started on."""

    default_name = "Bishop colour"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: The piece kinds this rule confines.
        """
        return [Field("kinds", "text", "Confined kinds", "bishop")]

    def attach(self) -> None:
        """Forget every starting square from a previous game.

        Returns:
            None
        """
        self.state["origins"] = {}

    def origins(self) -> Dict[int, int]:
        """Return the recorded starting shade of each confined piece.

        Returns:
            Dict[int, int]: Piece identity to shade.
        """
        return self.state.setdefault("origins", {})

    def on_move_made(self, position: Any, move: Move) -> None:
        """Record where a newly arrived confined piece appeared.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        piece = position.get_piece_at(move.end_pos)
        if piece is not None and self._is_confined(piece):
            self.origins().setdefault(id(piece), square_color(position, move.end_pos))

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a confined piece any move that would change its shade.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False when the move would change the piece's shade, or when the piece has
            no recorded starting square and so has no business moving yet.
        """
        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None or not self._is_confined(piece):
            return True
        origin = self.origins().get(id(piece))
        if origin is None:
            return True
        return square_color(position, move.end_pos) == origin

    def _is_confined(self, piece: Any) -> bool:
        """Report whether this rule confines a piece.

        Args:
            piece: The piece to test.

        Returns:
            bool: True when the piece's kind is one this rule confines.
        """
        kinds = self.value.get("kinds")
        if isinstance(kinds, str):
            kinds = [item.strip() for item in kinds.split(",") if item.strip()]
        return piece.getType() in (kinds or ["bishop"])
