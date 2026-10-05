"""The rules of draughts, one position at a time.

Perft counts nodes. It cannot say *which* rule is wrong, and it says nothing at all about the
rules that never change a move: when a game is over, what a draw is, how many kings a side may
hold. This file asks those questions directly, one position each, and every test here fails
if the rule it covers is broken rather than if a total moves.

**Squares are numbered 1 to 32** in the standard way — four playable squares to a row, rows
counted from the near side, so 1 to 4 is White's back row and 29 to 32 is the crown row.
`tests/test_draughts_perft.py` owns that numbering and this file borrows it, so there is one
numbering rather than two that could quietly disagree.

**Three of the rules tested here are not English draughts and are tested as variants.**
`max_capture`, `LimitedKingsRule` and `InsufficientMaterialRule` are all off their real
settings in the rulebook, and each is tested twice: once at the setting this configuration
ships, once at the other one, so that both the switch and the thing it switches between are
pinned.
"""

import pathlib
import shutil
from typing import Any, Dict, List, Optional, Tuple

import pytest

from model.game.board import Board
from model.game.configuration import load_configuration
from model.game.games import games_root
from model.game.rule import KIND_DRAW, KIND_WIN
from model.game.validator import MoveValidator
from tests.test_draughts_perft import coordinates, square_of

#: White and Black.
WHITE: int = 1
BLACK: int = -1

#: The piece codes a position is written in: the colour, then `m` for a man or `k` for a king.
CODES: Dict[str, str] = {"wm": "man", "wk": "king", "bm": "man", "bk": "king"}


def board_with(placement: Dict[int, str]) -> Board:
    """Build a board from a position written as square number to piece code.

    Args:
        placement: Square number to a code from `CODES`, such as `{9: "wm", 14: "bm"}`.

    Returns:
        Board: An eight by eight board holding exactly those pieces.
    """
    from games.checkers.pieces.king import King
    from games.checkers.pieces.man import Man

    board = Board((8, 8))
    for square, code in placement.items():
        colour = WHITE if code[0] == "w" else BLACK
        board.set_piece_at(
            coordinates(square), Man(colour) if CODES[code] == "man" else King(colour)
        )
    return board


def rules_with(**settings: Any) -> List[Any]:
    """Build the checkers rules, with some of them configured differently.

    Args:
        **settings: Rule label prefix and field name to a value, such as
            `max_capture=True`. The label a rule carries is its `default_name`.

    Returns:
        List[Any]: The rules in force, in declaration order.
    """
    from games.checkers.rules import build_rules

    rules = build_rules()
    for rule in rules:
        for key, value in settings.items():
            if key in rule.value:
                rule.value[key] = value
    return rules


def rules_of(rules: List[Any], label: str) -> Any:
    """Return the one rule carrying a label.

    Args:
        rules: The rules in force.
        label: The rule's `default_name`.

    Returns:
        Any: The rule.

    Raises:
        AssertionError: When no rule or more than one carries the label.
    """
    found = [rule for rule in rules if rule.label == label]
    assert len(found) == 1, f"expected exactly one rule labelled {label!r}, found {len(found)}"
    return found[0]


def legal_moves(board: Board, colour: int, rules: Optional[List[Any]] = None) -> List[str]:
    """Return every legal move for a side, written as `from-to` in the square numbering.

    Args:
        board: The position to read.
        colour: The side to move.
        rules: The rules in force. The English draughts defaults are built when none is given.

    Returns:
        List[str]: The moves, sorted, one string each.
    """
    rules = rules_with() if rules is None else rules
    validator = MoveValidator(board)
    validator.set_rules(rules, attach=False)
    return sorted(
        f"{square_of(*move.start_pos)}-{square_of(*move.end_pos)}"
        for move in validator.get_all_valid_moves(colour, board)
    )


def the_move(board: Board, colour: int, name: str, rules: Optional[List[Any]] = None) -> Any:
    """Return the one offered move written as `from-to`.

    Args:
        board: The position to read.
        colour: The side to move.
        name: The move as `from-to`, such as `17-10`.
        rules: The rules in force.

    Returns:
        Any: The move, with whatever its rule attached.

    Raises:
        LookupError: When the move is not offered.
    """
    origin, land = name.split("-")
    rules = rules_with() if rules is None else rules
    validator = MoveValidator(board)
    validator.set_rules(rules, attach=False)
    for move in validator.get_all_valid_moves(colour, board):
        if (
            square_of(*move.start_pos),
            square_of(*move.end_pos),
        ) == (int(origin), int(land)):
            return move
    raise LookupError(f"{name} is not offered in this position")


