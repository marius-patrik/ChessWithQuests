"""Perft: how many legal moves a position has, counted to a depth.

Every other test in this suite asks a component a question. That is why a promotion bug which
made `Ra8-b8` legal survived 239 passing tests: nobody ever asked how many moves the position
had. Perft asks the one question whose answer is published, so an engine that invents or loses
a move cannot pass.

The expected counts are the standard perft values for the starting position. They are data, not
an oracle computed at test time, so a wrong engine cannot agree with itself.

The regression tests below the gate are here for the same reason. A count only says that
*somebody* is wrong; each of these names one position in which the engine invented or withheld
a move, which is the smallest reproducible form of what the perft numbers were made of and the
only thing that stops a fix being quietly undone.
"""

import copy
from typing import Any, Dict, List, Optional, Tuple

import pytest
from model.game.board import Board
from model.game.configuration import load_default_configuration
from model.game.manager import GameManager
from model.game.move import Move
from model.game.validator import MoveValidator

#: Published perft counts for the standard starting position.
PERFT = [(1, 20), (2, 400), (3, 8902), (4, 197281)]


def legal_moves(board: Board, color: int, rules: Optional[List[Any]] = None) -> List[Move]:
    """Return every legal move for a side in a position.

    Args:
        board: The position to read.
        color: The side to move, 1 for White and -1 for Black.
        rules: The rules in force. A fresh set is built when none is given, which is what a
            one-off question about a position wants.

    Returns:
        List[Move]: The moves that side may play.
    """
    from games.chess.rules import build_rules

    return _composed(build_rules() if rules is None else rules, board).get_all_valid_moves(
        color, board
    )


def _composed(rules: List[Any], board: Board) -> MoveValidator:
    """Build a validator over a rule set without disturbing what that set remembers.

    Args:
        rules: The rules in force.
        board: The position they are being asked about.

    Returns:
        MoveValidator: A validator whose rules keep the history they have built.
    """
    validator = MoveValidator(board)
    validator.set_rules(rules, attach=False)
    return validator


def perft(board: Board, color: int, depth: int, rules: Optional[List[Any]] = None) -> int:
    """Count the leaf nodes of the legal move tree to a depth.

    One rule set is kept for the whole walk and told about every move, because a capture in
    passing is only offered to a rule that was told about the advance that made it possible.
    Whatever a rule remembered is part of what a move changes, so it is snapshotted and put
    back with the board.

    Args:
        board: The position to start from.
        color: The side to move.
        depth: How many plies to search.
        rules: The rules in force. A fresh set is built when none is given.

    Returns:
        int: The number of move sequences of exactly `depth` plies.
    """
    from games.chess.rules import build_rules

    rules = build_rules() if rules is None else rules
    if depth == 0:
        return 1
    moves = _composed(rules, board).get_all_valid_moves(color, board)
    if depth == 1:
        return len(moves)
    total = 0
    for move in moves:
        before = _snapshot(board, rules)
        move.execute(board)
        _notify(rules, board, move)
        total += perft(board, -color, depth - 1, rules)
        _restore(board, rules, before)
    return total


def _snapshot(board: Board, rules: List[Any]) -> Tuple[List[Tuple], List[Dict[str, Any]]]:
    """Record everything about a position that playing a move can change.

    A move changes three things: which piece stands where, whether a piece has moved (which is
    what a first-only advance reads, and what says a rook may still castle), and what the rules
    have remembered (which is the whole of a capture in passing, and of a repetition's count).

    Args:
        board: The position to record.
        rules: The rules whose remembered state to record.

    Returns:
        Tuple: The occupied squares as (square, piece, piece.has_moved) triples, and a deep
        copy of each rule's runtime state.
    """
    squares = [
        ((row, col), piece, piece.has_moved)
        for row in range(board.rows)
        for col in range(board.cols)
        if (piece := board.get_piece_at((row, col))) is not None
    ]
    return squares, [copy.deepcopy(rule.state) for rule in rules]


def _restore(board: Board, rules: List[Any], snapshot: Tuple) -> None:
    """Return a position and its rules to a recorded state.

    Args:
        board: The position to restore.
        rules: The rules whose remembered state to restore.
        snapshot: What `_snapshot` recorded.

    Returns:
        None
    """
    squares, states = snapshot
    for row in range(board.rows):
        for col in range(board.cols):
            board.set_piece_at((row, col), None)
    for square, piece, has_moved in squares:
        piece.has_moved = has_moved
        board.set_piece_at(square, piece)
    board.captured_white.clear()
    board.captured_black.clear()
    for rule, state in zip(rules, states):
        rule.state = copy.deepcopy(state)


