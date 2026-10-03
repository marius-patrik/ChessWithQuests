"""King: any distance along a diagonal, forwards or backwards.

A king is a man that has been crowned, and everything that changes is declared here and
nowhere else: it slides instead of stepping, and it jumps backwards as well as forwards.
Both follow from the data rather than from a special case — no declared maximum step means
the engine already slides it as far as the board allows, and all four diagonals are declared
so a jump along any of them is available.

**This is the flying king, and the WCDF rulebook for English draughts does not have one.** Its
"ordinary move of a king" is "from one square diagonally forward or backward, left or right
to an immediately neighbouring vacant square", and its "capturing move of a king" is that of a
man with the direction widened — one square over one piece onto the square beyond. Flying
kings are the rule in international, Brazilian, Czech and Dutch draughts and the short king is
the rule in English, American, Italian and Turkish draughts, and the two disagree about which
positions a king has a move in, so they are genuinely different games.

Flying is kept here because this configuration was specified with it, and because the two are
one line of data: `max_steps=None` slides, `max_steps=1` steps. A variant that wants the
rulebook's king declares `max_steps=1`, and every rule above reads that same number — a jump
of one square or of any distance is `jump_reach`, which is this piece's declared step length.
Nothing else in the configuration has to know which of the two games it is playing.

Whether a man may be crowned at all is a rule, and so is how many kings a side may hold. This
piece does not decide either.
"""

from typing import Any, List, Tuple

from model.pieces.piece import Piece

#: Every diagonal, which is the whole of a king's movement.
DIRECTIONS: List[Tuple[int, int]] = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class King(Piece):
    """Slides any distance along any diagonal, and jumps the same way."""

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
            max_steps=None,
        )