def on(board: Board, square: int) -> Any:
    """Return the piece standing on a numbered square.

    Args:
        board: The position to read.
        square: The square's number.

    Returns:
        Any: The piece, or None.
    """
    return board.get_piece_at(coordinates(square))


# --------------------------------------------------------------------------------------
# The board.
# --------------------------------------------------------------------------------------


def test_a_game_of_checkers_starts_with_twelve_men_a_side_on_the_three_nearest_rows():
    """Twenty-four pieces, all of them men, and none of them on a light square.

    Returns:
        None
    """
    from games.checkers.board import build_board, is_played_square

    board = build_board()
    pieces = [
        (row, col)
        for row in range(8)
        for col in range(8)
        if board.get_piece_at((row, col)) is not None
    ]
    assert len(pieces) == 24
    assert all(board.get_piece_at(where).getType() == "man" for where in pieces)
    assert all(is_played_square(row, col) for row, col in pieces)
    assert sum(1 for row, _col in pieces if row in (0, 1, 2)) == 12
    assert sum(1 for row, _col in pieces if row in (5, 6, 7)) == 12


def test_a_side_has_seven_moves_in_the_opening_and_not_eight():
    """Seven, because the man on the edge of its own front row has only one square to step to.

    Returns:
        None
    """
    from games.checkers.board import build_board

    assert len(legal_moves(build_board(), WHITE)) == 7


def test_the_english_draughts_starting_position_refuses_any_board_but_its_own():
    """A ten by ten board has no English draughts starting position, and says so.

    Returns:
        None
    """
    from games.checkers.board import build_board

    with pytest.raises(ValueError, match="starting position"):
        build_board(10, 10)


# --------------------------------------------------------------------------------------
# Men.
# --------------------------------------------------------------------------------------


def test_a_man_steps_one_square_forward_diagonally_and_to_nowhere_else():
    """The man on 9 has exactly two moves, both forwards. A man that could slide, or step
    sideways, or step backwards, would offer more than two.

    Returns:
        None
    """
    assert legal_moves(board_with({9: "wm", 32: "bk"}), WHITE) == ["9-13", "9-14"]


def test_a_man_at_the_crown_row_cannot_step_off_the_board():
    """The man on 26 is one row from the end and offers only the two squares that exist.

    Returns:
        None
    """
    assert legal_moves(board_with({26: "wm", 1: "bk"}), WHITE) == ["26-30", "26-31"]


def test_a_man_captures_forwards_only():
    """The man on 18 has four black men beside it, two ahead and two behind.

    It may take either of the two in front and neither of the two behind. A generator that let
    a man leap backwards would offer 18-9 and 18-11 as well, and a generator that let a man
    leap two squares would offer more than that again.

    Returns:
        None
    """
    board = board_with({18: "wm", 14: "bm", 15: "bm", 22: "bm", 23: "bm"})

    assert legal_moves(board, WHITE) == ["18-25", "18-27"]


def test_a_man_that_reaches_the_far_row_is_crowned_and_is_not_removed():
    """Stepping onto 30 crowns the man. It is still on the board afterwards, as a king.

    The removal rule of international draughts — the man comes off the board and the game
    continues with one piece fewer — is not English draughts, and this is the position that
    tells the two apart.

    Returns:
        None
    """
    board = board_with({26: "wm", 1: "bk"})
    move = the_move(board, WHITE, "26-30")
    assert move.promotion_piece is not None
    assert move.promotion_piece.getType() == "king"

    move.execute(board)

    assert on(board, 26) is None
    assert on(board, 30) is not None
    assert on(board, 30).getType() == "king"
    assert on(board, 30).getColor() == WHITE
    assert board.captured_white == []
    assert board.captured_black == []


def test_a_man_that_is_crowned_by_a_jump_arrives_a_king_and_stops_there():
    """The man on 21 leaps the black man on 25 and lands on 30, which is the crown row.

    It becomes a king on arrival and the move ends. There is one jump, one victim, and the
    piece that lands is a king — not a man that jumps on as a king it has only just become,
    and not a man still uncrowned.

    Returns:
        None
    """
    board = board_with({21: "wm", 25: "bm", 1: "bk"})
    move = the_move(board, WHITE, "21-30")

    assert move.captured_count == 1
    assert len(move.captures) == 1
    assert move.captures[0] == coordinates(25)
    move.execute(board)

    assert on(board, 30).getType() == "king"
    assert on(board, 25) is None
    assert len(board.captured_black) == 1
    assert board.captured_white == []


