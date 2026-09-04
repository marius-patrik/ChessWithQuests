"""King chess piece implementation with 8-direction step movement and castling state."""

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class King(Piece):
    """King chess piece with 1-square movement in any of 8 directions and moved-state tracking."""

    def __init__(self, color: int, piece_type: str = "king"):
        """Initialize a King piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece type descriptor (default: "king").
        """
        vectors = [
            (0, 1),
            (0, -1),
            (1, 0),
            (-1, 0),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="King",
        )
        self._has_moved = False

    def hasMoved(self) -> bool:
        """Check whether the King has moved from its starting position.

        Returns:
            bool: True if the King has moved, False otherwise.
        """
        return self._has_moved

    def setMoved(self, moved: bool = True) -> None:
        """Update the King's moved state.

        Args:
            moved: Movement flag value (default: True).
        """
        self._has_moved = moved