def _notify(rules: List[Any], board: Board, move: Move) -> None:
    """Tell every rule a move has been played.

    Args:
        rules: The rules in force.
        board: The board after the move.
        move: The move that was played.

    Returns:
        None
    """
    for rule in rules:
        rule.on_move_made(board, move)


def _starting_board() -> Board:
    """Return the standard starting position.

    Returns:
        Board: A freshly dealt chess board.
    """
    return load_default_configuration().new_board()


@pytest.mark.parametrize("depth,expected", PERFT)
def test_the_starting_position_has_exactly_as_many_moves_as_chess_says(depth, expected):
    """The published counts, asserted exactly at every depth this suite walks.

    Depth four is the deepest one measured here: it takes about half a minute, and depth five
    takes hours. Nothing about the engine changes at that boundary — the positions below are
    the ones that used to be wrong.
    """
    assert perft(_starting_board(), 1, depth) == expected


# --------------------------------------------------------------------------------------
# Regression tests. One invented or withheld move each, in one position.
# --------------------------------------------------------------------------------------


def from_fen(fen: str) -> Board:
    """Build a board from the position part of a FEN.

    Args:
        fen: Ranks separated by slashes, rank eight first, digits counting empty squares, and
            then the side to move, the castling rights and the en passant square.

    Returns:
        Board: The position described. Every piece arrives with its moved flag clear, which
        is what a game that has just been dealt looks like.
    """
    ranks = []
    for rank in fen.split()[0].split("/"):
        row: List[Any] = []
        for character in rank:
            if character.isdigit():
                row.extend([None] * int(character))
            else:
                row.append(_piece(character))
        ranks.append(row)
    ranks.reverse()

    board = Board((len(ranks), len(ranks[0])))
    for row_index, pieces in enumerate(ranks):
        for col_index, piece in enumerate(pieces):
            board.set_piece_at((row_index, col_index), piece)
    return board


def square(position: Tuple[int, int]) -> str:
    """Name a square the way chess does.

    Args:
        position: The (row, col) square, where row zero is White's back rank.

    Returns:
        str: The square's name, such as `e2`.
    """
    return f"{chr(ord('a') + position[1])}{position[0] + 1}"


def moves_of(board: Board, color: int, rules: Optional[List[Any]] = None) -> List[str]:
    """Return every move a side may play, written as `from to`.

    Args:
        board: The position to read.
        color: The side to move.
        rules: The rules in force, for a position that needs remembered state.

    Returns:
        List[str]: The moves, one string each.
    """
    return [
        f"{square(move.start_pos)} {square(move.end_pos)}"
        for move in legal_moves(board, color, rules)
    ]


def test_a_capture_in_passing_may_not_expose_the_king_along_the_rank():
    """White's pawn on d5 may take the pawn on e5 in passing, and may not.

    The pawn it takes is not on the square it lands on, so a legality test that only swapped
    the two squares the move names never lifted it. That left one blocker fewer on the fifth
    rank than there really is, and the rook on h5 reached the king on a5 in the fiction.
    """
    board = from_fen("4k3/8/8/K2Pp2r/8/8/8/8 w - e6 0 1")
    rules = _rules()
    _advance(board, rules, _black_advance(4, 4))

    assert "d5 e6" not in moves_of(board, 1, rules)


def test_a_capture_in_passing_is_offered_when_nothing_is_pinned():
    """The other half of the same rule, so that the fix cannot be 'refuse every capture'.

    The same position without the rook: the pawn may take, and the engine says so.
    """
    board = from_fen("4k3/8/8/3Pp3/8/8/8/7K w - e6 0 1")
    rules = _rules()
    _advance(board, rules, _black_advance(4, 4))

    assert "d5 e6" in moves_of(board, 1, rules)


def test_black_may_not_capture_in_passing_exposing_the_king_along_the_rank():
    """The same exposure with the colours the other way round.

    Black's pawn on b4 would take the pawn on c4 in passing onto c3, emptying both b4 and c4
    and opening the fourth rank to the rook on a4.
    """
    board = from_fen("8/8/8/8/RpPk4/8/8/K7 b - c3 0 1")
    rules = _rules()
    _advance(board, rules, _white_advance(3, 2))

    assert "b4 c3" not in moves_of(board, -1, rules)


