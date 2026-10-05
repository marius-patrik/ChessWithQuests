"""The position record, and all six of its fields.

`games/chess/export/fen.py` used to end in `return f"{board_fen} {turn} - - 0 1"`, which wrote
four constants whatever the game was doing: the castling rights, the en passant target, the
halfmove clock and the fullmove number. A position record's whole claim is that it describes a
position, and four of its six fields were a claim about nothing.

What is here is each field against a fact about the game rather than against a literal the
writer itself produced. The starting position's record is checked against the one every chess
program in the world agrees on, which is a fact about the position rather than about this
code. The rest are played games, and each field is read out of the game and then checked
against the thing that already knew it — the fifty-move rule's own counter for the halfmove
clock, and the castling rule's own conditions for the rights.

**The en passant convention is stated in the writer's module docstring and repeated here**,
because it is a choice rather than a fact: this writer records a target after every two-square
advance, whether or not a capture is actually available to anybody. `EnPassantRule.on_move_made`
keeps exactly that and nothing more, so reading it is reading the game rather than forming a
second opinion about it at write time.
"""

from games.chess.board import build_board
from games.chess.export.algebraic import algebraic_to_pos
from games.chess.export.fen import ExportFEN
from games.chess.pieces.king import King
from games.chess.pieces.rook import Rook
from model.game.board import Board
from model.game.manager import GameManager
from model.game.move import Move
from model.game.rule import Rule

#: The starting position as the whole chess world writes it. Not this repository's output:
#: the string every program agrees on, used here as a fixed point.
START_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

#: A line that leaves both sides' kings and rooks on their own squares, so both sides keep both
#: rights, and whose last move is a pawn's two-square advance, so it also carries a target.
RIGHTS_AND_TARGET = [
    "e2e4",
    "e7e5",
    "g1f3",
    "b8c6",
    "f1c4",
    "f8c5",
    "d2d3",
    "a7a6",
    "d3d4",
    "d7d5",
]

#: A line whose last move takes a pawn in passing, so the offer is spent and so is the
#: target the record would otherwise carry. The capturing pawn has to be on the fifth rank
#: beside the pawn that advanced, which is why this line walks e4-e5 first.
SPENT_OFFER = ["e2e4", "e7e6", "e4e5", "d7d5", "e5d6"]

#: Six plies of development: no capture and no advance, so the clock counts every one.
QUIET_PLIES = ["b1c3", "b8c6", "g1f3", "g8f6", "a1b1", "a8b8"]

#: A capture and a pawn move, then two quiet moves: the clock is reset twice and counts twice.
CAPTURE_AND_QUIET = ["d2d4", "d7d5", "c2c4", "d5c4", "b1c3", "b8c6", "c1g5", "c8g4"]


