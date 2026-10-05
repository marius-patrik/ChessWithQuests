"""Standard Algebraic Notation, checked against a PGN nobody here wrote.

`ExportPGN` writes its movetext by replaying the game, because every part of Standard
Algebraic Notation that a `Move` does not carry is a question about a position: which knight
moved when two can, and whether the move gave check or mate. The risk in that is a notation
checked only against itself — a writer that agreed with its own output would pass every test
here while being wrong.

So the first test below replays **the Opera Game** — Paul Morphy against the Duke of Brunswick
and Count Isouard, Paris 1858 — and asserts the movetext against the game as it is published,
transcribed as a literal into `OPERA_GAME`. That transcription is from the English Wikipedia
article "Opera Game", read on 2026-10-05, whose move list runs
`1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3 c6
9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+
Nxd7 16. Qb8+ Nxb8 17. Rd8#`. The squares this repository's board uses are spelled out beside
the line, because a move list of square names is the only part of the test that is this
repository's own.

The game is chosen because it exercises four of the vocabulary at once: a queen capture, a
knight capture, a *file* disambiguation (`Nbd7`, two knights that can both reach d7), three
check suffixes, a long castle and a mate. Each remaining case — the rank disambiguation, the
both-file-and-rank disambiguation, a pawn capture, a promotion with and without a capture, and
a piece that cannot legally reach the square — is a separate test below, because the risk
`SCRATCHPAD.md` §9 names is exactly `Nbd7` versus `N1d7` versus `Nd7` and each of those is a
different answer.
"""

import pytest

from games.chess.board import build_board
from games.chess.export.algebraic import algebraic_to_pos
from games.chess.export.pgn import ExportPGN
from games.chess.pieces.king import King
from games.chess.pieces.knight import Knight
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen
from games.chess.pieces.rook import Rook
from model.game.board import Board
from model.game.manager import GameManager
from model.game.move import Move
from model.pieces.piece import Piece

#: The Opera Game's movetext, as published. Not this repository's output.
OPERA_GAME = (
    "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 "
    "8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 "
    "14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0"
)

#: The same game as the squares this repository's board uses. `e2e4` is e2 to e4, and a castle
#: is the king's own two squares — the rule's whole move, rook and all, is found through the
#: validator rather than rebuilt, or the rook would never travel.
OPERA_SQUARES = [
    "e2e4",
    "e7e5",
    "g1f3",
    "d7d6",
    "d2d4",
    "c8g4",
    "d4e5",
    "g4f3",
    "d1f3",
    "d6e5",
    "f1c4",
    "g8f6",
    "f3b3",
    "d8e7",
    "b1c3",
    "c7c6",
    "c1g5",
    "b7b5",
    "c3b5",
    "c6b5",
    "c4b5",
    "b8d7",
    "e1c1",
    "a8d8",
    "d1d7",
    "d8d7",
    "h1d1",
    "e7e6",
    "b5d7",
    "f6d7",
    "b3b8",
    "d7b8",
    "d1d8",
]

#: A line that reaches the corner where two rooks stand on one file, which is what makes the
#: notation name a rank rather than a file.
ROOKS_ON_A_FILE = [
    "e2e4",
    "e7e5",
    "d2d4",
    "d7d6",
    "g1f3",
    "g8f6",
    "b1c3",
    "b8c6",
    "c1g5",
    "c8e6",
    "f1e2",
    "f8e7",
    "d1d2",
    "d6d5",
    "a2a4",
    "a7a5",
    "e1g1",
    "e8g8",
    "a1a3",
    "h7h6",
    "f1a1",
    "b7b6",
]

#: The same position with the other rook making the move, which is the other half of the pair.
ROOKS_ON_A_FILE_FROM_A1 = ROOKS_ON_A_FILE + ["a1a2"]
#: And with the rook from a3 making it, which shares the file and so must be named by rank.
ROOKS_ON_A_FILE_FROM_A3 = ROOKS_ON_A_FILE + ["a3a2"]

#: A line that leaves two knights on b1 and f3, both of which can reach d2.
TWO_KNIGHTS_TO_D2 = ["e2e4", "d7d5", "d2d3", "g8f6", "g1f3", "a7a6"]
#: The b1 knight arriving, and the f3 knight arriving. One is `Nbd2`, the other `Nfd2`.
KNIGHT_FROM_B1 = TWO_KNIGHTS_TO_D2 + ["b1d2"]
KNIGHT_FROM_F3 = TWO_KNIGHTS_TO_D2 + ["f3d2"]

