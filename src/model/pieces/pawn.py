"""Pawn chess piece implementation with forward steps and diagonal capture vectors."""

from typing import Any, List, Tuple

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Pawn(Piece):
    """Pawn piece with forward movement, diagonal capture, and 2-step first advance.

    Attributes:
        _initial_vectors: Move vectors for the two-square initial pawn push.
        _has_moved: Boolean tracking if the pawn has left its starting rank.
    """

    def __init__(self, color: Any, piece_type: str = "pawn"):
        """Initialize a Pawn piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "pawn").
        """
        direction = 1 if color == 1 or color == "white" else -1
        vectors = [(direction, 0)]
        attack_vectors = [(direction, 1), (direction, -1)]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=attack_vectors,
            can_jump=False,
            name="Pawn",
        )
        self._initial_vectors = [(direction * 2, 0)]
        self._has_moved = False

    def hasMoved(self) -> bool:
        """Check whether the pawn has moved from its initial square.

        Returns:
            bool: True if the pawn has moved, False otherwise.
        """
        return self._has_moved

    def setMoved(self, moved: bool = True) -> None:
        """Set whether the pawn has moved.

        Args:
            moved: New moved state boolean (default: True).
        """
        self._has_moved = moved

    def getInitialVectors(self) -> List[Tuple[int, int]]:
        """Return the vectors available on the pawn's first move.

        Returns:
            List[Tuple[int, int]]: List containing the 2-square advance vector.
        """
        return self._initial_vectors
