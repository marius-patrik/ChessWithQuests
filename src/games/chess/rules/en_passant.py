"""En passant.

A capture whose target is not where the capturing piece lands, so it needs the square the
captured pawn actually stands on. Nothing here knows what a pawn is: the rule recognises a
one-off long advance from the piece's declared `initial_vectors`, and offers the capture to
whatever piece takes the right way.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule


class EnPassantRule(Rule):
    """Offer the capture in passing for exactly one ply after a two-square advance."""

    default_name = "En passant"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: None. The rule needs no configuration; it reads the board.
        """
        return []

    def attach(self) -> None:
        """Forget any capture in passing from a previous game.

        Returns:
            None
        """
        self.state.setdefault("victim", None)
        self.state.setdefault("victim_color", None)

    def victim_square(self) -> Optional[tuple]:
        """Return the square the pawn that may be taken in passing stands on.

        Returns:
            Optional[tuple]: The square, or None when no capture is available.
        """
        return self.state.get("victim")

    def on_move_made(self, position: Any, move: Move) -> None:
        """Offer a capture for exactly one ply after a two-square advance.

        The offer lives on the square the advanced piece *stands on*, because that is the
        square it must be lifted from. Any other move ends the offer, including the capture
        in passing itself.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        if self._is_double_step(position, move):
            self.state["victim"] = tuple(move.end_pos)
            self.state["victim_color"] = piece_color(position, move)
        else:
            self.state["victim"] = None
            self.state["victim_color"] = None

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer the capture in passing when one is available to this piece.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The capture, or nothing.
        """
        victim = self.state.get("victim")
        victim_color = self.state.get("victim_color")
        if victim is None or victim_color is None:
            return []
        target = position.get_piece_at(victim)
        if target is None or target.getColor() != victim_color:
            return []

        offered: List[Move] = []
        origin = piece_origin(position, piece)
        if origin is None:
            return []
        for destination in self._capture_destinations(position, piece):
            # The advanced piece stands beside the capturer, on the capturer's own rank. The
            # capture is on when that square is the one just offered, and the piece is
            # lifted from it rather than from the square the capturer lands on.
            beside = (origin[0], destination[1])
            if beside == origin or beside != victim:
                continue
            offered.append(
                Move(
                    start_pos=origin,
                    end_pos=destination,
                    piece=piece,
                    move_type="en_passant",
                    capture_from=victim,
                )
            )
        return offered

    def _capture_destinations(self, position: Any, piece: Any) -> List[tuple]:
        """Return the squares this piece may take on.

        Args:
            position: The board to read.
            piece: The piece asking.

        Returns:
            List[tuple]: The one-step take destinations, taken from the piece's declared
            attack vectors.
        """
        origin = piece_origin(position, piece)
        if origin is None:
            return []
        take_only = [
            vector
            for vector in (piece.getAttackDirections() or [])
            if vector not in (piece.getDirections() or [])
        ]
        destinations = []
        for dr, dc in take_only:
            nr, nc = origin[0] + dr, origin[1] + dc
            if position.is_within_bounds(nr, nc):
                destinations.append((nr, nc))
        return destinations

    @staticmethod
    def _is_double_step(position: Any, move: Move) -> bool:
        """Report whether a move was a piece's declared one-off long advance.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            bool: True when the move's offset is one the piece only had before its first
            move.
        """
        piece = position.get_piece_at(move.end_pos)
        if piece is None:
            return False
        offset = (move.end_pos[0] - move.start_pos[0], move.end_pos[1] - move.start_pos[1])
        return offset in piece.getInitialVectors()


def piece_origin(position: Any, piece: Any) -> Optional[tuple]:
    """Find where a piece stands.

    Args:
        position: The board to read.
        piece: The piece to find.

    Returns:
        Optional[tuple]: Its square, or None when it is not on the board.
    """
    for r in range(position.rows):
        for c in range(position.cols):
            if position.get_piece_at((r, c)) is piece:
                return (r, c)
    return None


def piece_color(position: Any, move: Move) -> Optional[int]:
    """Return the colour of the piece that just moved.

    Args:
        position: The board after the move.
        move: The move that was played.

    Returns:
        Optional[int]: The colour, or None when the square is empty.
    """
    piece = position.get_piece_at(move.end_pos)
    return None if piece is None else piece.getColor()