#: A line that leaves two knights on b3 and f3 with a black pawn on d4 that either may take.
TWO_KNIGHTS_TO_D4 = ["e2e4", "d7d5", "d2d3", "d5d4", "b1d2", "g8f6", "d2b3", "a7a6", "g1f3", "c7c6"]
KNIGHT_TAKES_FROM_B3 = TWO_KNIGHTS_TO_D4 + ["b3d4"]
KNIGHT_TAKES_FROM_F3 = TWO_KNIGHTS_TO_D4 + ["f3d4"]

#: A line that leaves both rooks on the first rank able to reach e1.
BOTH_ROWKS_REACH_E1 = [
    "e2e4",
    "d7d5",
    "d2d4",
    "e7e6",
    "g1f3",
    "g8f6",
    "b1c3",
    "b8c6",
    "f1c4",
    "f8c5",
    "c1g5",
    "e8g8",
    "d1d2",
    "h7h6",
    "e1g1",
    "b7b6",
]
ROOK_FROM_F1 = BOTH_ROWKS_REACH_E1 + ["f1e1"]
ROOK_FROM_A1 = BOTH_ROWKS_REACH_E1 + ["a1e1"]

#: A line with two white pawns on c4 and e4 and a black pawn on d5 that either may take. A
#: pawn is named by the file it came from and needs no letter and no hint.
TWO_PAWNS_TO_D5 = ["e2e4", "d7d5", "c2c4", "g8f6"]
PAWN_FROM_E4 = TWO_PAWNS_TO_D5 + ["e4d5"]
PAWN_FROM_C4 = TWO_PAWNS_TO_D5 + ["c4d5"]


def _play(squares):
    """Play a game from a list of square names, one pair of squares per move.

    The move a rule offered is looked up rather than rebuilt from the two squares, because a
    castle is a king's move *and* a rook's and rebuilding it drops the rook. Nothing here is
    under test; this is the driver that puts a real game in front of the writer.

    Args:
        squares: A flat list of square names, two per move, as chess names them.

    Returns:
        GameManager: The game, with every move played.
    """
    game = GameManager()
    for token in squares:
        start, end = algebraic_to_pos(token[:2]), algebraic_to_pos(token[2:])
        move = game.move_validator.find_move(start, end, game.board) or Move(start, end)
        assert game.make_move(move), f"{token} was refused"
    return game


def _movetext(squares):
    """Return the movetext of a game played from a list of square names.

    Args:
        squares: A flat list of square names, two per move.

    Returns:
        str: The movetext and the result, which is everything after the header's blank line.
    """
    game = _play(squares)
    game.finish_game()
    return game.transcript("PGN").split("\n\n")[1]


def _position(pairs):
    """Deal a position from a list of square-name and piece pairs.

    The replay plays on the board it is handed and leaves it as the replay ended, so a test
    that wants the same position twice deals it twice.

    Args:
        pairs: (square name, piece) pairs.

    Returns:
        Board: The position dealt.
    """
    board = Board((8, 8), setup_pieces=False)
    board.apply_placement([(algebraic_to_pos(name), piece) for name, piece in pairs])
    return board


def _written(position, moves):
    """Write moves played from a position that was not a standard opening.

    Args:
        position: The position the moves are played from.
        moves: The moves to write.

    Returns:
        str: The movetext.
    """
    return ExportPGN().to_pgn(moves, position=position).split("\n\n")[1]


def test_a_published_game_is_written_in_the_notation_that_game_is_published_in():
    """The whole movetext, against a game recorded before this repository existed.

    The Opera Game carries a queen capture, a knight capture, three checks, a long castle, a
    mate, and `Nbd7` — a knight capture's cousin, two knights that can both reach d7 and so
    must say which one did. Written by hand into `OPERA_GAME` from the published game.

    Returns:
        None
    """
    assert _movetext(OPERA_SQUARES) == OPERA_GAME


def test_two_knights_that_can_both_reach_a_square_are_told_apart_by_their_file():
    """`Nbd2` against `Nfd2`: the same destination, and the notation has to say which knight.

    Returns:
        None
    """
    assert _movetext(KNIGHT_FROM_B1).endswith("Nbd2 *")
    assert _movetext(KNIGHT_FROM_F3).endswith("Nfd2 *")


def test_a_knight_that_takes_something_is_named_by_its_file_before_the_capture_mark():
    """`Nbxd4` against `Nfxd4` — the hint goes between the letter and the `x`, not after it.

    Returns:
        None
    """
    assert _movetext(KNIGHT_TAKES_FROM_B3).endswith("Nbxd4 *")
    assert _movetext(KNIGHT_TAKES_FROM_F3).endswith("Nfxd4 *")


