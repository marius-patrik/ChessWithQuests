from typing import Optional, List, Tuple

try:
    from model.pieces.pawn import Pawn
    from model.pieces.rook import Rook
    from model.pieces.horse import Horse
    from model.pieces.bishop import Bishop
    from model.pieces.queen import Queen
    from model.pieces.king import King
    from model.pieces.piece import Piece
except ImportError:
    from ..pieces.pawn import Pawn
    from ..pieces.rook import Rook
    from ..pieces.horse import Horse
    from ..pieces.bishop import Bishop
    from ..pieces.queen import Queen
    from ..pieces.king import King
    from ..pieces.piece import Piece


class Board:
    def __init__(self, dimensions: Tuple[int, int] = (8, 8), setup_pieces: bool = True):
        self.dimensions = dimensions
        self.rows, self.cols = dimensions
        self.board: List[List[Optional[Piece]]] = [
            [None for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self.captured_white: List[Piece] = []
        self.captured_black: List[Piece] = []

        if setup_pieces and dimensions == (8, 8):
            self.setup_default_board()

    def is_within_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_piece_at(self, position: Tuple[int, int]) -> Optional[Piece]:
        row, col = position
        if not self.is_within_bounds(row, col):
            return None
        return self.board[row][col]

    def set_piece_at(self, position: Tuple[int, int], piece: Optional[Piece]) -> None:
        row, col = position
        if self.is_within_bounds(row, col):
            self.board[row][col] = piece

    def move_piece(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> bool:
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
        self.set_piece_at(position, new_piece)

    def setup_default_board(self) -> None:
        self.board = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.captured_white.clear()
        self.captured_black.clear()

        # White pieces (row 0 and 1, color = 1)
        self.board[0][0] = Rook(1)
        self.board[0][1] = Horse(1)
        self.board[0][2] = Bishop(1)
        self.board[0][3] = Queen(1)
        self.board[0][4] = King(1)
        self.board[0][5] = Bishop(1)
        self.board[0][6] = Horse(1)
        self.board[0][7] = Rook(1)
        for c in range(8):
            self.board[1][c] = Pawn(1)

        # Black pieces (row 7 and 6, color = -1)
        self.board[7][0] = Rook(-1)
        self.board[7][1] = Horse(-1)
        self.board[7][2] = Bishop(-1)
        self.board[7][3] = Queen(-1)
        self.board[7][4] = King(-1)
        self.board[7][5] = Bishop(-1)
        self.board[7][6] = Horse(-1)
        self.board[7][7] = Rook(-1)
        for c in range(8):
            self.board[6][c] = Pawn(-1)
