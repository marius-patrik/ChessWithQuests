"""Castling.

A move that carries a rook with its king, and the most conditional rule in the game: five
things must hold before it may be offered at all. Every rank and file it needs is derived
from the board rather than assumed, so the rule works at any board size.
"""

from typing import Any, List, Optional, Tuple

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule
from games.chess.rules.attacks import is_attacked, opponent

#: Precedence is unused here; castling never ends a game.
CASTLE_KING_SIDE = "O-O"
CASTLE_QUEEN_SIDE = "O-O-O"


class CastlingRule(Rule):
    """Offer a castle when nothing forbids it, and forbid it otherwise."""

    default_name = "Castling"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: The royal piece kind and the rook piece kind.
        """
        return [
            Field("royal_kind", "text", "Royal piece kind", "king"),
            Field("rook_kind", "text", "Rook piece kind", "rook"),
        ]

    def attach(self) -> None:
        """Remember which colours have already castled.

        Returns:
            None
        """
        self.state.setdefault("castled", set())

    def home_row(self, position: Any, color: int) -> int:
        """Return the row a colour's back rank sits on.

        Args:
            position: The board to read.
            color: Colour whose back rank is wanted.

        Returns:
            int: Row zero for the first colour, and the far row for the other.
        """
        return 0 if color == 1 else position.rows - 1

    def start_file(self, position: Any) -> int:
        """Return the file a colour's royal piece castles from.

        Castling is not a move to a chosen square: it is a move to one of two squares, and
        only from the one it started on. Offering it from anywhere else is how a royal piece
        that has wandered to g1 was offered a castle to c1, dragging a rook across the board
        to do it. The file is therefore derived from the board rather than assumed, as the
        middle file of the back rank, which is where a chess king starts.

        Args:
            position: The board to read.

        Returns:
            int: The file a castle begins on.
        """
        return position.cols // 2

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer the castles this piece could make right now.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The castles that are currently legal.
        """
        kind = self.value.get("royal_kind")
        if not kind or piece.getType() != kind or piece.hasMoved():
            return []

        color = piece.getColor()
        row = self.home_row(position, color)
        origin = piece_position(position, piece)
        if origin is None or origin[0] != row or origin[1] != self.start_file(position):
            return []
        castled = self.state.setdefault("castled", set())
        if color in castled:
            return []

        # Everything else follows from where the royal piece stands. It crosses two files
        # towards one rook or the other, and that rook ends up on the file next to where the
        # royal piece lands.
        start = origin[1]
        offered: List[Move] = []
        for king_dest, rook_file, rook_dest in (
            (start + 2, start + 3, start + 1),
            (start - 2, start - 4, start - 1),
        ):
            if not (0 <= rook_file < position.cols and 0 <= king_dest < position.cols):
                continue
            move = self._castle(position, piece, color, row, rook_file, rook_dest, king_dest)
            if move is not None:
                offered.append(move)
        return offered

    def _castle(
        self,
        position: Any,
        piece: Any,
        color: int,
        row: int,
        rook_file: int,
        rook_dest: int,
        king_dest: int,
    ) -> Optional[Move]:
        """Build one castle if it is legal, and return None if it is not.

        Args:
            position: The board to read.
            piece: The royal piece asking to castle.
            color: Its colour.
            row: Its back rank.
            rook_file: The file the rook stands on.
            rook_dest: The file the rook lands on.
            king_dest: The file the royal piece lands on.

        Returns:
            Optional[Move]: The castle, or None when any condition fails.
        """
        rook_kind = self.value.get("rook_kind")
        origin = piece_position(position, piece)
        if origin is None:
            return None

        rook_square = (row, rook_file)
        rook = position.get_piece_at(rook_square)
        if (
            rook is None
            or rook.getType() != rook_kind
            or rook.getColor() != color
            or rook.hasMoved()
        ):
            return None

        # Every square either piece crosses must be empty. The royal piece crosses two files
        # and the rook crosses three, so testing only the royal piece's span left the file
        # the rook has to travel down untested — which is why a pawn on b1 did not stop a
        # castle to c1.
        span = range(min(origin[1], king_dest), max(origin[1], king_dest) + 1)
        span = set(span) | set(range(min(rook_file, rook_dest), max(rook_file, rook_dest) + 1))
        for file in span:
            occupant = position.get_piece_at((row, file))
            if occupant is not None and occupant is not piece and occupant is not rook:
                return None

        # The royal piece may not start in check, nor cross a square that is attacked, nor
        # land on one. The rook's own squares are not judged: the rook is being carried by a
        # king that may not be harmed, and chess does not ask whether a rook would be safe.
        for file in range(min(origin[1], king_dest), max(origin[1], king_dest) + 1):
            if is_attacked(position, (row, file), opponent(color)):
                return None

        return Move(
            start_pos=origin,
            end_pos=(row, king_dest),
            piece=piece,
            move_type="castling",
            companion_start=rook_square,
            companion_end=(row, rook_dest),
        )

    def permits_move(self, position: Any, move: Any) -> bool:
        """Refuse a king move that is a castle the rules have not offered.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False when the move claims to be a castle it is not entitled to.
        """
        if move.move_type != "castling":
            return True
        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None or piece.getType() != self.value.get("royal_kind"):
            return False
        return any(
            offered.start_pos == move.start_pos for offered in self.available_moves(position, piece)
        )

    def on_move_made(self, position: Any, move: Any) -> None:
        """Record that a colour has castled, and forget it if its royal piece moves.

        Args:
            position: The board after the move.
            move: The move that was played.

        Returns:
            None
        """
        castled = self.state.setdefault("castled", set())
        piece = position.get_piece_at(move.end_pos)
        if move.move_type == "castling" and piece is not None:
            castled.add(piece.getColor())
            return
        # A royal piece that moves by any other route gives the right up again. The castling
        # branch returns first: it used to fall through to this test, whose `piece` is the king
        # that had just castled, so the right was granted and revoked on the same move.
        if piece is not None and piece.getType() == self.value.get("royal_kind"):
            castled.discard(piece.getColor())


def piece_position(position: Any, piece: Any) -> Optional[Tuple[int, int]]:
    """Find where a piece stands.

    Args:
        position: The board to read.
        piece: The piece to find.

    Returns:
        Optional[Tuple[int, int]]: Its square, or None when it is not on the board.
    """
    for r in range(position.rows):
        for c in range(position.cols):
            if position.get_piece_at((r, c)) is piece:
                return (r, c)
    return None
