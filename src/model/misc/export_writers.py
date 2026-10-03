"""Export writers converting games to PGN, FEN, and stenographic notation.

The writer holds no piece knowledge at all. A piece declares the character it is written as,
and a configuration that has not declared one is a configuration with no position record —
which is said out loud rather than guessed at.

This module should not be here at all: PGN, FEN and algebraic coordinates are chess formats,
and `notes/object_model.md` registers them as belonging to `games/chess/export/`. What blocks
that move is `model/game/manager.py`, which imports `ChessNotationWriter` by name. Until that
caller is updated, the chess naming of squares is reached through `_to_algebraic()` below,
which imports the chess configuration on demand rather than at module level — a module-level
import would make `games/chess/__init__.py` and this module import each other, and loading any
variant configuration would then fail on a circular import.
"""

from typing import List, Optional, Any, Tuple

from model.misc.metadata import MetadataWriter


def _to_algebraic(position: Tuple[int, int]) -> str:
    """Name a square the way chess names it.

    Args:
        position: Tuple of (row, col) 0-indexed coordinates.

    Returns:
        str: The square's chess algebraic notation (e.g. 'e4').

    Raises:
        ImportError: If the chess configuration is not importable. That configuration is
            where the chess naming lives, so a writer used without it has no naming to use.
    """
    from games.chess.export.algebraic import pos_to_algebraic

    return pos_to_algebraic(position)


class ExportWriter:
    """Abstract base class for game export serialization writers."""

    def __init__(self):
        """Initialize an ExportWriter instance."""
        self.field: str = ""

    def export(self, *args: Any, **kwargs: Any) -> str:
        """Export game data into the target serialization format.

        Args:
            *args: Variable positional arguments.
            **kwargs: Any: Variable keyword arguments.

        Returns:
            str: The serialized game in the format this writer produces.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class ChessNotationWriter(ExportWriter):
    """Serializes chess moves and board states into standard chess formats (PGN, FEN, stenographic)."""

    def __init__(self):
        """Initialize a ChessNotationWriter instance."""
        super().__init__()

    @staticmethod
    def _fen_letter(piece: Any) -> str:
        """Return the character a piece declares for a position record.

        Args:
            piece: The piece being written.

        Returns:
            str: The piece's declared letter, in lower case.

        Raises:
            ValueError: If the piece declares no character. A piece with nothing to say about
                a position record has no position record, and writing it as something else
                would be a lie about the position.
        """
        get_fen = getattr(piece, "getFen", None)
        letter = get_fen() if callable(get_fen) else None
        if not letter:
            get_type = getattr(piece, "getType", None)
            name = get_type() if callable(get_type) else None
            raise ValueError(
                f"a piece of type {name!r} declares no character for a position record, "
                "so this position cannot be written"
            )
        return str(letter).lower()

    def to_stenographic(self, moves: List[Any]) -> str:
        """Convert a list of moves to stenographic coordinate format (e.g. 'e2e4 e7e5').

        Args:
            moves: List of Move instances with start_pos and end_pos.

        Returns:
            Space-delimited string of concatenated coordinate pairs.
        """
        tokens = []
        for m in moves:
            start = _to_algebraic(m.start_pos)
            end = _to_algebraic(m.end_pos)
            tokens.append(f"{start}{end}")
        return " ".join(tokens)

    def to_fen(self, board: Any, active_color: int = 1) -> str:
        """Convert board state to Forsyth-Edwards Notation (FEN) string.

        Args:
            board: Board instance. Its rows and cols decide how many ranks and files the
                record carries, so a board of any size serialises.
            active_color: Active side color (1 for White, -1 for Black).

        Returns:
            FEN record string.

        Raises:
            ValueError: If a piece on the board declares no character for a position record.
                Nothing is guessed: an undeclared piece has no place in a position record,
                and a record that quietly called it a pawn would be wrong in a way no reader
                could see.
        """
        ranks = []
        for r in range(board.rows - 1, -1, -1):
            empty = 0
            rank_str = ""
            for c in range(board.cols):
                piece = board.get_piece_at((r, c))
                if piece is None:
                    empty += 1
                else:
                    if empty > 0:
                        rank_str += str(empty)
                        empty = 0
                    char = self._fen_letter(piece)
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
            w_end = getattr(moves[i], "end_pos", None)
            w_move = _to_algebraic(w_end) if w_end is not None else str(moves[i])
            if i + 1 < len(moves):
                b_end = getattr(moves[i + 1], "end_pos", None)
                b_move = _to_algebraic(b_end) if b_end is not None else str(moves[i + 1])
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
            **kwargs: Any: Format-specific parameters ('moves', 'board', 'metadata', 'active_color').

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
