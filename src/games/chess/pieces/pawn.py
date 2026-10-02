"""Pawn: a piece whose movement vectors and attack vectors are different shapes.

Nothing in the engine knows this is a pawn. It knows that a vector present in
`getDirections()` but not in `getAttackDirections()` is a move and not a capture, and that a
vector in `initial_vectors` is available once.
"""

from typing import Any, List, Tuple

from model.pieces.piece import Piece


class Pawn(Piece):
    """Advances straight, takes diagonally, and may make one long first advance."""

    def __init__(self, color: Any, piece_type: str = "pawn"):
        """Initialize a Pawn piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "pawn").
        """
        direction = 1 if color == 1 or color == "white" else -1
        super().__init__(
            symbols=("♙", "♟"),
            fen="P",
            color=color,
            piece_type=piece_type,
            vectors=[(direction, 0)],
            attack_vectors=[(direction, 1), (direction, -1)],
            can_jump=False,
            name="Pawn",
            max_steps=1,
            initial_vectors=[(direction * 2, 0)],
        )
