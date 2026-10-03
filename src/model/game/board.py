"""A playing surface: piece layout, bounds, and captures.

The board knows how to hold a rectangle of pieces. It does not know what a piece is, who
starts where, or how big the game is — a configuration supplies all three, which is why
nothing here imports a piece subclass.
"""

from typing import Iterable, List, Optional, Tuple

from model.game.field import Field
from model.pieces.piece import Piece

#: The largest side a board may have. A board is any number of rows by any number of columns,
#: and this is a bound the *form* applies so a player cannot type a board nobody meant, not a
#: limit the engine enforces on a board it is handed.
MAX_SIDE = 64


class Board:
    """A rectangular playing surface that tracks piece positions and captures.

    The board is any number of rows by any number of columns. It starts empty: a starting
    position is a fact about a game, so the configuration hands one over as `placement`.

    `DEFAULT_DIMENSIONS` is the size used when a caller does not care. It is a convenience
    and nothing more — no piece, rule or game may treat it as the size of a board.
    """

    #: The size used when a caller states no size of its own.
    DEFAULT_DIMENSIONS: Tuple[int, int] = (8, 8)

    def __init__(
        self,
        dimensions: Tuple[int, int] = DEFAULT_DIMENSIONS,
        setup_pieces: bool = False,
        placement: Optional[Iterable[Tuple[Tuple[int, int], Piece]]] = None,
    ):
        """Initialize a board.

        Args:
            dimensions: Board dimensions as a (rows, cols) tuple.
            setup_pieces: Deprecated. A board has no starting position of its own, so this
                now only raises: pass `placement` instead. It is kept so a caller that
                relied on the old default is told why rather than silently handed an empty
                board.
            placement: The starting placement as (position, piece) pairs, supplied by the
                configuration.

        Raises:
            ValueError: If `setup_pieces` is requested without a `placement`.
        """
        self.dimensions = dimensions
        self.rows, self.cols = dimensions
        self.board: List[List[Optional[Piece]]] = [
            [None for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self.captured_white: List[Piece] = []
        self.captured_black: List[Piece] = []

        if placement is not None:
            self.apply_placement(placement)
        elif setup_pieces:
            raise ValueError(
                "a board carries no starting position of its own; the configuration "
                "supplies one as placement=[((row, col), piece), ...]"
            )

    def value_fields(self) -> List[Field]:
        """Declare the values a board is configured with.

        FR-1 makes the dimensions configurable, and FR-32 makes every configurable thing a
        form assembled from a declaration rather than a hand-built form. The board is the
        first thing a player changes in a variant, so it declares like everything else.

        Returns:
            List[Field]: The rows and the columns, each an integer from 1 to 64. A board
            larger than that is playable but is a configuration nobody means, and the bound
            is here so the form can say so rather than the engine refusing a board later.
        """
        return [
            Field("rows", "integer", "Rows", self.rows, minimum=1, maximum=MAX_SIDE),
            Field("cols", "integer", "Columns", self.cols, minimum=1, maximum=MAX_SIDE),
        ]

    def set_dimensions(self, rows: int, cols: int) -> None:
        """Resize the board, keeping every piece that still fits.

        A game in progress must not lose pieces to a settings change, so a piece on a square
        that survives the resize stays where it is and one that does not is left on the board
        object rather than silently removed: the grid is rebuilt and the pieces are re-placed
        only where they fit.

        Args:
            rows: The new number of rows.
            cols: The new number of columns.

        Raises:
            ValueError: If either dimension is below 1 or above `MAX_SIDE`.
        """
        for value, name in ((rows, "rows"), (cols, "columns")):
            if value < 1 or value > MAX_SIDE:
                raise ValueError(f"a board may have 1 to {MAX_SIDE} {name}, not {value}")
        if (rows, cols) == self.dimensions:
            return
        surviving = [
            ((row, col), self.board[row][col])
            for row in range(self.rows)
            for col in range(self.cols)
            if self.board[row][col] is not None
        ]
        self.dimensions = (rows, cols)
        self.rows, self.cols = rows, cols
        self.board = [[None for _ in range(cols)] for _ in range(rows)]
        for position, piece in surviving:
            self.set_piece_at(position, piece)
        self._stranded = [
            piece for position, piece in surviving if not self.is_within_bounds(*position)
        ]

    def is_within_bounds(self, row: int, col: int) -> bool:
        """Check if coordinates lie within the board boundaries.

        Args:
            row: 0-indexed board row.
            col: 0-indexed board column.

        Returns:
            True if (row, col) is within bounds, False otherwise.
        """
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_piece_at(self, position: Tuple[int, int]) -> Optional[Piece]:
        """Retrieve the piece located at the specified board position.

        Args:
            position: Tuple of (row, col) coordinates.

        Returns:
            Piece instance at the position, or None if empty or out of bounds.
        """
        row, col = position
        if not self.is_within_bounds(row, col):
            return None
        return self.board[row][col]

    def set_piece_at(self, position: Tuple[int, int], piece: Optional[Piece]) -> None:
        """Place or remove a piece at a specified position.

        Args:
            position: Tuple of (row, col) coordinates.
            piece: Piece instance to place, or None to clear square.
        """
        row, col = position
        if self.is_within_bounds(row, col):
            self.board[row][col] = piece

    def move_piece(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> bool:
        """Move a piece from start_pos to end_pos, tracking captured pieces.

        Args:
            start_pos: Source (row, col) coordinates.
            end_pos: Target (row, col) coordinates.

        Returns:
            True if the piece was successfully moved, False if invalid or empty start.
        """
        piece = self.get_piece_at(start_pos)
        if piece is None:
            return False
        if not self.is_within_bounds(end_pos[0], end_pos[1]):
            return False

        target = self.get_piece_at(end_pos)
        if target is not None:
            if target.getColor() == 1 or target.getColor() == "white":
                self.captured_white.append(target)
            else:
                self.captured_black.append(target)

        self.set_piece_at(end_pos, piece)
        self.set_piece_at(start_pos, None)
        piece.has_moved = True
        return True

    def replace_piece(self, position: Tuple[int, int], new_piece: Piece) -> None:
        """Replace a piece at the given position (e.g. during pawn promotion).

        Args:
            position: Target (row, col) coordinate.
            new_piece: Replacement Piece instance.
        """
        self.set_piece_at(position, new_piece)

    def apply_placement(self, placement: Iterable[Tuple[Tuple[int, int], Piece]]) -> None:
        """Clear the board and place every piece in a placement.

        Args:
            placement: (position, piece) pairs. Positions outside the board are ignored.

        Returns:
            None
        """
        self.board = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.captured_white.clear()
        self.captured_black.clear()
        for position, piece in placement:
            self.set_piece_at(position, piece)


#: Czech alias for `Board`, as `PRD.md` section 5 and `HerníPlocha` in the diagram require.
HerniPlocha = Board
