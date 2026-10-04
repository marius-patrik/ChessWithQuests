"""King: one square diagonally, forwards or backwards.

A king is a man that has been crowned, and everything that changes is declared here and
nowhere else: it steps instead of sliding, and it jumps backwards as well as forwards. Both
follow from the data rather than from a special case — `max_steps=1` is a one-square step,
and all four diagonals are declared so a jump along any of them is available.

This is the WCDF rulebook's king, and it is what ships. Rule 1.17: an ordinary move of a king
"is from one square diagonally forward or backward, left or right to an immediately
neighbouring vacant square", and rule 1.21 gives its capturing move as a man's "but may be in
a forward or backward direction" — one square over one piece onto the square beyond.

The two kings are genuinely different games. The flying king of international, Brazilian,
Czech and Dutch draughts slides and jumps any distance along a diagonal, and the two disagree
about which positions a piece has a move in. Flying is one line of data here: `max_steps=None`
slides and `max_steps=1` steps, so a variant that wants the international game changes this
number and nothing else. Every rule above reads the same number — a jump of one square or of
any distance is `jump_reach`, which is this piece's declared step length. Nothing else in the
configuration has to know which of the two games it is playing.

Whether a man may be crowned at all is a rule, and so is how many kings a side may hold. This
piece does not decide either.
"""

from typing import Any, List, Tuple

from model.pieces.piece import Piece

#: Every diagonal, which is the whole of a king's movement.
DIRECTIONS: List[Tuple[int, int]] = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class King(Piece):
    """Steps one square along any diagonal, and jumps the same way."""

    def __init__(self, color: Any, piece_type: str = "king"):
        """Initialize a King piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "king").
        """
        super().__init__(
            symbols=("⛁", "⛃"),
            fen="K",
            color=color,
            piece_type=piece_type,
            vectors=DIRECTIONS,
            attack_vectors=DIRECTIONS,
            can_jump=False,
            name="King",
            max_steps=1,
        )
