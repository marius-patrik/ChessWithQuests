"""The one-off long advance, and the capture in passing it allows.

A long first advance is the one move a piece may make only from the row it starts on, which
the piece itself does not record: all it declares is an offset it may use once. Nothing here
knows what a pawn is. The rule recognises a one-off long advance from the piece's declared
`initial_vectors`, insists it is made from the row it belongs on, and offers the capture in
passing to whatever piece takes the right way.
"""

from typing import Any, List, Optional, Tuple

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

    def start_row(self, position: Any, piece: Any) -> Optional[int]:
        """Return the row this piece's one-off advance is offered from.

        A piece that has declared a long advance declares an offset, not a square, and the
        piece itself keeps no record of where it began. The row is therefore derived from the
        board the same way the far end of a piece's travel is derived elsewhere: one row in
        from the edge the advance starts against, which for a pawn is its own starting rank.
        Without it a pawn that had already reached the middle of the board was offered a
        fresh two-square advance from wherever it stood.

        Args:
            position: The board to read.
            piece: The piece asking.

        Returns:
            Optional[int]: The row, or None when this piece declares no long advance.
        """
        if piece is None:
            return None
        for dr, dc in piece.getInitialVectors() or []:
            if dc != 0 or dr == 0:
                continue
            return position.rows - 2 if dr < 0 else 1
        return None

    def is_first_advance(
        self, position: Any, piece: Any, start: Tuple[int, int], end: Tuple[int, int]
    ) -> bool:
        """Report whether these two squares are this piece's one-off long advance.

        The row is what makes it the *first* advance rather than any move of that shape, so
        this asks nothing about whether the piece has already moved: it is also asked about a
        move that has already been played, and by then the piece has.

        Args:
            position: The board to read.
            piece: The piece that moves.
            start: The (row, col) square it leaves.
            end: The (row, col) square it lands on.

        Returns:
            bool: True when the offset is one the piece declared for its first move only
            and the piece is standing on the row that advance belongs on.
        """
        if piece is None:
            return False
        offset = (end[0] - start[0], end[1] - start[1])
        if offset not in (piece.getInitialVectors() or []):
            return False
        return start[0] == self.start_row(position, piece)

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
        piece = piece_at(position, move.end_pos)
        if self.is_first_advance(position, piece, move.start_pos, move.end_pos):
            self.state["victim"] = tuple(move.end_pos)
            self.state["victim_color"] = piece.getColor() if piece is not None else None
        else:
            self.state["victim"] = None
            self.state["victim_color"] = None

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a long first advance made from anywhere but the row it belongs on.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for a declared first-move advance that begins off its own row, True
            otherwise.
        """
        piece = move.piece or piece_at(position, move.start_pos)
        if piece is None:
            return True
        start_row = self.start_row(position, piece)
        if start_row is None or move.start_pos[0] == start_row:
            return True
        offset = (move.end_pos[0] - move.start_pos[0], move.end_pos[1] - move.start_pos[1])
        return offset not in (piece.getInitialVectors() or [])

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


def piece_at(position: Any, square: Tuple[int, int]) -> Optional[Any]:
    """Return whatever stands on a square.

    Args:
        position: The board to read.
        square: The (row, col) square to look at.

    Returns:
        Optional[Any]: The piece standing there, or None.
    """
    return position.get_piece_at(square)


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