def _play(squares):
    """Play a game from a list of square names, one pair of squares per move.

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


def _fields(game, fmt="FEN"):
    """Return a written record as its six fields.

    Args:
        game: The game to write.
        fmt: The notation to ask for.

    Returns:
        List[str]: Placement, side to move, castling rights, en passant target, halfmove clock
        and fullmove number.
    """
    return game.transcript(fmt).split(" ")


def _rule(game, name):
    """Return the rule of one name that is in force in a game.

    Found by name rather than by class, because the configuration a game loads is its own copy:
    `games/chess/` imported by path is a different set of class objects from `games.chess`
    imported by name, which is the whole point of `games/chess/__init__.py`. `isinstance`
    against the imported class would never match, and a test that looked would find nothing.

    Args:
        game: The game whose rules to search.
        name: The rule's class name.

    Returns:
        Rule: The instance, so its runtime state can be read.
    """
    return next(rule for rule in game.move_validator.rules if type(rule).__name__ == name)


def test_the_starting_position_is_written_as_the_starting_position():
    """Six fields, and every one of them a fact about where the pieces are.

    The string is the one every chess program agrees on, so this is a fixed point rather than
    a snapshot: the four fields that used to be constants are `KQkq`, `-`, `0` and `1`.

    Returns:
        None
    """
    game = GameManager()

    assert _fields(game) == START_POSITION.split(" ")


def test_a_position_that_has_moved_carries_the_rights_and_the_target_the_moves_earned():
    """Both sides keep both rights, and the last move was a pawn's two-square advance.

    Returns:
        None
    """
    fields = _fields(_play(RIGHTS_AND_TARGET))

    assert fields[2] == "KQkq"
    assert fields[3] == "d6"
    assert fields[4] == "0"
    assert fields[5] == "6"


def test_a_castle_gives_the_right_up_for_the_side_that_castled():
    """After `O-O` the second colour's rights are gone and the first colour's are not.

    This is the castling rule's own condition, read by the record: the royal piece has left
    the file it castles from, and a piece that has moved does not get its one-off back.

    Returns:
        None
    """
    fields = _fields(_play(["e2e4", "e7e5", "f1c4", "g8f6", "g1f3", "f8c5", "e1g1", "e8g8"]))

    assert fields[2] == "-"
    assert _fields(_play(["e2e4", "e7e5", "f1c4", "g8f6", "g1f3", "f8c5", "e1g1"]))[2] == "kq"


def test_a_rook_that_has_moved_gives_its_own_right_up_and_leaves_the_other_alone():
    """`Qkq`: the rook on h1 has travelled and the rook on a1 has not.

    A rook that has left and come home has still moved, and the flag that says so is what the
    castling rule reads and what the record now reads. Nothing else on the board could tell.

    Returns:
        None
    """
    game = _play(
        ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b1c3", "g8f6", "h2h3", "h7h6", "h1h2"]
    )

    assert _fields(game)[2] == "Qkq"


def test_a_king_that_has_moved_gives_up_both_of_its_own_rights():
    """A king that walks one square cannot castle on either side afterwards.

    Returns:
        None
    """
    game = _play(["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b1c3", "g8f6", "e1e2"])

    assert _fields(game)[2] == "kq"


def test_the_record_says_the_second_colours_rights_in_lower_case():
    """`KQkq` and not `KQKQ`, because the case is how a reader tells whose is whose.

    Returns:
        None
    """
    fields = _fields(_play(RIGHTS_AND_TARGET))

    assert fields[2][:2] == "KQ"
    assert fields[2][2:] == "kq"


def test_a_board_too_narrow_to_castle_on_writes_no_rights():
    """Seven files have no rook three files beyond the middle one, and nothing is invented.

    Returns:
        None
    """
    board = Board((5, 7), setup_pieces=False)
    board.set_piece_at((0, 3), King(1))

    assert ExportFEN().to_fen(board).split(" ")[2] == "-"


def test_a_capture_in_passing_ends_the_offer_and_the_record_with_it():
    """The target is the square the last move asked to be recorded on, and the capture is last.

    Returns:
        None
    """
    assert _fields(_play(RIGHTS_AND_TARGET))[3] == "d6"
    assert _fields(_play(SPENT_OFFER))[3] == "-"


def test_a_move_that_is_not_a_two_square_advance_records_no_target():
    """One square forward is not the move the field describes.

    Returns:
        None
    """
    assert _fields(_play(["e2e3"]))[3] == "-"
    assert _fields(_play(["e2e4", "e7e6", "e4e5"]))[3] == "-"


def test_the_halfmove_clock_counts_what_the_fifty_move_rule_counts():
    """One counter, not two: the record's clock is the rule's own number.

    `FiftyMoveRule.state["plies"]` is the plies since the last capture or advance, which is
    the definition of the field. Asserting the two equal after a game that has captures,
    pawn moves and quiet moves in it is what makes it a fact about this code rather than a
    claim in a docstring — and it is why the engine grew no second counter.

    Returns:
        None
    """
    game = _play(CAPTURE_AND_QUIET)
    fields = _fields(game)

    assert int(fields[4]) == _rule(game, "FiftyMoveRule").state["plies"]


def test_the_halfmove_clock_is_reset_by_a_capture_and_by_a_pawn_move():
    """And counted again by anything else, which is the other half of the same assertion.

    Six plies of piece development take nothing and advance nothing, so the clock is still
    what it was. Then a pawn captures and the clock restarts from that ply rather than from
    the game.

    Returns:
        None
    """
    assert _fields(_play(QUIET_PLIES))[4] == "6"
    assert _fields(_play(CAPTURE_AND_QUIET))[4] == "4"


def test_the_fullmove_number_rises_when_the_second_side_has_answered():
    """Move one after one ply, move two after two, and so on.

    Returns:
        None
    """
    assert _fields(_play([]))[5] == "1"
    assert _fields(_play(["e2e4"]))[5] == "1"
    assert _fields(_play(["e2e4", "e7e5"]))[5] == "2"
    assert _fields(_play(["e2e4", "e7e5", "g1f3"]))[5] == "2"


def test_the_record_says_whose_turn_it_is_from_the_game_rather_than_from_a_default():
    """A position with the second side to move is written `b`, which the engine now hands over.

    The writer's own default is still the first colour, because a caller handing it only a
    board has said nothing else; what is asserted here is that the game does say, and that the
    writer reads what it was given.

    Returns:
        None
    """
    assert _fields(_play(["e2e4"]))[1] == "b"
    assert _fields(_play(["e2e4", "e7e5"]))[1] == "w"
    assert ExportFEN().to_fen(build_board()).split(" ")[1] == "w"


def test_a_position_of_any_size_is_written_with_six_fields():
    """Board generalisation extends to the record, not only to the placement.

    Returns:
        None
    """
    for rows, cols in ((8, 8), (10, 10), (5, 7)):
        board = Board((rows, cols), setup_pieces=False)
        board.set_piece_at((0, 0), King(1))

        assert len(ExportFEN().to_fen(board).split(" ")) == 6


def test_a_board_with_no_castle_on_it_writes_the_marker_and_not_an_empty_field():
    """Six fields means six: the format's own marker for a field with nothing in it.

    Returns:
        None
    """
    board = Board((8, 8), setup_pieces=False)
    board.set_piece_at((4, 4), Rook(1))

    placement, turn, rights, target, clock, fullmove = ExportFEN().to_fen(board).split(" ")

    assert (turn, rights, target, clock, fullmove) == ("w", "-", "-", "0", "1")
    assert placement.count("/") == 7


def test_the_kinds_the_rights_are_about_are_read_from_this_configurations_own_rule():
    """A configuration that renamed its royal kind is described by the same code.

    The writer asks the castling rule in its own directory what it calls the two kinds,
    rather than carrying a second opinion of what a king is called. That is what makes a copy
    of `games/chess/` write its own games rather than the original's.

    Returns:
        None
    """
    from games.chess.rules.castling import CastlingRule

    rule = CastlingRule()

    assert ExportFEN()._rights_kinds() == (rule.value["royal_kind"], rule.value["rook_kind"])
    assert isinstance(rule, Rule)
