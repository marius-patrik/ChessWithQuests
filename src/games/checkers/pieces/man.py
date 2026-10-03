"""Man: one square forward diagonally, and crowned on reaching the far row.

Nothing in the engine knows this is a man. It knows that a vector in `getDirections()` moves
a piece to an empty square one step away, and that a piece declaring no attack vectors takes
nothing by walking onto a square.

That last part is the point. A draughts capture is not a step onto an occupied square, it is
a leap over one onto the square beyond, and the leap is a rule — the engine's three generic
movement shapes cannot express "over one piece onto the empty square after it", which is
exactly why a game whose capture is a jump contributes its captures as moves a rule offers.

`max_steps=1` is what makes this piece a one-square mover, and it is also read as the reach
of one jump: a man jumps exactly one square over the piece it takes. A king declares no
maximum step, and that is read the other way — it may slide as far as the board allows, and
its jumps may travel any distance too.
"""

from typing import Any

from model.pieces.piece import Piece


class Man(Piece):
    """Moves one square forward diagonally, and is crowned on the far row."""

    def __init__(self, color: Any, piece_type: str = "man"):
        """Initialize a Man piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "man").

        Raises:
            ValueError: If `color` is neither a side. A man with no side has no forward
                direction, and declaring one arbitrarily would let it walk off the board.
        """
        if color not in (1, -1, "white", "black"):
            raise ValueError(f"{color!r} is not a side; a man needs one to know its direction")
        direction = 1 if color == 1 or color == "white" else -1
        super().__init__(
            symbols=("⛀", "⛂"),
            # Declared only so that a writer in the engine which insists on a character for
            # every piece is not handed one that has none. What an English draughts position
            # is written as is that writer's business and not this piece's.
            fen="W",
            color=color,
            piece_type=piece_type,
            vectors=[(direction, -1), (direction, 1)],
            attack_vectors=[],
            can_jump=False,
            name="Man",
            max_steps=1,
        )