def test_a_black_man_is_crowned_on_its_own_far_row():
    """The same rule with the rows the other way round, which is what a derived rule gets wrong.

    Returns:
        None
    """
    board = board_with({6: "bm", 2: "wm"})
    move = the_move(board, BLACK, "6-1")

    assert move.promotion_piece is not None
    move.execute(board)

    assert on(board, 1).getType() == "king"
    assert on(board, 1).getColor() == BLACK


# --------------------------------------------------------------------------------------
# Kings.
# --------------------------------------------------------------------------------------


def test_a_king_steps_one_square_along_every_diagonal():
    """Four squares from the middle of the board — one in each direction, and no others.

    Rule 1.17: an ordinary move of a king "is from one square diagonally forward or backward,
    left or right to an immediately neighbouring vacant square". A king that slid would offer
    eleven squares from here, the four nearest and seven further along the same diagonals.

    Returns:
        None
    """
    assert legal_moves(board_with({22: "wk"}), WHITE) == ["22-17", "22-18", "22-25", "22-26"]


def test_a_king_jumps_one_square_over_exactly_one_piece():
    """The king on 1 walks over the black man on 6 and lands on the one square beyond it.

    Rule 1.21 gives a king's capturing move as a man's "but may be in a forward or backward
    direction": over the adjacent piece, onto the next square. A king that could jump from any
    distance would offer five moves here, the four it cannot reach in English draughts
    included.

    Returns:
        None
    """
    assert legal_moves(board_with({1: "wk", 6: "bm", 20: "bk"}), WHITE) == ["1-10"]


def test_a_capture_forbids_the_king_its_own_quarter_square():
    """Capturing is compulsory, so a king that may take does not also step.

    Returns:
        None
    """
    assert legal_moves(board_with({22: "wk", 26: "bm"}), WHITE) == ["22-31"]


def test_a_king_stops_at_the_first_piece_on_its_diagonal_whether_or_not_it_may_take_it():
    """The white man on 15 is the king's own and ends the diagonal, so 1-10 is the whole move
    and 19, 24 and 28 are not offered at all.

    A king that walked over whatever stood in its way, own pieces included, would offer four
    moves here.

    Returns:
        None
    """
    assert legal_moves(board_with({1: "wk", 6: "bm", 15: "wm"}), WHITE) == ["1-10"]


def test_a_king_jumps_backwards_as_well_as_forwards():
    """The king on 22 has a black man beside it on each side and may take either.

    The man on 17 is behind it — towards the rows it came from — and taking it is the one
    movement a man is never allowed. This is the whole difference between the two kinds.

    Returns:
        None
    """
    assert legal_moves(board_with({22: "wk", 17: "bm", 25: "bm"}), WHITE) == ["22-13", "22-29"]


def test_no_piece_may_end_a_move_on_an_occupied_square():
    """A king is one square away from a black man and may not simply walk onto it.

    The compulsory capture is switched off for this position on purpose. Left on, the rule
    about captures refuses the move by accident — it refuses every move that takes nothing
    while a chain exists — and a rule that only holds a geometry in place while another rule
    happens to be beside it is not holding it in place. With the compulsory capture off, this
    is the only thing refusing the move, and the king jumps over the man instead.

    Returns:
        None
    """
    board = board_with({22: "wk", 26: "bm"})
    rules = rules_with(mandatory=False)
    offered = legal_moves(board, WHITE, rules)

    assert "22-26" not in offered
    assert "22-31" in offered


# --------------------------------------------------------------------------------------
# Capturing.
# --------------------------------------------------------------------------------------


def test_a_capture_is_compulsory_even_for_a_piece_that_cannot_take():
    """The man on 1 could step quietly to 5 or 6. It may not, because the man on 9 can take.

    Returns:
        None
    """
    board = board_with({1: "wm", 9: "wm", 14: "bm"})

    assert legal_moves(board, WHITE) == ["9-18"]


def test_a_quiet_move_is_offered_when_nothing_can_be_taken():
    """The other half of the same rule, so that the fix cannot be "refuse every quiet move".

    Returns:
        None
    """
    assert legal_moves(board_with({9: "wm", 32: "bk"}), WHITE) == ["9-13", "9-14"]


def test_a_chain_may_not_be_abandoned_part_way():
    """The king on 1 takes the man on 6 and lands on 10, and from 10 it can take the man on
    15 as well — so the only moves offered are the three that do both.

    1-10 is not offered at all. A generator that recorded a chain wherever it happened to
    stop, and offered the stops as well as the ends, would offer four moves here and count a
    different tree at every depth from three.

    Returns:
        None
    """
    board = board_with({1: "wk", 6: "bm", 15: "bm"})

    assert legal_moves(board, WHITE) == ["1-19"]
    assert the_move(board, WHITE, "1-19").captured_count == 2


