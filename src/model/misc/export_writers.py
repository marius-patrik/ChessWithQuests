"""Chess export writers converting games to PGN, FEN, and stenographic notation."""

from typing import List, Optional, Any

try:
    from model.misc.notation import pos_to_algebraic
    from model.misc.metadata import MetadataWriter
except ImportError:
    from .notation import pos_to_algebraic
    from .metadata import MetadataWriter


class ExportWriter:
    """Abstract base class for game export serialization writers."""

    def __init__(self):
        """Initialize an ExportWriter instance."""
        self.field: str = ""

    def export(self, *args: Any, **kwargs: Any) -> str:
        """Export game data into the target serialization format.

        Args:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class ChessNotationWriter(ExportWriter):
    """Serializes chess moves and board states into standard chess formats (PGN, FEN, stenographic)."""

    PIECE_CHARS = {
        "king": "k",
        "queen": "q",
        "rook": "r",
        "bishop": "b",
        "horse": "n",
        "knight": "n",
        "pawn": "p",
    }

    def __init__(self):
        """Initialize a ChessNotationWriter instance."""
        super().__init__()

    def to_stenographic(self, moves: List[Any]) -> str:
        """Convert a list of moves to stenographic coordinate format (e.g. 'e2e4 e7e5').

        Args:
            moves: List of Move instances with start_pos and end_pos.

        Returns:
            Space-delimited string of concatenated coordinate pairs.
        """
        tokens = []
        for m in moves:
            start = pos_to_algebraic(m.start_pos)
            end = pos_to_algebraic(m.end_pos)
            tokens.append(f"{start}{end}")
        return " ".join(tokens)

    def to_fen(self, board: Any, active_color: int = 1) -> str:
        """Convert board state to Forsyth-Edwards Notation (FEN) string.

        Args:
            board: Board instance with rows, cols, and get_piece_at.
            active_color: Active side color (1 for White, -1 for Black).

        Returns:
            FEN record string.
        """
        ranks = []
        for r in range(7, -1, -1):
            empty = 0
            rank_str = ""
            for c in range(8):
                piece = board.get_piece_at((r, c))
                if piece is None:
                    empty += 1
                else:
                    if empty > 0:
                        rank_str += str(empty)
                        empty = 0
                    ptype = piece.getType().lower() if hasattr(piece, "getType") else "p"
                    char = self.PIECE_CHARS.get(ptype, "p")
                    rank_str += (
                        char.upper()
                        if (piece.getColor() == 1 or piece.getColor() == "white")
                        else char.lower()
                    )
            if empty > 0:
                rank_str += str(empty)
            ranks.append(rank_str)

        board_fen = "/".join(ranks)
        turn = "w" if active_color == 1 else "b"
        return f"{board_fen} {turn} - - 0 1"

    def to_pgn(self, moves: List[Any], metadata: Optional[MetadataWriter] = None) -> str:
        """Export game moves and metadata to Portable Game Notation (PGN) text.

        Args:
            moves: List of played Move instances.
            metadata: Optional MetadataWriter instance providing PGN header tags.

        Returns:
            Complete PGN format string.
        """
        headers = (
            metadata.format_pgn_headers() if metadata else '[Event "Casual Game"]\n[Result "*"]'
        )
        move_pairs = []
        for i in range(0, len(moves), 2):
            move_num = (i // 2) + 1
            w_move = (
                pos_to_algebraic(moves[i].end_pos)
                if hasattr(moves[i], "end_pos")
                else str(moves[i])
            )
            if i + 1 < len(moves):
                b_move = (
                    pos_to_algebraic(moves[i + 1].end_pos)
                    if hasattr(moves[i + 1], "end_pos")
                    else str(moves[i + 1])
                )
                move_pairs.append(f"{move_num}. {w_move} {b_move}")
            else:
                move_pairs.append(f"{move_num}. {w_move}")

        moves_text = " ".join(move_pairs)
        result = metadata.get_header("Result", "*") if metadata else "*"
        return f"{headers}\n\n{moves_text} {result}".strip()

    def export(self, format_type: str = "PGN", **kwargs: Any) -> str:
        """Export game information in the requested format ('PGN', 'FEN', or 'STENOGRAPHIC').

        Args:
            format_type: Format name case-insensitively ('PGN', 'FEN', 'STENOGRAPHIC').
            **kwargs: Format-specific parameters ('moves', 'board', 'metadata', 'active_color').

        Returns:
            Serialized string representation.
        """
        fmt = format_type.upper()
        if fmt == "PGN":
            return self.to_pgn(kwargs.get("moves", []), kwargs.get("metadata"))
        elif fmt == "FEN":
            return self.to_fen(kwargs["board"], kwargs.get("active_color", 1))
        elif fmt == "STENOGRAPHIC":
            return self.to_stenographic(kwargs.get("moves", []))
        return ""
