"""The chess naming, and one writer per chess notation.

Which notations a game can write is the configuration's answer, so each writer lives in
`games/chess/export/` beside the naming it needs and the engine keeps only the protocol.
These tests hold each writer to the record it wrote before the split, byte for byte, and to
the rule that a writer answers the notations it declares and refuses the rest.

Two notations arrived after the split and are here with the others: the algebraic record the
diagram calls *letter*, and the header record the diagram calls *Field - Field - Extra*.
`tests/test_metadata.py` holds the header's derivation in detail; what is claimed here is
that it is one writer among five, that it declares exactly one notation, and that a game's
own transcript and a game's own header are the same roster written twice.
"""

from games.chess.board import build_board
from games.chess.export.algebraic import (
    AlgebraicNotation,
    ExportAlgebraic,
    algebraic_to_pos,
    pos_to_algebraic,
)
from games.chess.export.fen import ExportFEN
from games.chess.export.metadata import ExportMetadata
from games.chess.export.pgn import ExportPGN
from games.chess.export.stenographic import ExportStenographic
import pytest
from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter
from model.game.board import Board
from model.game.move import Move


def test_algebraic_conversions():
    assert pos_to_algebraic((0, 0)) == "a1"
    assert pos_to_algebraic((0, 4)) == "e1"
    assert pos_to_algebraic((7, 7)) == "h8"

    assert algebraic_to_pos("a1") == (0, 0)
    assert algebraic_to_pos("e4") == (3, 4)
    assert algebraic_to_pos("h8") == (7, 7)


def test_the_chess_naming_of_a_move_is_the_algebraic_naming_of_both_its_squares():
    """The move history and the transcript are one conversion, not two that agree today.

    Returns:
        None
    """
    notation = AlgebraicNotation()
    move = Move((1, 4), (3, 4))

    assert notation.move_label(1, move) == "1. e2 – e4"
    assert notation.square_label(move.start_pos) == pos_to_algebraic(move.start_pos)
    assert notation.square_label(move.end_pos) == pos_to_algebraic(move.end_pos)


def test_the_chess_configuration_declares_its_naming():
    """A configuration declares how it names a move, and chess declares the algebraic one.

    Returns:
        None
    """
    from games.chess import build_configuration

    assert isinstance(build_configuration().notation, AlgebraicNotation)


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
    metadata = ExportMetadata({"Event": "Friendly Match", "Result": "1-0"})

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


# --- the algebraic record, which the diagram calls *letter*


def test_the_algebraic_writer_declares_one_notation_and_writes_it():
    """The naming the window draws moves in is also a record a game can be written into.

    `AlgebraicNotation` was the naming with no writer behind it, so a chess game had an
    algebraic move history and no way to write the game algebraically at all.

    Returns:
        None
    """
    writer = ExportAlgebraic()
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]

    assert writer.formats() == ("Algebraic",)
    assert writer.export("Algebraic", moves=moves) == "1. e4 e5"
    assert writer.export("algebraic", moves=moves) == "1. e4 e5"
    assert writer.export(" Algebraic ", moves=moves) == "1. e4 e5"

    with pytest.raises(UnsupportedExportFormat, match="Algebraic"):
        writer.export("PGN", moves=moves)


def test_the_algebraic_record_is_not_the_coordinate_record_and_not_the_transcript():
    """Three notations of the same four moves, and three different texts.

    Written side by side so that "it writes algebraic notation" cannot be satisfied by a
    writer that writes the coordinate pair with the letters run together.

    Returns:
        None
    """
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4)), Move((1, 6), (3, 6))]

    assert ExportStenographic().to_stenographic(moves) == "e2e4 e7e5 g2g4"
    assert ExportAlgebraic().to_algebraic(moves) == "1. e4 e5 2. g4"


def test_an_algebraic_record_names_a_piece_that_moved_and_a_pawn_that_did_not():
    """A pawn is the one piece the notation names by its destination alone.

    The letters come from the pieces themselves rather than from a table here, which is what
    a piece that declares its own character for a position record makes possible.

    Returns:
        None
    """
    from games.chess.pieces.knight import Knight
    from games.chess.pieces.pawn import Pawn

    board = build_board()
    pawn = Pawn(1)
    knight = Knight(1)
    board.set_piece_at((1, 4), pawn)
    board.set_piece_at((0, 1), knight)
    moves = [
        Move((1, 4), (3, 4), piece=pawn),
        Move((0, 1), (2, 2), piece=knight),
    ]

    assert ExportAlgebraic().to_algebraic(moves) == "1. e4 Nc3"


def test_an_algebraic_record_marks_a_capture_a_promotion_and_a_castle():
    """The three markers that are not a square, asserted separately so none is assumed.

    Returns:
        None
    """
    from games.chess.pieces.pawn import Pawn
    from games.chess.pieces.queen import Queen

    queen = Queen(1)
    taken = Queen(-1)
    pawn = Pawn(-1)
    crowned = Queen(-1)
    moves = [
        Move((3, 3), (4, 4), piece=queen, captured_piece=taken),
        Move((6, 4), (4, 4), move_type="castling_kingside"),
        Move((7, 6), (7, 7), piece=pawn, promotion_piece=crowned),
    ]

    assert ExportAlgebraic().to_algebraic(moves) == "1. Qxe5 O-O 2. h8=Q"


def test_a_queenside_castle_is_named_as_one_rather_than_as_a_king_move():
    """Two castlings and one spelling of each, or the record cannot be read back.

    Returns:
        None
    """
    moves = [
        Move((7, 4), (7, 6), move_type="castling_queenside"),
        Move((0, 4), (0, 6), move_type="castling_kingside"),
    ]

    assert ExportAlgebraic().to_algebraic(moves) == "1. O-O-O O-O"


# --- the header record, which the diagram calls *Field - Field - Extra*


def test_the_chess_configuration_offers_five_notations_and_leads_with_the_transcript():
    """The diagram enumerates five, one writer each, and the transcript leads.

    The order matters twice over: `default_format` takes the first, and `save_log` names its
    file from it, so a chess game written without being asked for a notation is a `.pgn`.

    Returns:
        None
    """
    from games.chess import build_configuration

    configuration = build_configuration()
    offered = [name for writer in configuration.exporters for name in writer.formats()]

    assert offered == ["PGN", "Algebraic", "Field-Field-Extra", "FEN", "Stenographic"]
    assert configuration.metadata is not None


def test_a_game_written_without_being_asked_for_a_notation_is_still_a_transcript():
    """The order the writers are declared in is the order `default_format` and `save_log` read.

    Returns:
        None
    """
    from games.chess import build_configuration
    from model.game.manager import GameManager

    game = GameManager(configuration=build_configuration())

    assert game.default_format() == "PGN"
    assert game.notation.formats() == ("PGN",)


def test_the_configuration_hands_the_manager_the_same_header_it_offers_as_a_format():
    """Otherwise a game would be written with a header the configuration does not export.

    Returns:
        None
    """
    from games.chess import build_configuration

    configuration = build_configuration()

    assert configuration.metadata in configuration.exporters


def test_a_header_written_on_its_own_is_the_header_the_transcript_carries():
    """One roster written twice is two that drift apart, so the PGN composes this writer.

    Returns:
        None
    """
    header = ExportMetadata({"Event": "Club Championship"})
    moves = [Move((1, 4), (3, 4))]

    on_its_own = header.export("Field-Field-Extra")
    inside_a_transcript = ExportPGN().export("PGN", moves=moves, metadata=header)

    assert inside_a_transcript.startswith(on_its_own + "\n\n")