def test_two_rooks_on_one_rank_are_told_apart_by_their_file():
    """`Rfe1` against `Rae1`, the pair the disambiguation exists for after a short castle.

    Returns:
        None
    """
    assert _movetext(ROOK_FROM_F1).endswith("Rfe1 *")
    assert _movetext(ROOK_FROM_A1).endswith("Rae1 *")


def test_two_rooks_on_one_file_are_told_apart_by_their_rank():
    """`R1a2` against `R3a2` — a rank, because the file is what they share.

    This is the case `SCRATCHPAD.md` §9 writes as the risk, `Nbd7` versus `N1d7` versus `Nd7`,
    on the other axis: when the file cannot say it, the rank can, and when the file is what the
    two pieces share the rank is what distinguishes them.

    Returns:
        None
    """
    assert _movetext(ROOKS_ON_A_FILE_FROM_A1).endswith("R1a2 *")
    assert _movetext(ROOKS_ON_A_FILE_FROM_A3).endswith("R3a2 *")


def test_three_queens_need_the_file_and_the_rank_both():
    """`Qd4d8`: one rival shares the file, the other shares the rank, and neither alone says it.

    No game from a standard opening reaches this — it takes three queens of one colour, which
    takes two promotions — so the position is dealt rather than played. The rule is the
    notation's own: the file is written when it alone is enough, the rank when it alone is, and
    both when neither is.

    Returns:
        None
    """
    position = _position(
        [("a1", King(1)), ("d4", Queen(1)), ("d6", Queen(1)), ("h4", Queen(1)), ("a8", King(-1))]
    )

    assert _written(position, [Move(algebraic_to_pos("d4"), algebraic_to_pos("d8"))]) == (
        "1. Qd4d8+ *"
    )


def test_a_pawn_that_takes_something_is_named_by_the_file_it_came_from():
    """`exd5` and `cxd5`: a pawn has no letter, and the file is the whole of its name.

    Returns:
        None
    """
    assert _movetext(PAWN_FROM_E4).endswith("exd5 *")
    assert _movetext(PAWN_FROM_C4).endswith("cxd5 *")


def test_a_pawn_that_does_not_take_anything_is_named_by_its_destination_alone():
    """`e4` and not `e2e4`: the notation drops the square it came from when nothing is taken.

    Returns:
        None
    """
    assert _movetext(["e2e4"]).startswith("1. e4 ")


def test_a_castle_is_written_as_a_castle_and_not_as_a_king_walk():
    """`O-O` and `O-O-O`, both of them, and the rook's own file is what says which.

    The engine's move type for a castle is the single word `castling` with no side in it, so a
    writer that read the name would write `O-O` for both.

    Returns:
        None
    """
    text = _movetext(OPERA_SQUARES)

    assert "12. O-O-O Rd8" in text
    assert "12. O-O Rd8" not in text


def test_a_short_castle_is_written_as_a_short_castle():
    """The other castle, from a line that plays it.

    Returns:
        None
    """
    line = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b1c3", "g8f6", "e1g1", "e8g8"]

    assert "5. O-O O-O" in _movetext(line)


def test_a_move_that_gives_check_is_written_with_a_check_mark():
    """`Bb4+` from the Scholar's mate: the suffix is a claim about the position after the move.

    Returns:
        None
    """
    line = ["e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7"]

    assert _movetext(line).startswith("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#")


def test_a_promotion_is_written_as_the_piece_it_became_and_the_check_it_gave():
    """`e8=Q+`: the promoted piece is named, and the suffix is the position's answer.

    Returns:
        None
    """
    position = _position([("e7", Pawn(1)), ("a1", King(1)), ("a8", King(-1))])
    move = Move(algebraic_to_pos("e7"), algebraic_to_pos("e8"), promotion_piece=Queen(1))

    assert _written(position, [move]) == "1. e8=Q+ *"


def test_a_promotion_that_takes_something_names_the_file_and_the_piece_it_became():
    """`exd8=Q+`: a capture mark and a promotion at once, which is where both halves meet.

    Returns:
        None
    """
    position = _position([("e7", Pawn(1)), ("d8", Rook(-1)), ("a1", King(1)), ("a8", King(-1))])
    move = Move(algebraic_to_pos("e7"), algebraic_to_pos("d8"), promotion_piece=Queen(1))

    assert _written(position, [move]) == "1. exd8=Q+ *"


