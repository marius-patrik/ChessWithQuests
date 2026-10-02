"""Pawn promotion.

The far rank is derived from the piece's own declared forward vector rather than from the
number eight, so the rule works on a board of any size.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule


class PromotionRule(Rule):
    """Offer every choice of replacement piece, and insist on one."""

    default_name = "Promotion"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: The piece kinds a promotion may choose from, in the order the form
            should offer them. Orthodox chess allows all four, and underpromotion is a real
            answer rather than a curiosity, so the default offers all four.
        """
        return [
            Field(
                "promotable_kinds",
                "text",
                "Kinds that promote",
                "pawn",
            ),
            Field(
                "promotion_kinds",
                "choice",
                "Promote to",
                ("queen", "rook", "bishop", "horse"),
                choices=("queen", "rook", "bishop", "horse"),
            ),
        ]

    def promotion_row(self, position: Any, piece: Any) -> Optional[int]:
        """Return the row on which this piece promotes.

        Whether a piece promotes is declared, not inferred. A rook and a king both have a
        purely vertical step, so deriving the rank from geometry promoted every piece that
        could slide sideways on the far rank: no queen or rook could ever reach it, and a king
        walking its own back rank turned into a knight.

        Args:
            position: The board to read.
            piece: The piece asking.

        Returns:
            Optional[int]: The row a single-square forward step reaches, or None when this
            piece does not promote.
        """
        if not self._promotes(piece):
            return None
        origin = _origin(position, piece)
        if origin is None:
            return None
        for dr, dc in piece.getDirections() or []:
            if dc != 0 or dr == 0:
                continue
            return position.rows - 1 if dr > 0 else 0
        return None

    def _promotes(self, piece: Any) -> bool:
        """Report whether this piece is one that promotes.

        Args:
            piece: The piece asking.

        Returns:
            bool: True when the piece's kind is one of the declared promoting kinds.
        """
        configured = _split(self.value.get("promotable_kinds")) or ["pawn"]
        return piece is not None and piece.getType() in configured

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer one promoting move per choice of replacement piece.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The promoting moves, or nothing when the piece is not promoting.
        """
        target_row = self.promotion_row(position, piece)
        if target_row is None:
            return []

        origin = _origin(position, piece)
        if origin is None:
            return []

        take_only = [
            vector
            for vector in (piece.getAttackDirections() or [])
            if vector not in (piece.getDirections() or [])
        ]
        destinations = []
        for dr, dc in piece.getDirections() or []:
            landing = (origin[0] + dr, origin[1] + dc)
            if position.is_within_bounds(*landing) and position.get_piece_at(landing) is None:
                destinations.append(landing)
        for dr, dc in take_only:
            landing = (origin[0] + dr, origin[1] + dc)
            if not position.is_within_bounds(*landing):
                continue
            target = position.get_piece_at(landing)
            if target is not None and target.getColor() != piece.getColor():
                destinations.append(landing)

        offered: List[Move] = []
        for destination in destinations:
            if destination[0] != target_row:
                continue
            for kind in self._kinds():
                offered.append(
                    Move(
                        start_pos=origin,
                        end_pos=destination,
                        piece=piece,
                        move_type="promotion",
                        promotion_piece=_make_promotion(piece, kind),
                    )
                )
        return offered

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a move onto the far rank that has not chosen what it becomes.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for an undecorated move onto the promotion rank, True otherwise.
        """
        if move.promotion_piece is not None:
            return True
        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None:
            return True
        if self.promotion_row(position, piece) != move.end_pos[0]:
            return True
        return bool(self._kinds()) and move.move_type == "promotion"

    def _kinds(self) -> List[str]:
        """Return the kinds this rule may promote to.

        Returns:
            List[str]: The configured choices, defaulting to a single queen.
        """
        configured = self.value.get("promotion_kinds")
        if isinstance(configured, str):
            return [configured]
        if configured:
            return list(configured)
        return ["queen"]


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


def _make_promotion(piece: Any, kind: str) -> Any:
    """Build the replacement piece for a promotion.

    Args:
        piece: The piece promoting, whose colour the replacement takes.
        kind: The piece type descriptor to promote to.

    Returns:
        Any: A piece of that kind and colour, or None when the kind is unknown.
    """
    from games.chess.pieces.bishop import Bishop
    from games.chess.pieces.horse import Horse
    from games.chess.pieces.queen import Queen
    from games.chess.pieces.rook import Rook

    catalogue = {"queen": Queen, "rook": Rook, "bishop": Bishop, "knight": Horse, "horse": Horse}
    factory = catalogue.get(kind)
    if factory is None:
        raise ValueError(f"{kind!r} is not a piece kind a pawn can promote to")
    return factory(piece.getColor())


def _origin(position: Any, piece: Any) -> Optional[tuple]:
    """Find where a piece stands.

    Args:
        position: The board to read.
        piece: The piece to find.

    Returns:
        Optional[tuple]: Its square, or None when it is not on the board.
    """
    for r in range(position.rows):
        for c in range(position.cols):
            if position.get_piece_at((r, c)) is piece:
                return (r, c)
    return None
