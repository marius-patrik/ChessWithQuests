"""Where a castle's two squares are, found on the board rather than calculated.

Both `games/chess/rules/castling.py` and `games/chess/export/fen.py` need the same answer: on a
colour's back rank, which rooks are still on their own squares, and where the royal piece would
land beside each. They used to work it out separately, by arithmetic — the rook's file as the
king's file plus three or minus four — because on an eight-file board the rooks stand three files
from the king and the arithmetic is right.

It is only right there. On a board of ten files the rooks stand five files from the king, the
arithmetic names squares nothing stands on, and both callers agree with each other and are wrong
together: no castle is offered, and no castling right is written.

So the question is asked once, here, and the answer is read from the board. Both callers import it
relatively, which is the same direction `games/chess/export/pgn.py` already imports
`games/chess/export/algebraic.py` from — a file inside the chess configuration answering a chess
question, with the engine never learning the answer.
"""

from typing import Any, List, NamedTuple, Optional


class CastlingSide(NamedTuple):
    """One side's castle: where the rook is and where both pieces would land.

    Attributes:
        letter: The conventional name, `K` for the king's own side and `Q` for the far one.
        rook_file: The file the unmoved rook stands on, found on the board.
        king_dest: The file the royal piece would land on, two files towards the rook.
        rook_dest: The file the rook would land on, the file between it and the king.
    """

    letter: str
    rook_file: int
    king_dest: int
    rook_dest: int


def castling_sides(
    position: Any,
    color: int,
    row: int,
    royal_kind: Optional[str],
    rook_kind: Optional[str],
) -> List[CastlingSide]:
    """Return every castle one colour could still make on this rank.

    A side is offered only when both pieces are where they started: the royal piece unmoved on the
    given rank, and an unmoved rook of the given kind and colour beside it. The squares are then
    read off the relationship between the two pieces, so the answer does not depend on how wide the
    board is.

    Args:
        position: The board to read.
        color: The colour whose castling is being asked about.
        row: The rank that colour's royal piece would castle on.
        royal_kind: The piece kind this configuration treats as royal.
        rook_kind: The piece kind this configuration treats as a rook.

    Returns:
        List[CastlingSide]: One entry per rook that could be used, ordered from the board's first
        file to its last.
    """
    if not royal_kind or not rook_kind:
        return []

    king = None
    for col in range(position.cols):
        piece = position.get_piece_at((row, col))
        if piece is not None and piece.getType() == royal_kind and piece.getColor() == color:
            if piece.hasMoved() or king is not None:
                # A royal piece that has moved has no castle, and two of them is a position this
                # rule does not know how to read. Either way, offer nothing rather than guess.
                return []
            king = piece
    if king is None:
        return []

    king_file = next(
        col for col in range(position.cols) if position.get_piece_at((row, col)) is king
    )

    found: dict = {}
    for col in range(position.cols):
        rook = position.get_piece_at((row, col))
        if rook is None or rook is king:
            continue
        if rook.getType() != rook_kind or rook.getColor() != color or rook.hasMoved():
            continue
        if col > king_file:
            found["K"] = CastlingSide("K", col, king_file + 2, king_file + 1)
        else:
            found["Q"] = CastlingSide("Q", col, king_file - 2, king_file - 1)

    # The king's own side first, then the far one. The position record writes its rights in that
    # order — `KQkq` — so an order chosen by board position would write the field the wrong way
    # round. Declaring it here means both callers inherit one order instead of each having an own.
    return [found[letter] for letter in ("K", "Q") if letter in found]
