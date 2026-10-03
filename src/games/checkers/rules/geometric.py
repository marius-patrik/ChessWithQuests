"""Reading a draughts position.

Nothing here is a rule and nothing here ends a game. These are the questions the checkers
rules ask of a position and of a piece — which row crowns a man, how far one jump of this
piece travels, what would the piece become if it were crowned — and every one of them is
answered from data the piece already declares.

The one thing a rule cannot read off a piece is the direction a piece considers forward,
because a piece declares no facing. It is derived the way the rest of this engine derives a
pawn's starting rank: from the vertical component of a declared diagonal step, which points
at the rows the owner is trying to reach.
"""

from typing import Any, List, Optional, Tuple

from ..pieces.king import King

#: The kind a piece has before it is crowned, and the kind it has afterwards.
MAN_KIND: str = "man"
KING_KIND: str = "king"


def opponent(color: Any) -> int:
    """Return the other side's colour.

    Args:
        color: One side's colour, 1 or -1.

    Returns:
        int: The opposing colour.
    """
    return -1 if color == 1 else 1


def origin_of(position: Any, piece: Any) -> Optional[Tuple[int, int]]:
    """Find where a piece stands.

    A rule is handed a piece and a board and not the square it came from, so the square is
    found by asking the board. A piece that is not on the board has no origin, and None is
    returned rather than a square it was never on.

    Args:
        position: The board to read.
        piece: The piece to find.

    Returns:
        Optional[Tuple[int, int]]: Its square, or None when it is not on the board.
    """
    if piece is None:
        return None
    for row in range(position.rows):
        for col in range(position.cols):
            if position.get_piece_at((row, col)) is piece:
                return (row, col)
    return None


def pieces_of(position: Any, color: int) -> List[Any]:
    """Return every piece belonging to a colour, in board order.

    Args:
        position: The board to read.
        color: Colour to collect, 1 for White and -1 for Black.

    Returns:
        List[Any]: The pieces of that colour.
    """
    return [
        position.get_piece_at((row, col))
        for row in range(position.rows)
        for col in range(position.cols)
        if position.get_piece_at((row, col)) is not None
        and position.get_piece_at((row, col)).getColor() == color
    ]


def kinds_of(position: Any, color: int) -> dict:
    """Count a colour's pieces by kind.

    Args:
        position: The board to read.
        color: Colour to count.

    Returns:
        dict: Kind descriptor to how many of it the colour has.
    """
    counts: dict = {}
    for piece in pieces_of(position, color):
        counts[piece.getType()] = counts.get(piece.getType(), 0) + 1
    return counts


def forward_row(position: Any, piece: Any) -> Optional[int]:
    """Return the row a piece is travelling towards.

    Derived from the piece's own declared diagonal steps: the vertical component of one of
    them points at the rows its owner is trying to reach. A piece that declares no diagonal
    step travels nowhere in particular, and None says so.

    Args:
        position: The board to read, for its dimensions.
        piece: The piece asking.

    Returns:
        Optional[int]: The row the piece moves towards, or None when it declares no
        diagonal step.
    """
    for dr, dc in piece.getDirections() or []:
        if dc == 0 or dr == 0:
            continue
        return 0 if dr < 0 else position.rows - 1
    return None


def crowning_row(position: Any, piece: Any, crowning_kinds: Any) -> Optional[int]:
    """Return the row on which this piece is crowned, if it can be crowned at all.

    The row is derived from the board and the piece's declared forward direction rather than
    from the number eight, so the same question works on a board of any size. The kind is
    checked against the declared crowning kinds first, which is what stops a king being
    "crowned" on the far row: a king already is what a man becomes.

    Args:
        position: The board to read.
        piece: The piece asking.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        Optional[int]: The crowning row, or None when this piece is not crowned.
    """
    if piece is None or piece.getType() not in _kinds(crowning_kinds):
        return None
    return forward_row(position, piece)


def crown(piece: Any) -> Optional[Any]:
    """Return what this piece becomes on reaching the far row.

    The replacement takes the colour of the piece it replaces and nothing else: a draughts
    king is the same piece that has stopped being a man, with no history of its own and no
    right to move recorded anywhere.

    Args:
        piece: The piece being crowned.

    Returns:
        Optional[Any]: A king of the same colour, or None when there is no piece to crown.
    """
    if piece is None:
        return None
    return King(piece.getColor())


def jump_reach(piece: Any) -> Optional[int]:
    """Return how far one jump of this piece may travel.

    This is the piece's own declared step length, read the way the validator reads it: a
    declared maximum step of one means the piece moves one square at a time and jumps
    exactly one square over what it takes, and no declared step at all means it slides as far
    as the board allows — so it may jump as far as the board allows too, over exactly one
    piece.

    Args:
        piece: The piece being measured.

    Returns:
        Optional[int]: 1 for a one-square jump, or None when a jump may travel any distance
        along its diagonal.
    """
    return piece.getMaxSteps()


def diagonals(position: Any) -> List[Tuple[int, int]]:
    """Return every diagonal step a king may take on this board.

    Args:
        position: The board to read.

    Returns:
        List[Tuple[int, int]]: The four diagonal steps.
    """
    return [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _kinds(value: Any) -> List[str]:
    """Read a configured list of piece kinds.

    Args:
        value: The configured value, a comma-separated string or a sequence.

    Returns:
        List[str]: The kinds, empty when nothing is configured.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if value:
        return [str(item) for item in value]
    return []
