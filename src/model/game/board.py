"""Chessboard representation managing piece layout, bounds, and piece movements."""

from typing import Iterable, Optional, List, Tuple

from model.pieces.pawn import Pawn
from model.pieces.rook import Rook
from model.pieces.horse import Horse
from model.pieces.bishop import Bishop
from model.pieces.queen import Queen
from model.pieces.king import King
from model.pieces.piece import Piece


class Board:
    """A rectangular playing surface that tracks piece positions and captures.

    The board is any number of rows by any number of columns. `DEFAULT_DIMENSIONS` is the
    size the shipped starting placement describes; it is a default, not a constraint, and
    nothing outside this class may rely on it.
    """

    #: The board size the shipped starting placement describes.
    DEFAULT_DIMENSIONS: Tuple[int, int] = (8, 8)

    def __init__(
        self,
        dimensions: Tuple[int, int] = DEFAULT_DIMENSIONS,
        setup_pieces: bool = True,
        placement: Optional[Iterable[Tuple[Tuple[int, int], Piece]]] = None,
    ):
        """Initialize a board.

        Args:
            dimensions: Board dimensions as a (rows, cols) tuple.
            setup_pieces: Whether to apply the shipped starting placement. Ignored when
                `placement` is given.
            placement: Explicit starting placement as (position, piece) pairs. Use this to
                populate a board the shipped placement does not describe.

        Raises:
            ValueError: If `setup_pieces` is requested for a board the shipped placement
                does not describe and no `placement` was supplied.
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
            self.setup_default_board()

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
        if hasattr(piece, "setMoved"):
            piece.setMoved(True)
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

    def default_placement(self) -> List[Tuple[Tuple[int, int], Piece]]:
        """Return the shipped starting placement for this board.

        Returns:
            List[Tuple[Tuple[int, int], Piece]]: (position, piece) pairs, White first.

        Raises:
            ValueError: If this board is not the size the shipped placement describes. A
                board of any other size is legal and playable; it simply has no shipped
                starting position, and saying so beats handing back an empty board that
                looks like a starting position.
        """
        if self.dimensions != self.DEFAULT_DIMENSIONS:
            raise ValueError(
                f"the shipped starting placement describes a "
                f"{self.DEFAULT_DIMENSIONS[0]}x{self.DEFAULT_DIMENSIONS[1]} board, not a "
                f"{self.rows}x{self.cols} one; pass placement=..., or setup_pieces=False"
            )

        back_rank = [Rook, Horse, Bishop, Queen, King, Bishop, Horse, Rook]
        placement: List[Tuple[Tuple[int, int], Piece]] = [
            ((0, file), piece(1)) for file, piece in enumerate(back_rank)
        ]
        placement += [((1, file), Pawn(1)) for file in range(self.cols)]

        last_row = self.rows - 1
        last_pawn_row = self.rows - 2
        placement += [((last_row, file), piece(-1)) for file, piece in enumerate(back_rank)]
        placement += [((last_pawn_row, file), Pawn(-1)) for file in range(self.cols)]
        return placement

    def setup_default_board(self) -> None:
        """Initialize the board with the shipped starting placement.

        Returns:
            None

        Raises:
            ValueError: If this board is not the size the shipped placement describes.
        """
        self.apply_placement(self.default_placement())
