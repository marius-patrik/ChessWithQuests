"""The coordinate record, and the compression the format is required to have.

`PRD.md` FR-49 asks for "compression that is either a standard choice or a configured one,
drawn from the standard library codecs only", and the diagram annotates *Stenographic*
"(Standard or custom compression)". Three sentences, and they are the whole of it. What they
settle is what `games/chess/export/stenographic.py` implements: a standard library codec, not a
scheme written here, and a choice that is a standard one by default and a configured one when
asked. What they leave open — which codec, and how the compressed bytes are written into a
record that has to be a string — is decided there and recorded in the module's docstring.

These tests hold the writer to that: the record names the codec that produced it, every codec
in the roster reads its own record back to the coordinate pairs, a codec outside the roster is
refused by name rather than silently uncompressed, and a long game is genuinely shorter
compressed than not. The last one is the requirement itself — a record that is longer than the
text it stands for has the compression and none of the benefit.

The coordinate pairs are untouched by any of it, and that is asserted too: `e2e4` is still
`e2e4` when the record is read back.
"""

import pytest

from games.chess.export.stenographic import (
    DEFAULT_CODEC,
    STANDARD_CODECS,
    ExportStenographic,
)
from model.game.manager import GameManager
from model.game.move import Move

#: A game long enough for compression to have something to work on. Ninety-odd plies of quiet
#: development, which is what a long game mostly is.
LONG_GAME = [
    Move((1, 4), (3, 4)),
    Move((6, 4), (4, 4)),
    Move((0, 6), (2, 5)),
    Move((7, 5), (5, 4)),
    Move((0, 5), (3, 2)),
    Move((7, 6), (5, 5)),
    Move((1, 3), (3, 3)),
    Move((6, 3), (5, 3)),
    Move((0, 1), (2, 2)),
    Move((7, 1), (5, 2)),
    Move((0, 2), (2, 4)),
    Move((7, 2), (5, 3)),
    Move((0, 3), (3, 3)),
    Move((7, 3), (7, 5)),
    Move((2, 5), (3, 5)),
    Move((5, 4), (4, 4)),
    Move((2, 2), (3, 3)),
    Move((5, 2), (4, 3)),
    Move((1, 1), (2, 2)),
    Move((6, 1), (5, 2)),
    Move((1, 0), (3, 0)),
    Move((6, 0), (5, 0)),
    Move((3, 5), (4, 5)),
    Move((4, 4), (3, 5)),
    Move((2, 4), (3, 5)),
    Move((5, 3), (4, 4)),
    Move((2, 3), (3, 4)),
    Move((5, 5), (4, 5)),
    Move((3, 3), (4, 4)),
    Move((4, 5), (3, 4)),
    Move((3, 4), (4, 3)),
    Move((4, 4), (3, 3)),
]


def _plain(moves):
    """Return the coordinate pairs a record stands for, before any compression.

    Args:
        moves: The moves to write out.

    Returns:
        str: The coordinate pairs, space-delimited.
    """
    from games.chess.export.algebraic import pos_to_algebraic

    return " ".join(
        f"{pos_to_algebraic(move.start_pos)}{pos_to_algebraic(move.end_pos)}" for move in moves
    )


def test_a_record_says_which_codec_wrote_it():
    """The record is read back by whoever holds it, and that reader is not the writer.

    Returns:
        None
    """
    writer = ExportStenographic()

    assert DEFAULT_CODEC == "zlib"
    assert writer.to_stenographic([Move((1, 4), (3, 4))]).startswith(f"{DEFAULT_CODEC}:")


def test_every_standard_library_codec_in_the_roster_reads_its_own_record_back():
    """One test for each, because a codec that compresses and cannot decompress is not a codec.

    Returns:
        None
    """
    moves = LONG_GAME
    plain = _plain(moves)

    for name in STANDARD_CODECS:
        record = ExportStenographic().to_stenographic(moves, codec=name)

        assert record.startswith(f"{name}:")
        assert ExportStenographic().from_stenographic(record) == plain


def test_the_codec_is_the_standard_choice_unless_another_one_is_asked_for():
    """FR-49's two halves: "either a standard choice or a configured one".

    A writer built with another codec uses it, and a call may override the writer, which is
    what makes the choice configuration rather than a constant in the class.

    Returns:
        None
    """
    built = ExportStenographic("bz2")
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]

    assert built.to_stenographic(moves).startswith("bz2:")
    assert built.to_stenographic(moves, codec="gzip").startswith("gzip:")
    assert built.to_stenographic(moves, codec="").startswith("bz2:")


def test_a_codec_that_is_not_one_of_the_standard_library_is_refused_by_name():
    """Not a fallback, and not a silent passthrough: a record this writer cannot name is one it
    cannot read, and saying so beats writing an uncompressed record that looks compressed.

    Returns:
        None
    """
    moves = [Move((1, 4), (3, 4))]

    with pytest.raises(ValueError, match="not a compression codec"):
        ExportStenographic().to_stenographic(moves, codec="rot13")

    with pytest.raises(ValueError, match="not a compression codec"):
        ExportStenographic("rot13")


def test_a_record_that_names_no_codec_is_refused_rather_than_read_as_one():
    """There is nothing to undo, and guessing would be worse than refusing.

    Returns:
        None
    """
    with pytest.raises(ValueError, match="names no compression"):
        ExportStenographic().from_stenographic("e2e4 e7e5")


def test_a_long_game_is_shorter_compressed_than_it_is_written_out():
    """The requirement itself, measured rather than asserted: fewer bytes than the plain record.

    Returned as both counts so that a failure says which way it went wrong, and the plain
    record is measured the way the record is measured — as UTF-8, because a character is not a
    byte and counting them as one is how a "compression" passes while making things longer.

    Returns:
        None
    """
    plain = _plain(LONG_GAME)
    record = ExportStenographic().to_stenographic(LONG_GAME)

    assert len(record) < len(plain)
    assert len(record.encode("utf-8")) < len(plain.encode("utf-8"))


def test_the_coordinate_pairs_are_unchanged_by_the_compression():
    """`e2e4` is still `e2e4` when the record is read back: the squares are the record.

    Returns:
        None
    """
    writer = ExportStenographic()
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4)), Move((1, 6), (3, 6))]

    assert writer.from_stenographic(writer.to_stenographic(moves)) == "e2e4 e7e5 g2g4"


def test_a_game_written_through_the_game_loop_is_compressed_and_reads_back():
    """The same record, reached the way a player reaches it.

    Returns:
        None
    """
    game = GameManager()
    for start, end in [((1, 5), (2, 5)), ((6, 4), (4, 4)), ((1, 6), (3, 6)), ((7, 3), (3, 7))]:
        assert game.make_move(Move(start, end))

    record = game.transcript("Stenographic")

    assert ExportStenographic().from_stenographic(record) == "f2f3 e7e5 g2g4 d8h4"


def test_a_record_of_no_moves_reads_back_as_no_moves():
    """Nothing played is nothing written, which is not the same as refusing the notation.

    Returns:
        None
    """
    writer = ExportStenographic()

    assert writer.from_stenographic(writer.to_stenographic([])) == ""