def test_black_is_offered_a_capture_in_passing_when_nothing_is_pinned():
    """And the same position without the rook on a4 still offers it.

    Returns:
        None
    """
    board = from_fen("4k3/8/8/8/2pP4/8/8/K7 b - d3 0 1")
    rules = _rules()
    _advance(board, rules, _white_advance(3, 3))

    assert "c4 d3" in moves_of(board, -1, rules)


def test_queenside_castling_is_refused_while_the_rook_has_a_piece_to_cross():
    """A pawn on b1 stops a castle to c1, because the rook has to travel over it.

    The squares tested were only those between the king's own origin and its destination — c1,
    d1 and e1. b1 is on the rook's road and not the king's, so nothing ever looked at it.
    """
    board = from_fen("4k3/8/8/8/8/8/8/Rp2K2R w KQ - 0 1")

    assert "e1 c1" not in moves_of(board, 1)


def test_queenside_castling_is_offered_when_the_rook_has_a_clear_road():
    """The other half of the same rule, so that the fix cannot be 'refuse every castle'.

    Returns:
        None
    """
    board = from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")

    assert {"e1 c1", "e1 g1"} <= set(moves_of(board, 1))


def test_a_royal_piece_off_its_starting_file_is_offered_no_castle_at_all():
    """A king on g1 with a rook on a1 was offered a castle to c1, dragging that rook across
    the board to do it. A castle goes to one of two squares from one particular square, and
    the rule was measuring the king's position from the rook's instead."""
    board = from_fen("4k3/8/8/8/8/8/8/R5KR w - - 0 1")

    assert not [move for move in legal_moves(board, 1) if move.move_type == "castling"]


def test_castling_is_refused_through_a_square_the_king_passes_over():
    """A queen on f2 attacks f1, which the king crosses on its way to g1."""
    board = from_fen("4k3/8/8/8/8/8/5q2/R3K2R w KQ - 0 1")

    assert "e1 g1" not in moves_of(board, 1)


def test_the_right_to_castle_survives_the_castle_that_granted_it():
    """A castle records the colour in its own `castled` set and returns before the test that
    forgets a royal piece that has moved. Without that return the same move both granted the
    right and took it away, and no castle could ever be played."""
    board = from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    rule = _rule_named("CastlingRule")
    move = _offered(board, rule, "e1 g1")

    move.execute(board)
    rule.on_move_made(board, move)

    assert rule.state["castled"] == {1}
    assert rule.available_moves(board, board.get_piece_at((0, 6))) == []


def test_a_two_square_advance_may_not_step_over_a_piece():
    """The path a first-only advance walks has to be empty, and not merely its destination.

    The square in between was tested with the destination's coordinates, so the test passed
    a pawn sitting on a3 straight to a4. This one bug was the whole of the perft(3) and
    perft(4) divergence.
    """
    board = from_fen("4k3/8/8/8/8/N7/P7/4K3 w - - 0 1")

    assert "a2 a4" not in moves_of(board, 1)


def test_a_two_square_advance_is_offered_when_its_path_is_clear():
    """The other half of the same rule.

    Returns:
        None
    """
    board = from_fen("4k3/8/8/8/8/8/P7/4K3 w - - 0 1")

    assert "a2 a4" in moves_of(board, 1)


def test_a_two_square_advance_is_only_offered_from_the_row_it_belongs_to():
    """A pawn that has already reached the fifth rank does not get a fresh two-square
    advance. The piece declares an offset it may use once; it does not declare where that
    offset begins, so the row has to come from the board."""
    board = from_fen("4k3/8/8/P7/8/8/8/4K3 w - - 0 1")

    assert "a5 a7" not in moves_of(board, 1)


def test_black_gets_no_two_square_advance_from_a_row_it_has_left():
    """The same rule for the other colour, whose rows run the other way.

    Returns:
        None
    """
    board = from_fen("4k3/8/p7/8/8/8/8/4K3 b - - 0 1")

    assert "a6 a4" not in moves_of(board, -1)


def test_only_a_declared_kind_is_offered_a_promotion():
    """A rook, a bishop, a knight and a king all reach the far rank. Only the kind the
    promotion names may turn into something else there."""
    board = from_fen("4k3/8/8/8/8/8/8/R3K2R w - - 0 1")

    assert all(move.promotion_piece is None for move in legal_moves(board, 1))


def test_a_pawn_is_offered_a_promotion_for_each_declared_kind():
    """The other half of the same rule, which is what makes the first half a rule and not a
    way of stopping promotions.

    Returns:
        None
    """
    board = from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    kinds = sorted(
        move.promotion_piece.getType()
        for move in legal_moves(board, 1)
        if move.promotion_piece is not None
    )

    assert kinds == ["bishop", "horse", "queen", "rook"]