def test_a_chain_which_cannot_be_continued_may_be_played_at_its_own_length():
    """The other half of the same rule, so that the fix cannot be "no chain is ever finished".

    With only the man on 6 to take there is nothing to continue with, so 1-10 is the whole move
    and it is legal. A king that slid would also reach 15, 19, 24 and 28 from here.

    Returns:
        None
    """
    board = board_with({1: "wk", 6: "bm", 20: "bk"})

    assert legal_moves(board, WHITE) == ["1-10"]


def test_a_piece_may_not_take_the_same_victim_twice_in_one_chain():
    """The victim is lifted from the board as the chain takes it, so a king that comes back
    across the square it has just emptied finds nothing there.

    Returns:
        None
    """
    from games.checkers.rules.chains import chains_for

    board = board_with({1: "wk", 6: "bm"})
    chains = chains_for(board, on(board, 1), "man")

    assert all(len(captures) == len(set(captures)) for _, captures in chains)
    assert all(len(captures) == 1 for _, captures in chains)


# --------------------------------------------------------------------------------------
# The maximum capture rule, which English draughts does not have.
# --------------------------------------------------------------------------------------


def test_by_default_a_short_chain_may_be_chosen_beside_a_long_one():
    """The rulebook's game: where two jumps are available the player may select either.

    The man on 9 takes one piece and stops; the man on 13 takes two and stops. Neither chain
    can be continued, so both are complete moves, and English draughts lets the player have
    either.

    Returns:
        None
    """
    board = board_with({9: "wm", 13: "wm", 14: "bm", 17: "bm", 25: "bm"})

    assert legal_moves(board, WHITE) == ["13-29", "9-18"]


def test_the_maximum_capture_switch_leaves_only_the_longest_chain():
    """The international, Brazilian, Czech, Italian and Spanish rule, switched on.

    Returns:
        None
    """
    board = board_with({9: "wm", 13: "wm", 14: "bm", 17: "bm", 25: "bm"})
    rules = rules_with(max_capture=True)

    assert legal_moves(board, WHITE, rules) == ["13-29"]


def test_the_maximum_capture_switch_refuses_a_short_chain_outright():
    """The switch has to bind the legality test and not only the offered move list.

    A rule that filtered the list and left `permits_move` alone would offer only the longest
    chains and still accept a short one handed to it by something else, which is a rule that
    can be argued with. Both chains are built by hand here so that the test is asking the
    question directly rather than trusting the offer list to have filtered it already.

    Returns:
        None
    """
    from games.checkers.moves import HopMove

    board = board_with({9: "wm", 13: "wm", 14: "bm", 17: "bm", 25: "bm"})
    short = HopMove(
        start_pos=coordinates(9),
        end_pos=coordinates(18),
        hops=(coordinates(18),),
        captures=(coordinates(14),),
        piece=on(board, 9),
        move_type="capture",
    )
    long = HopMove(
        start_pos=coordinates(13),
        end_pos=coordinates(29),
        hops=(coordinates(21), coordinates(29)),
        captures=(coordinates(17), coordinates(25)),
        piece=on(board, 13),
        move_type="capture",
    )

    assert rules_of(rules_with(max_capture=True), "Capture").permits_move(board, short) is False
    assert rules_of(rules_with(max_capture=True), "Capture").permits_move(board, long) is True
    assert rules_of(rules_with(), "Capture").permits_move(board, short) is True


# --------------------------------------------------------------------------------------
# The hop sequence a chain carries.
# --------------------------------------------------------------------------------------


def test_a_chain_carries_its_whole_route_and_victims_and_gives_the_board_back_unchanged():
    """The chain 19x15-6 to 1 records three squares and two victims, and undoes exactly.

    Returns:
        None
    """
    board = board_with(
        {
            19: "bm",
            15: "wm",
            6: "wm",
            2: "wm",
            3: "wm",
            4: "wm",
            5: "wm",
            7: "wm",
            8: "wm",
            11: "wm",
            12: "wm",
            21: "bm",
            24: "bm",
            25: "bm",
            27: "bm",
            28: "bm",
            29: "bm",
            30: "bm",
            31: "bm",
            32: "bm",
        }
    )
    before = _fingerprint(board)
    move = the_move(board, BLACK, "19-1")

    assert move.route == tuple(coordinates(square) for square in (19, 10, 1))
    assert len(move.hops) == 2
    assert list(move.captures) == [coordinates(15), coordinates(6)]

    applied = move.apply_to_board(board)

    assert on(board, 15) is None
    assert on(board, 6) is None
    assert on(board, 1).getType() == "king"
    assert [piece.getType() for piece in move.captured_pieces] == ["man", "man"]
    assert len(board.captured_white) == 2

    move.unapply_from_board(board, applied)

    assert _fingerprint(board) == before


