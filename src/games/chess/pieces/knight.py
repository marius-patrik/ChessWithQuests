"""Knight: the L-shaped piece that leaps.

The class is `Knight` and `Kun` is its Czech alias, which is the direction
`PRD.md` section 5 fixes: English is canonical, Czech is an alias bound to the same class.
The code said the opposite for a while — the class was `Horse` and `Knight` was the alias —
and the piece descriptor stayed `horse` throughout, which is a separate matter and is why
`_KIND_ALIASES` in `../rules/draws.py` accepts either spelling of a configured kind.

The descriptor is not the class name. `piece_type` is data a configuration chooses and puts
in its saved values, so it is left as `horse` rather than rewritten to `knight`; a stored
configuration that says `horse` keeps meaning the knight.
"""

from model.pieces.piece import Piece

#: The eight offsets a knight moves by.
VECTORS = [
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
]


class Knight(Piece):
    """Moves in an L-shape and can leap over pieces."""

    def __init__(self, color: int, piece_type: str = "horse"):
        """Initialize a Knight piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece type descriptor (default: "horse"). This is the configured
                kind, not the class name; see the module docstring.
        """
        super().__init__(
            symbols=("♘", "♞"),
            fen="N",
            color=color,
            piece_type=piece_type,
            vectors=VECTORS,
            attack_vectors=VECTORS,
            can_jump=True,
            name="Knight",
        )


#: Czech alias for `Knight`, as `PRD.md` section 5 and `Kůň` in the diagram require.
Kun = Knight