def test_a_piece_that_cannot_legally_reach_the_square_does_not_make_the_mover_ambiguous():
    """The knight beside it is pinned, so it may not move, so the notation says nothing.

    Two white knights on a1 and d4 can both reach b3. With the a1 knight free, both can, and
    `Ndb3` says which one moved. With a black rook on h1 the a1 knight is pinned against the
    king on e1, may not move at all, and there is nothing left to tell apart — so the
    notation writes `Nb3`. This is the case pseudo-legal disambiguation gets wrong, and it is
    the reason the hint is written from *legal* moves rather than from geometry.

    Returns:
        None
    """
    move = Move(algebraic_to_pos("d4"), algebraic_to_pos("b3"))
    pinned = _position(
        [("e1", King(1)), ("a1", Knight(1)), ("d4", Knight(1)), ("h1", Rook(-1)), ("a8", King(-1))]
    )
    free = _position(
        [("e1", King(1)), ("a1", Knight(1)), ("d4", Knight(1)), ("h8", Rook(-1)), ("a7", King(-1))]
    )

    assert _written(pinned, [move]) == "1. Nb3 *"
    assert _written(free, [move]) == "1. Ndb3 *"


def test_the_writer_replays_the_position_it_is_handed_rather_than_the_starting_one():
    """The same two squares on two boards are two different notations, and both are right.

    One white knight on d4 moving to b3 is written `Nb3`. The same move with a second knight
    on a1 — which can also reach b3 — is written `Ndb3`, because now two knights can go there
    and the notation has to say which. The two boards differ in one piece and nothing else, so
    a writer reading the position cannot tell them apart by accident.

    Returns:
        None
    """
    move = Move(algebraic_to_pos("d4"), algebraic_to_pos("b3"))
    alone = _position([("e1", King(1)), ("d4", Knight(1)), ("h8", King(-1))])
    crowded = _position([("e1", King(1)), ("a1", Knight(1)), ("d4", Knight(1)), ("h8", King(-1))])

    assert _written(alone, [move]) == "1. Nb3 *"
    assert _written(crowded, [move]) == "1. Ndb3 *"


def test_a_move_that_does_not_fit_the_position_is_written_and_claims_no_suffix():
    """A fragment quoted out of a game is still written; what cannot be read is not claimed.

    The move is `e2e4` on a board with nothing on e2, so the replay cannot follow it. The
    token comes from the move itself and no `+` is invented for a position nobody looked at.

    Returns:
        None
    """
    empty = Board((8, 8), setup_pieces=False)

    assert _written(empty, [Move(algebraic_to_pos("e2"), algebraic_to_pos("e4"))]) == "1. e4 *"


def test_a_game_with_no_moves_is_written_as_a_header_and_a_result():
    """Nothing to write is not the same as refusing, and it is not an invented move.

    Returns:
        None
    """
    text = ExportPGN().to_pgn([])

    assert text.endswith("*")
    assert "[Result" in text


def test_the_movetext_is_written_without_a_header_when_there_is_no_game_to_describe():
    """The header is derived rather than left out, so this file exists to prove the header and
    the movetext are two separate things.

    Returns:
        None
    """
    text = ExportPGN().to_pgn([Move(algebraic_to_pos("e2"), algebraic_to_pos("e4"))])

    assert text.startswith("[Event ")
    assert "\n\n1. e4 *" in text


def test_a_piece_that_declares_no_character_is_refused_rather_than_written_as_something():
    """A letter is the piece's own; a piece that declares none has no place in a transcript.

    Returns:
        None
    """
    position = _position([("e2", Piece(1, "strider")), ("a1", King(1)), ("h8", King(-1))])

    with pytest.raises(ValueError, match="declares no character"):
        _written(position, [Move(algebraic_to_pos("e2"), algebraic_to_pos("e3"))])


def test_a_castle_is_read_from_the_rook_and_not_from_the_move_type_when_there_is_no_rook():
    """A hand-built move names its castle in the move type, and that is what is read.

    The rule builds a castle whose move type is the single word `castling`, and the rook's
    square beside it says which. A caller that builds the move itself and does not attach a
    rook has left only the name to go on.

    Returns:
        None
    """
    position = _position([("e1", King(1)), ("a8", King(-1))])
    short = Move(algebraic_to_pos("e1"), algebraic_to_pos("g1"), move_type="castling_kingside")
    long = Move(algebraic_to_pos("e1"), algebraic_to_pos("c1"), move_type="castling_queenside")

    assert _written(position, [short]) == "1. O-O *"
    assert _written(position, [long]) == "1. O-O-O *"


def test_the_writer_replays_from_the_configurations_own_starting_position_by_default():
    """No position handed in means this configuration's opening, which is what a game plays from.

    Returns:
        None
    """
    text = ExportPGN().to_pgn([Move(algebraic_to_pos("e2"), algebraic_to_pos("e4"))])

    assert "1. e4" in text
    assert build_board().rows == 8