def test_a_chain_that_cannot_be_played_is_refused_whole():
    """A chain whose route runs through a square something stands on is not a move.

    Returns:
        None
    """
    from games.checkers.moves import HopMove

    board = board_with({19: "wm", 15: "bm", 6: "bm", 10: "bm"})
    impossible = HopMove(
        start_pos=coordinates(19),
        end_pos=coordinates(10),
        hops=(coordinates(14), coordinates(10)),
        captures=(coordinates(15), coordinates(10)),
        piece=on(board, 19),
        move_type="capture",
    )

    assert impossible.apply_to_board(board) is None
    assert on(board, 19) is not None
    assert on(board, 15) is not None
    assert on(board, 10) is not None


def _fingerprint(board: Board) -> Tuple[Any, ...]:
    """Return everything about a board that a move changes.

    Args:
        board: The position to read.

    Returns:
        Tuple[Any, ...]: Square, piece identity, moved flag and kind for every piece, plus the
        two capture lists.
    """
    return (
        tuple(
            (row, col, id(board.get_piece_at((row, col))), board.get_piece_at((row, col)).has_moved)
            for row in range(8)
            for col in range(8)
            if board.get_piece_at((row, col)) is not None
        ),
        tuple(board.captured_white),
        tuple(board.captured_black),
    )


# --------------------------------------------------------------------------------------
# Crowning, and how many kings a side may hold.
# --------------------------------------------------------------------------------------


def test_by_default_a_side_may_crown_a_third_king():
    """The regression. This rule shipped capping kings at two, and two kings is a real
    position in a real game: a man one step from the crown row then simply could not be
    crowned, and nothing said why. A sweep of random games found three such positions in
    2885, every one of them a man that had walked to the crown row beside a side that already
    held two kings.

    Returns:
        None
    """
    board = board_with({26: "wm", 21: "wm", 1: "wk", 3: "wk", 32: "bk"})

    assert "26-30" in legal_moves(board, WHITE)
    assert "21-25" in legal_moves(board, WHITE) or "21-29" in legal_moves(board, WHITE)


def test_the_kings_cap_switches_a_crowning_off_at_the_limit():
    """And the cap works when it is set, which is what makes the default above a decision
    rather than a rule that does nothing.

    Returns:
        None
    """
    board = board_with({26: "wm", 1: "wk", 3: "wk", 32: "bk"})

    assert "26-30" not in legal_moves(board, WHITE, rules_with(max_kings=2))
    assert "26-30" in legal_moves(board, WHITE, rules_with(max_kings=3))
    assert "26-30" in legal_moves(board, WHITE)


def test_the_kings_cap_does_not_refuse_a_move_that_crowns_nothing():
    """A cap on kings is not a cap on men. A side holding no kings may still move its men.

    Returns:
        None
    """
    board = board_with({9: "wm", 32: "bk"})
    rules = rules_with(max_kings=0)

    assert legal_moves(board, WHITE, rules) == ["9-13", "9-14"]


# --------------------------------------------------------------------------------------
# Immobilisation: a side that cannot move has lost.
# --------------------------------------------------------------------------------------


def _outcome_for(board: Board, colour: int, rules: Optional[List[Any]] = None) -> Any:
    """Ask every rule in force whether the game is over.

    Args:
        board: The position as it stands.
        colour: Whose turn it is. A rule cannot work that out from a board alone, so it is
            handed over rather than guessed.
        rules: The rules in force.

    Returns:
        Any: The outcome the rules resolve to, or None while the game continues.
    """
    rules = rules_with() if rules is None else rules
    validator = MoveValidator(board)
    validator.set_rules(rules, attach=False, active_color=colour)
    return validator.resolve_outcome(board)


def test_a_side_with_no_pieces_at_all_has_lost():
    """Black has nothing. White has won, and the game says so.

    Returns:
        None
    """
    result = _outcome_for(board_with({9: "wm"}), BLACK)

    assert result is not None
    assert result.kind == KIND_WIN
    assert result.winner == WHITE


