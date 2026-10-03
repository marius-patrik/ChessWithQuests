"""No piece ever ends a move on an occupied square.

This is the one draughts rule the engine cannot be asked to enforce, and the reason it is
worth a file of its own.

The engine builds a king's quiet moves from what the king *declares*: four diagonals, and
along each of them every square up to and including the first one with something on it. That
is right for a chess bishop and wrong for a draughts king, because in draughts a capture is
never a step onto the piece taken — the piece taken is not the square landed on, the mover
leaps over it onto the square beyond. A king therefore has no move that ends on an occupied
square, ever, and the vector-driven generator offers one anyway: the step onto the man
immediately in front of it, offered as a `capture` because the destination holds an enemy.

Left alone, that move is *usually* refused by accident. With a compulsory capture in force,
`CaptureRule` refuses any move that takes no pieces while a chain exists, and while no chain
exists it refuses it too, so the king appears to be unable to do it. Switch the compulsory
capture off and the accident evaporates: the king walks onto the man and removes it, which is
a move in no variant of draughts there is.

So the geometry is stated here rather than left to a rule about captures to catch on the way
past. `permits_move` is the only hook needed, and it asks one question of one square.
"""

from typing import Any, List, Tuple

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule


class LandingRule(Rule):
    """Refuse any move that would end on a square something already stands on."""

    default_name = "Empty landing square"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: None. The rule has nothing to configure: a draughts piece either
            has an empty square to land on or it does not move.
        """
        return []

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a move whose destination is occupied.

        The whole chain is tested, not only its last square. Every square a chain passes
        through has to be empty as it passes over it, and a chain that has already lifted
        what stood there is legal — but a chain whose route is described through a square
        that still holds something describes a jump that cannot be made.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False when the move would end on an occupied square, True otherwise.
        """
        if not position.is_within_bounds(move.end_pos[0], move.end_pos[1]):
            return False
        if position.get_piece_at(move.end_pos) is not None:
            return False

        for square in self._route(move):
            if position.get_piece_at(square) is not None:
                return False
        return True

    @staticmethod
    def _route(move: Move) -> Tuple[Tuple[int, int], ...]:
        """Return the squares a chain passes through, if this move is a chain.

        A chain of jumps is a `HopMove`, which carries its own route; every other move the
        engine builds is a single step and has none to check. Reading the attribute and
        defaulting it to nothing is how this rule stays ignorant of the class that carries it.

        Args:
            move: The move being considered.

        Returns:
            Tuple[Tuple[int, int], ...]: The squares to test, empty for a move that is not a
            chain.
        """
        hops = getattr(move, "hops", ())
        return tuple(hops or ())


__all__ = ["LandingRule"]
