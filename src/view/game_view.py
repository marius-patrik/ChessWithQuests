"""The board, drawn.

`BoardView` is the only part of the program that knows what a square looks like. It draws the
squares, the coordinates, the pieces, and the two things a player cannot work out from the
position alone: which piece is selected, and where it may go. It reads the board and the
configuration's declared glyphs, and it emits a square; it never decides what a move means.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from model.game.board import Board
from model.pieces.piece import Piece

Square = Tuple[int, int]

#: How a square is coloured, by whether it is one of the two shades.
LIGHT = "#f0d9b5"
DARK = "#b58863"
#: The ring drawn on the selected piece's square.
SELECTED = "#ffd700"
#: The dot drawn on a square the selected piece may move to.
TARGET = "#2f6b1f"
#: The colour of a square the active player's royal piece is standing on while in check.
IN_CHECK = "#d9534f"

#: The glyph drawn on an empty square.
EMPTY = "·"


class BoardView(ttk.Frame):
    """The playing surface: squares, coordinates and pieces, with selection and targets."""

    def __init__(
        self,
        master: tk.Misc,
        board: Board,
        on_square_clicked: Optional[Callable[[Square], None]] = None,
        square_size: int = 56,
        show_coordinates: bool = True,
    ):
        """Draw a board.

        Args:
            master: The widget to draw into.
            board: The `Board` to draw, from the configuration the game is playing.
            on_square_clicked: Called with the (row, col) of a square the player clicked.
            square_size: The width and height of one square, in pixels.
            show_coordinates: Whether to label the files and ranks.
        """
        super().__init__(master)
        self.board = board
        self.on_square_clicked = on_square_clicked
        self.square_size = square_size
        self.show_coordinates = show_coordinates

        self.selected: Optional[Square] = None
        self.targets: List[Square] = []
        self.in_check: Optional[Square] = None

        self.canvas = tk.Canvas(
            self,
            width=board.cols * square_size,
            height=board.rows * square_size,
            highlightthickness=0,
            background=LIGHT,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._clicked)
        self.redraw()

    def refresh(self, board: Optional[Board] = None) -> None:
        """Redraw from a board that may have changed since the last draw.

        Args:
            board: The new board, or None to redraw the one already held.

        Returns:
            None
        """
        if board is not None:
            self.board = board
        self.redraw()

    def set_selection(self, selected: Optional[Square], targets: List[Square]) -> None:
        """Show which piece is selected and where it may go.

        Args:
            selected: The selected piece's square, or None when nothing is selected.
            targets: The squares that piece may move to.

        Returns:
            None
        """
        self.selected = selected
        self.targets = list(targets)
        self.redraw()

    def set_in_check(self, square: Optional[Square]) -> None:
        """Mark the square whose occupant is in check.

        Args:
            square: The square to mark, or None when nobody is in check.

        Returns:
            None
        """
        self.in_check = square
        self.redraw()

    def redraw(self) -> None:
        """Draw the whole board from scratch.

        Returns:
            None
        """
        self.canvas.delete("all")
        board = self.board

        for row in range(board.rows):
            for col in range(board.cols):
                # Drawn from White's side: rank 1 at the bottom, the a-file on the left, which
                # is how a player expects to read a board. Row 0 holds White's back rank, and
                # `pos_to_algebraic` calls row 0 rank 1, so the view must agree with it.
                board_row = board.rows - 1 - row
                left, top = self._origin(col, row)
                right = left + self.square_size
                bottom = top + self.square_size
                square = (board_row, col)

                fill = LIGHT if (board_row + col) % 2 == 0 else DARK
                if square == self.in_check:
                    fill = IN_CHECK
                self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#8b6b4a")

                piece = board.get_piece_at(square)
                if piece is not None:
                    self._draw_piece(piece, left, top, right, bottom)
                elif square in self.targets:
                    self._draw_target(left, top, right, bottom)

                if square == self.selected:
                    self.canvas.create_rectangle(
                        left + 2,
                        top + 2,
                        right - 2,
                        bottom - 2,
                        outline=SELECTED,
                        width=4,
                    )

        if self.show_coordinates:
            self._draw_coordinates()

    def _origin(self, col: int, row: int) -> Tuple[int, int]:
        """Return the pixel position of a square's top-left corner.

        Args:
            col: The square's file.
            row: The square's rank.

        Returns:
            Tuple[int, int]: The (x, y) pixel position.
        """
        return col * self.square_size, row * self.square_size

    def _draw_piece(self, piece: Piece, left: int, top: int, right: int, bottom: int) -> None:
        """Draw one piece using the glyph its configuration declared.

        Args:
            piece: The piece standing on the square.
            left: The square's left edge in pixels.
            top: The square's top edge in pixels.
            right: The square's right edge in pixels.
            bottom: The square's bottom edge in pixels.

        Returns:
            None
        """
        glyph = piece.getSymbol() or piece.getName()
        self.canvas.create_text(
            (left + right) / 2,
            (top + bottom) / 2,
            text=glyph,
            font=("TkDefaultFont", max(12, int(self.square_size * 0.6))),
        )

    def _draw_target(self, left: int, top: int, right: int, bottom: int) -> None:
        """Draw the marker on a square a selected piece may move to.

        Args:
            left: The square's left edge in pixels.
            top: The square's top edge in pixels.
            right: The square's right edge in pixels.
            bottom: The square's bottom edge in pixels.

        Returns:
            None
        """
        radius = self.square_size * 0.2
        centre_x = (left + right) / 2
        centre_y = (top + bottom) / 2
        self.canvas.create_oval(
            centre_x - radius,
            centre_y - radius,
            centre_x + radius,
            centre_y + radius,
            fill=TARGET,
            outline="",
        )

    def _draw_coordinates(self) -> None:
        """Label the files along the bottom and the ranks down the left.

        Returns:
            None
        """
        rows = self.board.rows
        for col in range(self.board.cols):
            centre_x = (col + 0.5) * self.square_size
            self.canvas.create_text(
                centre_x,
                rows * self.square_size - 10,
                text=self._file_label(col),
                fill="#3b2a1a",
                font=("TkDefaultFont", 9),
            )
        for row in range(rows):
            centre_y = (row + 0.5) * self.square_size
            self.canvas.create_text(
                10,
                centre_y,
                text=str(rows - row),
                fill="#3b2a1a",
                font=("TkDefaultFont", 9),
            )

    @staticmethod
    def _file_label(col: int) -> str:
        """Return the letter naming a file.

        Args:
            col: The file's index.

        Returns:
            str: The file's letter, so a column is `a` onwards.
        """
        return chr(ord("a") + col)

    def _clicked(self, event: tk.Event) -> None:
        """Report the square the player clicked.

        Args:
            event: The click event, whose x and y are in canvas pixels.

        Returns:
            None
        """
        if self.on_square_clicked is None:
            return
        col = int(event.x // self.square_size)
        row = int(event.y // self.square_size)
        # The same inversion the draw applies: the top of the window is rank 8.
        board_row = self.board.rows - 1 - row
        if self.board.is_within_bounds(board_row, col):
            self.on_square_clicked((board_row, col))
