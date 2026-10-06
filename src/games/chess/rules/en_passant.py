"""The one-off long advance, and the capture in passing it allows.

A long first advance is the one move a piece may make only from the row it starts on, which
the piece itself does not record: all it declares is an offset it may use once. Nothing here
knows what a pawn is. The rule recognises a one-off long advance from the piece's declared
`initial_vectors`, insists it is made from the row it belongs on, and offers the capture in
passing to whatever piece takes the right way.

The rule answers `target_square` as well, which is what makes the offer part of a position's
identity rather than only part of a position's moves: the same placement with the offer
standing and the offer gone is one position to a board and two positions to a game.
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
        self.state.setdefault("target", None)

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

    def target_square(self) -> Optional[Tuple[int, int]]:
        """Return the square a capture in passing would land on, for one ply after an advance.

        The offer is recorded after every declared first advance, whether or not a capture is
        available to anybody — the same convention the position record writes, and for the same
        reason: a record of the offer must not depend on which pieces happen to be standing
        where, and the answer therefore does not change with the rules in force.

        This is the square *behind* the advanced piece and not the square it stands on, because
        the first is where a capturing piece lands and the second is where the advanced piece
        is lifted from — and `victim_square` already answers for the second. The row it comes
        to is one row back along the direction the advanced piece travelled, which is read off
        the move rather than off the piece's colour, so it is right for either colour and for a
        board of any size. A long advance that would put that square off the board offers
        nothing, because there is no square to land on.

        Returns:
            Optional[Tuple[int, int]]: The square a capture in passing would land on, or None
            when no such offer stands.
        """
        return self.state.get("target")

    def on_move_made(self, position: Any, move: Move) -> None:
        """Offer a capture for exactly one ply after a two-square advance.

        The offer lives on the square the advanced piece *stands on*, because that is the
        square it must be lifted from. Any other move ends the offer, including the capture
        in passing itself.

        The square a capturing piece would land on is recorded beside it, and is cleared in the
        same breath, so the two never disagree about whether an offer stands — and `target_square`
        is answerable for any ply in which this rule was told what happened, which is what lets
        a rule counting positions ask its set what the position was offering.

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
            self.state["target"] = self._landing_square(position, move)
        else:
            self.state["victim"] = None
            self.state["victim_color"] = None
            self.state["target"] = None

    @staticmethod
    def _landing_square(position: Any, move: Move) -> Optional[Tuple[int, int]]:
        """Return the square behind the piece that just advanced.

        Behind is the opposite of the way the piece travelled, and the direction it travelled
        is read off the move's own row delta rather than off the piece's colour — which is what
        makes this right for either colour, for a board of any size, and for a configuration
        whose two sides do not start on the rows this one starts them on.

        Args:
            position: The board after the move, used only to ask whether the square is on it.
            move: The advance that was played.

        Returns:
            Optional[Tuple[int, int]]: One row back along the direction of travel, on the file
            the piece advanced, or None when that square is not on the board — which a declared
            advance long enough to run off the edge can produce, and in which case there is no
            square for a capture to land on.
        """
        behind = 1 if move.end_pos[0] < move.start_pos[0] else -1
        square = (move.end_pos[0] + behind, move.end_pos[1])
        return square if position.is_within_bounds(*square) else None

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
