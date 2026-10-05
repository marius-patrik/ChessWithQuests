"""King: one square in any of the eight directions.

`max_steps=1` is what makes it a one-square mover. The engine does not know it is a king;
whether it is royal is a rule, and that rule is chess's to declare.
"""

from typing import Any

from model.pieces.piece import Piece

DIRECTIONS = [
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
]


class King(Piece):
    """Moves exactly one square in any of the eight directions."""

    #: A pawn does not become the piece that ends the game. Whether this kind is *royal* is a
    #: rule — `royal_kind` is declared by a rule in this configuration's set, not by this file —
    #: but a piece that ends the game is not something a promotion produces, and that is this
    #: piece's own declaration to make.
    promotion_target = False

    def __init__(self, color: Any, piece_type: str = "king"):
        """Initialize a King piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece type descriptor (default: "king").
        """
        super().__init__(
            symbols=("♔", "♚"),
            fen="K",
            color=color,
            piece_type=piece_type,
            vectors=DIRECTIONS,
            attack_vectors=DIRECTIONS,
            can_jump=False,
            name="King",
            max_steps=1,
        )


#: Czech alias for `King`, as `PRD.md` section 5 and `Král` in the diagram require.
Kral = King
