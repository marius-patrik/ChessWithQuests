from games.chess.board import build_board
from games.chess.export.fen import ExportFEN
from games.chess.export.pgn import ExportPGN
from games.chess.export.stenographic import ExportStenographic
import pytest
from model.game.manager import UnsupportedExportFormat
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


def test_the_position_record_writer_declares_one_notation_and_writes_it():
    """A writer writes the notations it declares, and reaches them however they are spelled.

    `GameManager.writer_for` matches a notation without regard to case and hands `export` the
    caller's own spelling, so a writer that compared one exact string would refuse a notation
    the manager had just agreed to write.

    Returns:
        None
    """
    writer = ExportFEN()

    assert writer.formats() == ("FEN",)
    assert writer.export("FEN", board=build_board(), active_color=1) == (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"
    )
    assert writer.export("fen", board=build_board(), active_color=1).startswith("rnbqkbnr/")
    assert writer.export(" Fen ", board=build_board(), active_color=1).startswith("rnbqkbnr/")


def test_a_notation_the_writer_does_not_write_is_refused_rather_than_answered_emptyly():
    """An unknown notation is a question this writer cannot answer, and says so.

    The empty string the format switch fell through to was indistinguishable from a board with
    nothing on it, which is the ambiguity `formats()` was introduced to remove.

    Returns:
        None
    """
    writer = ExportFEN()

    assert writer._writes("FEN") is True
    assert writer._writes("Roll") is False

    with pytest.raises(UnsupportedExportFormat, match="FEN"):
        writer.export("Roll", board=build_board())


def test_the_base_writer_declares_no_notation_and_refuses_to_write():
    """The engine holds the protocol and nothing else, so the base answers nothing.

    Returns:
        None
    """
    writer = ExportWriter()

    assert writer.formats() == ()
    assert writer._writes("FEN") is False

    with pytest.raises(NotImplementedError):
        writer.export("FEN")


def test_the_transcript_writer_declares_one_notation_and_writes_it():
    """The game reaches PGN through the notation the writer declares, in any spelling.

    Returns:
        None
    """
    writer = ExportPGN()
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]
    metadata = MetadataWriter({"Event": "Friendly Match", "Result": "1-0"})

    assert writer.formats() == ("PGN",)
    assert "1. e4 e5 1-0" in writer.export("PGN", moves=moves, metadata=metadata)
    assert "1. e4 e5 1-0" in writer.export("pgn", moves=moves, metadata=metadata)

    with pytest.raises(UnsupportedExportFormat, match="PGN"):
        writer.export("FEN", moves=moves)


def test_the_coordinate_record_writer_declares_one_spelling_and_answers_any():
    """The public name is `Stenographic`, and every spelling of it reaches the same writer.

    The format used to be declared `"Stenographic"` and dispatched as `"STENOGRAPHIC"`, so the
    engine held a second, private spelling of a name callers could already see.

    Returns:
        None
    """
    writer = ExportStenographic()
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]

    assert writer.formats() == ("Stenographic",)
    assert writer.export("Stenographic", moves=moves) == "e2e4 e7e5"
    assert writer.export("stenographic", moves=moves) == "e2e4 e7e5"
    assert writer.export("STENOGRAPHIC", moves=moves) == "e2e4 e7e5"

    with pytest.raises(UnsupportedExportFormat, match="Stenographic"):
        writer.export("PGN", moves=moves)


def test_a_game_with_no_moves_still_writes_an_empty_coordinate_record():
    """A record of no moves is genuinely empty, which is not the same as refusing.

    Returns:
        None
    """
    assert ExportStenographic().export("Stenographic", moves=[]) == ""


def test_chess_notation_writer_fen():
    board = build_board()
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