def test_a_side_whose_pieces_are_all_walled_in_has_lost():
    """The man on 1 is boxed in by the men on 5 and 6, and the man on 6 cannot be jumped
    because 10 — the square beyond it — is occupied as well.

    No legal move is a loss and not a draw, which is the rule that separates draughts from
    chess and is the whole content of this file's `ImmobilisationRule`. Chess calls the same
    position a stalemate and the view draws it.

    Returns:
        None
    """
    board = board_with({1: "wm", 5: "bm", 6: "bm", 10: "bm", 32: "bk"})
    assert legal_moves(board, WHITE) == []

    result = _outcome_for(board, WHITE)

    assert result.kind == KIND_WIN
    assert result.winner == BLACK
    assert result.reason == "immobilised"


def test_a_side_that_can_still_move_has_not_lost():
    """The same board with the wall opened by one square.

    Returns:
        None
    """
    assert _outcome_for(board_with({1: "wm", 6: "bm", 32: "bk"}), WHITE) is None


def test_a_side_with_one_piece_walled_in_has_lost_even_though_it_still_has_a_piece():
    """Immobilisation is about having no *move*, not about having no *piece*.

    The man on 29 is on the crown row with the man on 25 in the only square it could reach,
    and the square it would land on after jumping that man is off the board.

    Returns:
        None
    """
    board = board_with({29: "wm", 25: "bm", 1: "bk"})

    assert legal_moves(board, WHITE) == []
    assert _outcome_for(board, WHITE).kind == KIND_WIN


def test_immobilisation_asks_the_rules_rather_than_reading_the_board_itself():
    """A side whose quiet moves are all forbidden is not stuck while a capture is on offer.

    The man on 1 has two quiet steps and no capture, so both of its steps are refused while
    any capture exists; the man on 9 has a capture, so the side can still move. A rule that
    asked "can this piece move?" rather than "can this side move?" would call White immobile
    on the strength of the piece that cannot.

    Returns:
        None
    """
    board = board_with({1: "wm", 9: "wm", 14: "bm"})

    assert legal_moves(board, WHITE) == ["9-18"]
    assert _outcome_for(board, WHITE) is None


# --------------------------------------------------------------------------------------
# The three draws.
# --------------------------------------------------------------------------------------


def test_forty_moves_of_king_shuffling_is_a_draw_because_a_king_makes_no_progress():
    """Eighty plies in which only kings moved and nothing was taken.

    Chess calls fifty moves by each side fifty-move rule. English draughts draws at forty
    moves each — rule 1.32.2 — and for a different reason: what matters is not the number but
    *progress*, and a king can only ever retrace ground it has already covered, so eighty plies
    of it have advanced nothing at all. A man that goes forward is progress even when it is
    crowned on arrival, because it got there.

    Returns:
        None
    """
    board = board_with({22: "wk", 32: "bk"})
    fifty = rules_of(rules_with(), "Fifty-move rule")
    quiet_king_move = the_move(board, WHITE, "22-17")

    for _ in range(80):
        fifty.on_move_made(board, quiet_king_move)

    assert fifty.state["plies"] == 80
    assert fifty.outcome(board).kind == KIND_DRAW


def test_the_draw_is_not_proposed_one_ply_early():
    """The boundary itself, so that an off-by-one in the comparison is caught.

    Returns:
        None
    """
    board = board_with({22: "wk", 32: "bk"})
    fifty = rules_of(rules_with(), "Fifty-move rule")
    quiet_king_move = the_move(board, WHITE, "22-17")

    for _ in range(79):
        fifty.on_move_made(board, quiet_king_move)

    assert fifty.outcome(board) is None

    fifty.on_move_made(board, quiet_king_move)

    assert fifty.outcome(board).kind == KIND_DRAW


def test_moving_a_man_counts_as_progress_and_starts_the_count_again():
    """The other half of the rule, and the reason it is a draughts rule and not chess's.

    Returns:
        None
    """
    board = board_with({9: "wm", 22: "wk", 32: "bk"})
    fifty = rules_of(rules_with(), "Fifty-move rule")
    quiet_king_move = the_move(board, WHITE, "22-17")
    for _ in range(79):
        fifty.on_move_made(board, quiet_king_move)

    assert fifty.state["plies"] == 79
    assert fifty.outcome(board) is None

    fifty.on_move_made(board, the_move(board, WHITE, "9-13"))

    assert fifty.state["plies"] == 0
    assert fifty.outcome(board) is None


def test_taking_a_piece_starts_the_count_again():
    """A capture is progress however short the chain was.

    Returns:
        None
    """
    fifty = rules_of(rules_with(), "Fifty-move rule")

    # A quiet move and a capture cannot be offered in one position, because a capture is
    # compulsory and forbids the quiet ones, so each is taken from a position that offers it.
    quiet_board = board_with({22: "wk", 32: "bk"})
    quiet_king_move = the_move(quiet_board, WHITE, "22-17")
    for _ in range(79):
        fifty.on_move_made(quiet_board, quiet_king_move)

    capture_board = board_with({22: "wk", 32: "bk", 26: "bm"})
    fifty.on_move_made(capture_board, the_move(capture_board, WHITE, "22-31"))

    assert fifty.state["plies"] == 0


