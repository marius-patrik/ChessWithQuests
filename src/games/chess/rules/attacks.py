"""Reading a chess position.

Nothing here is a rule and nothing here ends a game. These are the questions the rules ask
of a position — is this square attacked, does this colour have a piece of that kind, does it
have any legal move — and every one of them is answered from declared piece data.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

Position = Any


def is_attacked(position: Position, square: Tuple[int, int], by_color: int) -> bool:
    """Report whether a square is attacked by any piece of a colour.

    Args:
        position: The board to read.
        square: The (row, col) square being attacked.
        by_color: Colour of the attacking side.

    Returns:
        bool: True when a piece of that colour reaches the square.
    """
    tr, tc = square
    for r in range(position.rows):
        for c in range(position.cols):
            piece = position.get_piece_at((r, c))
            if piece is None or piece.getColor() != by_color:
                continue
            can_jump = piece.canJump()
            limit = (
                1
                if (can_jump or piece.getMaxSteps() is not None)
                else max(position.rows, position.cols)
            )
            for dr, dc in piece.getAttackDirections() or []:
                for step in range(1, limit + 1):
                    nr, nc = r + dr * step, c + dc * step
                    if not position.is_within_bounds(nr, nc):
                        break
                    if (nr, nc) == (tr, tc):
                        return True
                    if not can_jump and position.get_piece_at((nr, nc)) is not None:
                        break
    return False


def find_piece(position: Position, kind: str, color: int) -> Optional[Tuple[int, int]]:
    """Find a colour's piece of one kind.

    Args:
        position: The board to read.
        kind: The piece type descriptor to look for.
        color: Colour of the piece.

    Returns:
        Optional[Tuple[int, int]]: The square, or None when there is no such piece.
    """
    for r in range(position.rows):
        for c in range(position.cols):
            piece = position.get_piece_at((r, c))
            if piece is not None and piece.getColor() == color and piece.getType() == kind:
                return (r, c)
    return None


def pieces_of(position: Position, color: int) -> List[Any]:
    """Return every piece belonging to a colour.

    Args:
        position: The board to read.
        color: Colour to collect.

    Returns:
        List[Any]: The pieces, in board order.
    """
    found = []
    for r in range(position.rows):
        for c in range(position.cols):
            piece = position.get_piece_at((r, c))
            if piece is not None and piece.getColor() == color:
                found.append(piece)
    return found


def kinds_of(position: Position, color: int) -> Dict[str, int]:
    """Count a colour's pieces by kind.

    Args:
        position: The board to read.
        color: Colour to count.

    Returns:
        Dict[str, int]: Kind descriptor to how many of it the colour has.
    """
    counts: Dict[str, int] = {}
    for piece in pieces_of(position, color):
        counts[piece.getType()] = counts.get(piece.getType(), 0) + 1
    return counts


def square_color(position: Position, square: Tuple[int, int]) -> int:
    """Return which shade of square a coordinate falls on.

    Args:
        position: The board to read.
        square: The (row, col) coordinate.

    Returns:
        int: 0 or 1, the parity of the row plus column.
    """
    return (square[0] + square[1]) % 2


def opponent(color: int) -> int:
    """Return the other side's colour.

    Args:
        color: One side's colour.

    Returns:
        int: The opposing colour.
    """
    return -color


def has_legal_move(position: Position, color: int, rules: Iterable[Any]) -> bool:
    """Report whether a colour has any legal move at all.

    Args:
        position: The board to read.
        color: Colour whose turn it is.
        rules: The rules in force.

    Returns:
        bool: True when at least one legal move exists. This is what separates checkmate
        from stalemate, and it is the question neither of them can answer alone.
    """
    from model.game.validator import MoveValidator

    validator = MoveValidator(position, rules=rules)
    return bool(validator.get_all_valid_moves(color, position))
