"""Mandatory capture, and — as a variant — capturing as much as possible.

English draughts has one rule about taking, and one variant, and the difference between them
is not cosmetic:

- **A capture is compulsory.** While any capture is available to the side to move, no piece
  of that side may move quietly. This is one `permits_move` and it is checked against the
  whole side, not against the piece that happens to be moving: a man with nothing to take
  may not step aside because a different man three squares away has something. Once a chain
  is started it must be carried through to the end, which `chains.py` enforces by never
  offering a chain that could have gone further.
- **The most is the least** is *not* part of this game. The World Checkers Draughts
  Federation rulebook says that where two or more jumps are available "a player may select any
  one that they wish, not necessarily that which gains the most pieces", so `max_capture`
  ships **off**. It is a real rule of international, Brazilian, Czech, Italian and Spanish
  draughts, and a club that plays those wants it, so it is here as a switch — but a
  configuration that says it plays English draughts has to leave it off, and switching it on
  changes the game: at depth six of the opening the two disagree 36473 against 36768, which
  is why `tests/test_draughts_perft.py` gates both.

Switching `mandatory` off is the other half, and it changes the game rather than the code
path: a quiet move becomes legal beside a capture. Which value is right is configuration;
whether the rule is in force at all is the player's.

The chains themselves are contributed as moves. The engine's three generic movement shapes
are a step onto an empty square, a slide along an empty ray, and a step onto an occupied
square — and a draughts capture is none of them, since the piece taken is not the square
landed on. So the engine has nothing to offer here and the rule offers the whole chain
instead: one move, carrying every jump it makes and every piece it takes.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule

from ..moves import HopMove
from .chains import Chain, chains_for, side_chains_best
from .geometric import crowning_row, crown, origin_of

#: The move type a chain carries. Every rule that needs to tell a capture from a quiet move
#: reads this, so what "a capture" means is declared once.
CAPTURE_TYPE: str = "capture"


def is_capture(move: Optional[Move]) -> bool:
    """Report whether a move takes at least one piece.

    Args:
        move: The move being considered, or None.

    Returns:
        bool: True when the move carries the capture type. A chain of any length is a
        capture, because a chain of one jump is a capture too. A move the engine built from a
        king's own vectors also carries this type when it walks onto an enemy, which is not
        the same thing at all and is why `landing.py` exists.
    """
    return move is not None and move.move_type == CAPTURE_TYPE


class CaptureRule(Rule):
    """Contribute every capture chain, insist on capturing, and optionally insist on the most."""

    default_name = "Capture"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: Whether a capture is compulsory, whether only the longest chain may
            be played, and the piece kinds a man is crowned as. Only the first is on by
            default, because only the first is English draughts.
        """
        return [
            Field("mandatory", "boolean", "Capture is compulsory", True),
            Field("max_capture", "boolean", "Only the longest capture", False),
            Field("crowning_kinds", "text", "Kinds that are crowned", "man"),
        ]

    def captures_count(self, move: Optional[Move]) -> int:
        """Return how many pieces a move takes.

        Args:
            move: The move being considered, or None.

        Returns:
            int: One for a chain of one jump, and one per jump for a longer chain. A move
            that takes nothing takes nothing, whatever its type.
        """
        return len(getattr(move, "captures", ()) or ())

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer every chain this piece may play, as one move each.

        A chain that finishes on the row where a man is crowned carries the king it becomes,
        so it is offered as a move that both takes and crowns. Offering it uncrowned instead
        would be offering a move the crowning rule refuses, and the chain would be lost.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The chains, longest first, or nothing when this piece cannot take
            anything.
        """
        origin = origin_of(position, piece)
        if origin is None:
            return []

        found: List[Chain] = chains_for(position, piece, self.value.get("crowning_kinds"))
        if not found:
            return []

        longest = max(len(hops) for hops, _ in found)
        if self.value.get("max_capture", False):
            found = [chain for chain in found if len(chain[0]) == longest]
        else:
            found = sorted(found, key=lambda chain: -len(chain[0]))

        offered: List[Move] = []
        for hops, captures in found:
            offered.append(self._as_move(position, piece, origin, hops, captures))
        return offered

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a quiet move while this side has a capture, and — as a variant — a short one.

        The length test is read from `max_capture` rather than assumed, because a rule that
        always applied it would make the switch a decoration: the offered move list would
        grow when it was turned off and the legality test would still refuse everything the
        longer list had left out. Both halves of the test have to be switched together or
        neither.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for a quiet move played while this side can take anything, or — when
            `max_capture` is on — for a chain taking fewer pieces than the best chain
            available. True otherwise.
        """
        if not self.value.get("mandatory", True):
            return True

        colour = self._colour_of(position, move)
        if colour is None:
            return True
        crowning_kinds = self.value.get("crowning_kinds")

        best = side_chains_best(position, colour, crowning_kinds)
        if not is_capture(move):
            return best is None
        if best is None:
            return False
        if not self.value.get("max_capture", False):
            return True
        return self.captures_count(move) >= len(best[0])

    def _as_move(
        self,
        position: Any,
        piece: Any,
        origin: Any,
        hops: Any,
        captures: Any,
    ) -> HopMove:
        """Build the move one found chain is played as.

        Args:
            position: The board the chain was found on.
            piece: The piece making the chain.
            origin: The (row, col) square the chain starts on.
            hops: The landing square of each jump, in order.
            captures: The square each victim stood on, in the same order.

        Returns:
            HopMove: The chain as one move, carrying a king to replace the man with if the
            chain ends on the crowning row.
        """
        crowning = crowning_row(position, piece, self.value.get("crowning_kinds"))
        promotion = crown(piece) if crowning == hops[-1][0] else None
        return HopMove(
            start_pos=origin,
            end_pos=hops[-1],
            hops=hops,
            captures=captures,
            piece=piece,
            move_type=CAPTURE_TYPE,
            promotion_piece=promotion,
        )

    @staticmethod
    def _colour_of(position: Any, move: Move) -> Optional[int]:
        """Return which side is making this move.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            Optional[int]: The mover's colour, or None when the move names no piece and none
            stands on its starting square.
        """
        piece = move.piece or position.get_piece_at(move.start_pos)
        return piece.getColor() if piece is not None else None