def test_the_fifty_move_rule_can_be_set_to_whatever_a_club_plays():
    """It is a configured value rather than a constant, and a rule that cannot be changed is
    not configuration.

    Returns:
        None
    """
    board = board_with({22: "wk", 32: "bk"})
    fifty = rules_of(rules_with(plies=40), "Fifty-move rule")
    quiet_king_move = the_move(board, WHITE, "22-17")

    for _ in range(40):
        fifty.on_move_made(board, quiet_king_move)

    assert fifty.outcome(board).kind == KIND_DRAW


def test_a_draw_needs_both_players_to_agree_to_it():
    """An offer on its own is not a draw, and a game that continues is not a draw.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    board = board_with({9: "wm", 32: "bk"})
    agreement = rules_of(build_rules(), "Draw by agreement")

    assert agreement.outcome(board) is None
    agreement.offer()
    assert agreement.status(board) == "Draw offered"
    assert agreement.outcome(board) is None

    agreement.accept()
    assert agreement.status(board) is None
    assert agreement.outcome(board).kind == KIND_DRAW


def test_a_declined_draw_offer_leaves_no_draw_behind():
    """Declining puts the board back where it was before the offer was ever made.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    board = board_with({9: "wm", 32: "bk"})
    agreement = rules_of(build_rules(), "Draw by agreement")
    agreement.offer()
    agreement.decline()

    assert agreement.status(board) is None
    assert agreement.outcome(board) is None


# --------------------------------------------------------------------------------------
# What the game has no concept of.
# --------------------------------------------------------------------------------------


def test_nothing_in_this_game_can_be_in_check():
    """A king here is a crowned man, and it is taken like any other piece, so no rule declares
    a royal kind and the engine's check machinery has nothing to find.

    Returns:
        None
    """
    board = board_with({1: "wk", 6: "bk"})
    validator = MoveValidator(board)
    validator.set_rules(rules_with(), attach=False)

    assert validator.royal_kinds() == []
    assert validator.is_check(WHITE, board) is False
    assert validator.is_checkmate(WHITE, board) is False


# --------------------------------------------------------------------------------------
# A configuration is a directory, and a copy of it plays its own rules.
# --------------------------------------------------------------------------------------


#: The shipped king's file with its step length changed, so a copied configuration plays a
#: different game from the original. The shipped king steps one square, which is WCDF English
#: draughts; the copy below slides, which is the international king.
#: Resolved through `games_root()` rather than as a relative path from the working directory,
#: because this module is read at import time: a bare `games/...` path made the whole file
#: uncollectable from anywhere but the repository root.
FLYING_KING = (
    (pathlib.Path(games_root()) / "checkers" / "pieces" / "king.py")
    .read_text(encoding="utf-8")
    .replace("max_steps=1", "max_steps=None")
)


@pytest.fixture
def copied_checkers(tmp_path):
    """Copy the shipped checkers configuration into a throwaway `games/` root.

    The copy has its king rewritten to slide any distance, which is the international king and
    the opposite of the English one that ships. If the copy's rules are its own, the copy plays
    a different game from the original; if the copy reached back into `games.checkers`, it
    would play the original and the edit would be invisible.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        str: The path of the `games/` root holding the copy.
    """
    root = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / "checkers",
        root / "house",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (root / "house" / "pieces" / "king.py").write_text(FLYING_KING, encoding="utf-8")
    return str(root)


def test_a_copied_checkers_configuration_loads_its_own_rules(copied_checkers):
    """Every rule in the copy is the copy's own, loaded from the copy's directory.

    Returns:
        None
    """
    configuration = load_configuration("house", root=copied_checkers)

    assert configuration.rules
    for rule in configuration.rules:
        assert type(rule).__module__.startswith("_configuration_"), type(rule).__name__


def test_a_copied_checkers_configuration_plays_its_own_rules_not_the_originals(copied_checkers):
    """The behavioural proof: the copy's king slides, the original's steps.

    The chess configuration's rules tree still imports by absolute path and is shared with a
    copy, which `tests/test_configuration_copying.py` pins as a known gap. That is exactly
    the failure this test is here to keep out of checkers: a variant that looks edited and
    plays the original, with nothing erroring and nothing warning.

    Returns:
        None
    """
    original = load_configuration("checkers")
    variant = load_configuration("house", root=copied_checkers)

    assert len(legal_moves(_lone_king(original, 22), WHITE)) == 4
    assert len(legal_moves(_lone_king(variant, 22), WHITE)) == 11


