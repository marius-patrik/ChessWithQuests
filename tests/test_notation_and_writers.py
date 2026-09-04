import pytest
from model.misc.notation import pos_to_algebraic, algebraic_to_pos
from model.misc.export_writers import ChessNotationWriter, ExportWriter
from model.misc.metadata import MetadataWriter
from model.game.board import Board
from model.game.move import Move


def test_algebraic_conversions():
    assert pos_to_algebraic((0, 0)) == "a1"
    assert pos_to_algebraic((0, 4)) == "e1"
    assert pos_to_algebraic((7, 7)) == "h8"

    assert algebraic_to_pos("a1") == (0, 0)
    assert algebraic_to_pos("e4") == (3, 4)
    assert algebraic_to_pos("h8") == (7, 7)


def test_chess_notation_writer_fen():
    board = Board()
    writer = ChessNotationWriter()
    fen = writer.to_fen(board, active_color=1)
    assert "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1" == fen


def test_chess_notation_writer_stenographic():
    writer = ChessNotationWriter()
    moves = [
        Move((1, 4), (3, 4)),  # e2 -> e4
        Move((6, 4), (4, 4)),  # e7 -> e5
    ]
    steno = writer.to_stenographic(moves)
    assert steno == "e2e4 e7e5"


def test_chess_notation_writer_pgn():
    writer = ChessNotationWriter()
    metadata = MetadataWriter({"Event": "Friendly Match", "Result": "1-0"})
    moves = [
        Move((1, 4), (3, 4)),
        Move((6, 4), (4, 4)),
    ]
    pgn = writer.to_pgn(moves, metadata)
    assert '[Event "Friendly Match"]' in pgn
    assert "1. e4 e5 1-0" in pgn
