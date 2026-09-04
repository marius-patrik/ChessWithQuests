from typing import List, Optional, Any

try:
    from model.misc.notation import pos_to_algebraic
    from model.misc.metadata import MetadataWriter
except ImportError:
    from .notation import pos_to_algebraic
    from .metadata import MetadataWriter


class ExportWriter:
    def __init__(self):
        self.field: str = ""

    def export(self, *args, **kwargs) -> str:
        raise NotImplementedError


class ChessNotationWriter(ExportWriter):
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
        super().__init__()

    def to_stenographic(self, moves: List[Any]) -> str:
        tokens = []
        for m in moves:
            start = pos_to_algebraic(m.start_pos)
            end = pos_to_algebraic(m.end_pos)
            tokens.append(f"{start}{end}")
        return " ".join(tokens)

    def to_fen(self, board: Any, active_color: int = 1) -> str:
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

    def export(self, format_type: str = "PGN", **kwargs) -> str:
        fmt = format_type.upper()
        if fmt == "PGN":
            return self.to_pgn(kwargs.get("moves", []), kwargs.get("metadata"))
        elif fmt == "FEN":
            return self.to_fen(kwargs["board"], kwargs.get("active_color", 1))
        elif fmt == "STENOGRAPHIC":
            return self.to_stenographic(kwargs.get("moves", []))
        return ""