def test_the_shipped_checkers_configuration_loads_itself():
    """Converting to relative imports must not break the configuration that ships.

    Returns:
        None
    """
    configuration = load_configuration("checkers")

    assert configuration.name == "checkers"
    assert configuration.board.dimensions == (8, 8)
    assert configuration.pieces
    assert configuration.rules
    assert configuration.quests
    assert len(configuration.rules) == 8
    # Composed out of `pieces/` rather than listed, so the catalogue is the directory: two
    # kinds, `king.py` before `man.py` by file name. Nothing plays by this order — the board
    # places what it is told to — so it is the file order the assertion is about.
    assert [piece.__name__ for piece in configuration.pieces] == ["King", "Man"]
    assert configuration.clocks and [
        clock.__class__.__name__ for clock in configuration.clocks
    ] == ["Fischer"]
    assert [writer.formats()[0] for writer in configuration.exporters] == [
        "Letter",
        "Field-Field-Extra",
    ]


def _lone_king(configuration: Any, square: int) -> Board:
    """Put a configuration's own king on a board of its own and nothing else on it.

    The class is taken from the configuration rather than imported, because importing would
    hand back the original's piece and prove nothing about the copy.

    Args:
        configuration: The loaded configuration.
        square: The square number to stand the king on.

    Returns:
        Board: An empty board with that configuration's king on that square.
    """
    board = configuration.new_board()
    for row in range(8):
        for col in range(8):
            board.set_piece_at((row, col), None)
    king = next(cls for cls in configuration.pieces if cls.__name__ == "King")
    board.set_piece_at(coordinates(square), king(WHITE))
    return board


def _build(kind: str, colour: int) -> Any:
    """Build a piece of a kind and colour.

    Args:
        kind: `man` or `king`.
        colour: WHITE or BLACK.

    Returns:
        Any: The piece.
    """
    from games.checkers.pieces.king import King
    from games.checkers.pieces.man import Man

    return Man(colour) if kind == "man" else King(colour)


def test_a_kings_only_end_is_not_a_draw_because_no_rule_says_it_is():
    """Two kings against one is winnable, so no rule may call it a draw.

    WCDF article 1.32 lists three draws and this is not one of them. The configuration used to
    carry a fourth rule — neither side has a man left — which ended exactly this endgame while
    it was still playable. It has been removed, and this is what says so.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    board = board_with({22: "wk", 11: "bk"})

    labels = [rule.default_name for rule in build_rules()]
    assert (
        "Insufficient material" not in labels
    ), "a rule the rulebook does not have is deciding a kings-only endgame"
    assert rules_of(build_rules(), "Threefold repetition").outcome(board) is None
    assert rules_of(build_rules(), "Fifty-move rule").outcome(board) is None


def test_the_same_position_a_third_time_is_a_draw():
    """Rulebook rule 1.32.1: the same position for the third time.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    rule = rules_of(build_rules(), "Threefold repetition")
    rule.attach()
    board = board_with({22: "wk", 11: "bk"})
    rule.active_color = 1

    assert rule.record(board, 1) == 1
    assert rule.record(board, 1) == 1, "asking must not create the repetition"
    assert rule.outcome(board) is None

    seen = rule.state["seen"]
    key = next(iter(seen))
    seen[key] = 2
    assert rule.record(board, 1) == 2
    assert rule.outcome(board) is None

    seen[key] = 3
    assert rule.outcome(board).kind == KIND_DRAW
    assert rule.outcome(board).reason == "threefold repetition"


def test_a_position_the_other_side_is_to_move_in_is_not_the_same_position():
    """Whose turn it is is part of what makes a position a position.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    rule = rules_of(build_rules(), "Threefold repetition")
    rule.attach()
    board = board_with({22: "wk", 11: "bk"})

    assert rule.record(board, 1) == 1
    assert rule.record(board, -1) == 1


def test_the_forty_move_count_is_the_rulebooks_forty_moves_each():
    """Rulebook rule 1.32.2 draws after forty moves by *each* side, which is eighty plies.

    The count shipped as a hundred, which is fifty moves each — the international game's figure,
    in a configuration that claims to be English.

    Returns:
        None
    """
    from games.checkers.rules import build_rules

    rule = rules_of(build_rules(), "Fifty-move rule")
    rule.attach()

    assert rule.value["plies"] == 80
    rule.state["plies"] = 79
    assert rule.outcome(None) is None
    rule.state["plies"] = 80
    assert rule.outcome(None).kind == KIND_DRAW
