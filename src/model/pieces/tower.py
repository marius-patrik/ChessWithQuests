"""Tower chess piece module (alias for Rook in Czech chess terminology)."""

try:
    from .rook import Rook
except ImportError:
    try:
        from model.pieces.rook import Rook
    except ImportError:
        from rook import Rook

Tower = Rook