def test_a_repetition_is_counted_under_the_player_who_is_to_move_next():
    """Shuffling both knights out and back repeats the position after `Nf3 Nf6` every four
    plies, and the third time it occurs is a draw.

    The rule recorded every position under `active_color`, which named the player who had
    just moved when a move was announced and the player who was to move next when the position
    was judged. No position could therefore be seen twice, and the rule could never fire.

    The draw is offered after the ninth ply, not the tenth. The position at the start of the
    game is the first occurrence, the shuffle's fourth ply is the second and its eighth is the
    third — and while the key carried every piece's moved flag, the knight that had been out
    and back was not the knight that had not moved, so each return looked new and the count
    needed one more cycle than the rulebook does.
    """
    game = GameManager()
    rule = _rule_of(game, "ThreefoldRepetitionRule")
    reasons = [_play(game, uci) for uci in ["g1 f3", "g8 f6", "f3 g1", "f6 g8"] * 3]

    assert reasons[:8] == [None] * 8
    assert reasons[8:] == ["threefold repetition"] * 4
    assert max(rule.state["seen"].values()) == 3


def test_asking_whether_the_game_is_over_keeps_what_the_rules_know():
    """Asking a question is not the start of a new game.

    Answering it composes the same rules again, and attaching them a second time wiped the
    history they had built in the game being asked about: every position a repetition had seen
    and every colour that had castled.
    """
    game = GameManager()
    repetition = _rule_of(game, "ThreefoldRepetitionRule")
    for uci in ["g1 f3", "g8 f6", "f3 g1", "f6 g8"] * 2:
        _play(game, uci)
    before = max(repetition.state["seen"].values())

    game.get_result()

    assert before > 1
    assert max(repetition.state["seen"].values()) == before


def test_asking_whether_the_game_is_over_does_not_take_the_clock_away():
    """A flagged player can only lose on time if the rule that judges the clock still has it.

    The same recomposition used to hand every rule `clock=None` whenever no clock was passed,
    so the first question asked of a game silently disarmed the rule that watches the clock.
    """
    game = GameManager()
    game.timer.player_times[0] = 0
    game.active_player = -1

    first = game.get_result()
    second = game.get_result()

    assert first is not None and first.reason == "flag fall"
    assert second is not None and second.reason == "flag fall"


def test_asking_whether_a_move_is_legal_does_not_spend_it():
    """A legality test puts the move on the board and takes it off again, and taking it off
    has to put back each piece's moved flag: that flag is what says a piece has spent its
    one-off advance, and what says a rook may still castle."""
    board = from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")

    first = moves_of(board, 1)
    second = moves_of(board, 1)

    assert first == second
    assert {"e1 c1", "e1 g1"} <= set(first)
    assert all(not piece.has_moved for piece in _pieces(board))


def test_a_move_that_was_only_looked_at_does_not_count_as_a_capture():
    """A move being tested is not a move that happened, and the board's capture lists are how
    the view knows what has been taken."""
    board = from_fen("4k3/3p4/8/8/8/8/8/R3K2R w KQ - 0 1")

    moves_of(board, 1)

    assert board.captured_white == []
    assert board.captured_black == []


def _piece(character: str) -> Any:
    """Build the piece a FEN character stands for.

    Args:
        character: The FEN letter, in either case.

    Returns:
        Any: A piece of that kind and colour.
    """
    from games.chess.pieces.bishop import Bishop
    from games.chess.pieces.knight import Knight
    from games.chess.pieces.king import King
    from games.chess.pieces.pawn import Pawn
    from games.chess.pieces.queen import Queen
    from games.chess.pieces.rook import Rook

    catalogue = {"p": Pawn, "r": Rook, "n": Knight, "b": Bishop, "q": Queen, "k": King}
    return catalogue[character.lower()](1 if character.isupper() else -1)


def _advance(
    board: Board, rules: List[Any], squares: Tuple[Tuple[int, int], Tuple[int, int]]
) -> None:
    """Play the one-off advance that a capture in passing depends on.

    The engine is told a capture is available when the move that allowed it is played, not by
    reading the position off the board, so a test of the capture has to play the advance.

    Args:
        board: The position, holding the advanced piece on the square it reached.
        rules: The rules in force, which are told about the advance.
        squares: The (row, col) square it reached and the one it came from.

    Returns:
        None
    """
    reached, came_from = squares
    piece = board.get_piece_at(reached)
    board.set_piece_at(reached, None)
    board.set_piece_at(came_from, piece)
    move = Move(start_pos=came_from, end_pos=reached, piece=piece)
    move.execute(board)
    _notify(rules, board, move)


def _black_advance(row: int, col: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Return the squares of a black pawn's two-square advance onto the given square.

    Args:
        row: The row the pawn ends on.
        col: The column it ends on.

    Returns:
        Tuple: The square it reached and the one it came from.
    """
    return (row, col), (row + 2, col)


def _white_advance(row: int, col: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Return the squares of a white pawn's two-square advance onto the given square.

    Args:
        row: The row the pawn ends on.
        col: The column it ends on.

    Returns:
        Tuple: The square it reached and the one it came from.
    """
    return (row, col), (row - 2, col)


def _offered(board: Board, rule: Any, wanted: str) -> Move:
    """Return the one offered move written as `from to`.

    Args:
        board: The position to read.
        rule: The rule that offers moves.
        wanted: The move as `from to`, such as `e1 g1`.

    Returns:
        Move: The move, which the caller asserted was on offer.

    Raises:
        LookupError: When the rule offers no such move.
    """
    origin = _origin(wanted)
    for move in rule.available_moves(board, board.get_piece_at(origin)):
        if f"{square(move.start_pos)} {square(move.end_pos)}" == wanted:
            return move
    raise LookupError(f"{wanted} is not offered in this position")


def _origin(wanted: str) -> Tuple[int, int]:
    """Return the square the first half of a move names.

    Args:
        wanted: The move as `e1 g1` or `g1f3`.

    Returns:
        Tuple[int, int]: The (row, col) square the move begins on.
    """
    return int(wanted[1]) - 1, ord(wanted[0]) - ord("a")


def _target(wanted: str) -> Tuple[int, int]:
    """Return the square the second half of a move names.

    Args:
        wanted: The move as `e1 g1` or `g1f3`.

    Returns:
        Tuple[int, int]: The (row, col) square the move ends on.
    """
    where = wanted.index(" ") + 1 if " " in wanted else 2
    return int(wanted[where + 1]) - 1, ord(wanted[where]) - ord("a")


def _pieces(board: Board) -> List[Any]:
    """Return every piece on a board.

    Args:
        board: The board to read.

    Returns:
        List[Any]: The pieces, in board order.
    """
    return [
        board.get_piece_at((row, col))
        for row in range(board.rows)
        for col in range(board.cols)
        if board.get_piece_at((row, col)) is not None
    ]


def _rules() -> List[Any]:
    """Build one instance of every chess rule.

    Returns:
        List[Any]: The rules in force, in declaration order.
    """
    from games.chess.rules import build_rules

    return build_rules()


def _rules_of(game: GameManager) -> List[Any]:
    """Return the rules a live game is being played by.

    Args:
        game: The game whose rules are wanted.

    Returns:
        List[Any]: The rules in force.
    """
    return list(game.move_validator.rules)


def _rule_named(name: str) -> Any:
    """Build a single rule of the given class name.

    Args:
        name: The rule class's name.

    Returns:
        Any: The rule, attached and with nothing remembered.

    Raises:
        AssertionError: When the class is not among the rules chess plays by.
    """
    found = [rule for rule in _rules() if type(rule).__name__ == name]
    assert len(found) == 1, f"expected exactly one {name}, found {len(found)}"
    return found[0]


def _rule_of(game: GameManager, name: str) -> Any:
    """Return one rule out of a live game's rule set.

    Args:
        game: The game whose rules are wanted.
        name: The rule class's name.

    Returns:
        Any: The rule that game is playing by.
    """
    return next(rule for rule in _rules_of(game) if type(rule).__name__ == name)


def _play(game: GameManager, wanted: str) -> Optional[str]:
    """Play one move written as four squares and report the outcome the game then proposes.

    Args:
        game: The game to play in.
        wanted: The move as `from to`, such as `g1 f3`.

    Returns:
        Optional[str]: The reason the game is now over, or None while it continues.

    Raises:
        LookupError: When the move is not offered.
    """
    origin = _origin(wanted)
    target = _target(wanted)
    for move in game.get_valid_moves():
        if move.start_pos == origin and move.end_pos == target:
            assert game.make_move(move), f"{wanted} was offered but could not be played"
            break
    else:
        raise LookupError(f"{wanted} is not offered in this position")
    result = game.get_result()
    return None if result is None else result.reason
