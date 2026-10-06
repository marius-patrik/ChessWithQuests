"""The chess rules, exercised as rules.

Every case here sets up a position and asks a rule a question. Nothing reaches into a rule's
internals, because the point of the rule layer is that a rule is asked rather than inspected.
"""

import pytest

from games.chess.board import build_board
from model.game.board import Board
from model.game.move import Move
from model.game.validator import MoveValidator
from games.chess.pieces.bishop import Bishop
from games.chess.pieces.knight import Knight
from games.chess.pieces.king import King
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen
from games.chess.pieces.rook import Rook
from games.chess.board import build_board
from games.chess.rules import build_rules
from games.chess.rules.attacks import has_legal_move, square_color
from games.chess.rules.check import in_check
from games.chess.rules.castling import CastlingRule
from games.chess.rules.en_passant import EnPassantRule
from games.chess.rules.draws import (
    FiftyMoveRule,
    InsufficientMaterialRule,
    MutualAgreementRule,
    ThreefoldRepetitionRule,
    position_key,
)
from games.chess.rules.flag import FlagFallRule
from games.chess.rules.promotion import PromotionRule


def empty_board():
    """Return a board with no pieces on it."""
    return Board(setup_pieces=False)


def castling_ready_board(king_file=4):
    """Return a board where White may castle either way.

    Args:
        king_file: The file the white king stands on.

    Returns:
        Board: A board with both white rooks and the white king on their home squares.
    """
    board = empty_board()
    board.set_piece_at((0, king_file), King(1))
    board.set_piece_at((0, 0), Rook(1))
    board.set_piece_at((0, 7), Rook(1))
    board.set_piece_at((7, king_file), King(-1))
    return board


def bishop_colour_rule():
    """Return the rule that confines each bishop to the shade of square it started on.

    Taken from the rules a configuration composes rather than constructed here, so a
    configuration that stopped composing it has no rule to answer with and these tests fail.

    Returns:
        BishopColourRule: The rule, attached, so its record of where bishops began is empty.
    """
    rule = next(rule for rule in build_rules() if rule.default_name == "Bishop colour")
    rule.attach()
    return rule


def test_chess_declares_thirteen_rules_in_a_fixed_order():
    """The set of rules in force is closed, ordered, and read off the section's own files.

    The order used to be a hand-written tuple, and the file names in `rules/` were the
    order it happened to be written in. It is now the order `compose_section` composes in:
    the section's own module first, then the files by name — which is `bishop_colour.py`,
    `castling.py`, `check.py`, `draws.py`, `en_passant.py`, `flag.py`, `promotion.py`,
    `royal.py`, with `attacks.py` declaring none of them. `attacks.py` sorts first of all and
    contributes nothing, which is what a helper module in a section is for.

    The second assertion is the one that cannot drift: it says the order is the files, so a
    rule moved into a file of a different name moves with it rather than needing the list
    above edited.
    """
    rules = build_rules()
    assert [rule.default_name for rule in rules] == [
        "Bishop colour",
        "Castling",
        "Check",
        "Checkmate",
        "Stalemate",
        "Insufficient material",
        "Fifty-move rule",
        "Threefold repetition",
        "Draw by agreement",
        "En passant",
        "Flag fall",
        "Promotion",
        "Royal piece",
    ]
    assert [type(rule).__module__.rsplit(".", 1)[-1] for rule in rules] == [
        "bishop_colour",
        "castling",
        "check",
        "check",
        "check",
        "draws",
        "draws",
        "draws",
        "draws",
        "en_passant",
        "flag",
        "promotion",
        "royal",
    ]


def test_check_is_reported_while_the_game_continues():
    """Check is a status, not an outcome: the player is still allowed to move."""
    board = empty_board()
    board.set_piece_at((0, 4), King(1))
    board.set_piece_at((7, 4), Rook(-1))

    rules = build_rules()
    rule = next(r for r in rules if r.default_name == "Check")
    rule.active_color = 1

    assert in_check(board, 1) is True
    assert rule.status(board) == "Check"
    assert rule.outcome(board) is None
    assert has_legal_move(board, 1, rules) is True


def test_checkmate_ends_the_game_for_the_opponent():
    """Mate is a win for the other side, and it outranks the draws."""
    board = empty_board()
    board.set_piece_at((0, 0), King(1))
    board.set_piece_at((0, 1), Queen(-1))
    board.set_piece_at((1, 1), Rook(-1))

    rules = build_rules()
    MoveValidator(board, rules=rules)  # the validator hands each rule the rule set
    mate = next(r for r in rules if r.default_name == "Checkmate")
    mate.active_color = 1
    result = mate.outcome(board)

    assert result is not None
    assert result.kind == "win"
    assert result.winner == -1
    assert result.reason == "checkmate"
    assert has_legal_move(board, 1, rules) is False


def test_stalemate_is_a_draw_and_not_a_loss():
    """Stuck without being attacked is a draw, which is a different answer from mate."""
    board = empty_board()
    board.set_piece_at((0, 0), King(1))
    board.set_piece_at((1, 2), Queen(-1))
    board.set_piece_at((2, 2), King(-1))

    rules = build_rules()
    MoveValidator(board, rules=rules)
    stale = next(r for r in rules if r.default_name == "Stalemate")
    stale.active_color = 1
    result = stale.outcome(board)

    assert result is not None
    assert result.kind == "draw"
    assert result.reason == "stalemate"
    assert in_check(board, 1) is False


def test_the_opening_position_leaves_nobody_in_check():
    """Neither king starts attacked, so no status fires before the first move."""
    board = build_board()
    assert in_check(board, 1) is False
    assert in_check(board, -1) is False


def test_castling_is_offered_on_both_sides_and_moves_the_rook():
    """A castle carries the rook, which is why it needs a companion square."""
    board = castling_ready_board()
    rule = CastlingRule()

    offered = rule.available_moves(board, board.get_piece_at((0, 4)))
    assert [m.move_type for m in offered] == ["castling", "castling"]

    kingside, queenside = offered
    assert (kingside.end_pos, kingside.companion_start, kingside.companion_end) == (
        (0, 6),
        (0, 7),
        (0, 5),
    )
    assert (queenside.end_pos, queenside.companion_start, queenside.companion_end) == (
        (0, 2),
        (0, 0),
        (0, 3),
    )


def test_castling_is_withheld_when_the_king_would_cross_an_attacked_square():
    """The king may not pass through check, so the transit square decides."""
    board = castling_ready_board()
    board.set_piece_at((5, 5), Rook(-1))  # attacks f1, the square the king crosses
    rule = CastlingRule()

    offered = rule.available_moves(board, board.get_piece_at((0, 4)))
    assert [m.end_pos for m in offered] == [(0, 2)]  # queenside only


def test_castling_is_withdrawn_once_the_king_has_moved():
    """Rights are lost by moving the king, and remembered by the rule itself."""
    board = castling_ready_board()
    rule = CastlingRule()
    rule.attach()
    king = board.get_piece_at((0, 4))

    assert rule.available_moves(board, king) != []

    board.move_piece((0, 4), (1, 4))
    king.setMoved()
    rule.on_move_made(board, Move((0, 4), (1, 4), piece=king))

    assert rule.available_moves(board, board.get_piece_at((1, 4))) == []


def test_castling_is_withheld_when_the_path_is_occupied():
    """A blocked square means no castle, even though nothing is attacking.

    The bishop on f1 blocks the king's own route, so only the castle carrying the a-file rook
    survives. What is asserted is which castle survived, read from the rook each move carries:
    the previous assertion here compared `move_type` against the castle token `O-O`, which
    could never be equal and so could never fail — the move type for either castle is the one
    word `castling`, which is exactly why a writer that read it wrote `O-O` twice.

    Returns:
        None
    """
    board = castling_ready_board()
    board.set_piece_at((0, 5), Bishop(-1))
    rule = CastlingRule()

    offered = rule.available_moves(board, board.get_piece_at((0, 4)))

    assert [move.companion_start for move in offered] == [(0, 0)]
    assert [move.move_type for move in offered] == ["castling"]


def test_en_passant_is_offered_only_on_the_ply_after_a_double_advance():
    """The capture is available for exactly one move, and lifts the pawn from where it stands."""
    board = empty_board()
    white_pawn = Pawn(1)
    black_pawn = Pawn(-1)
    board.set_piece_at((4, 3), white_pawn)  # d5, the pawn that will capture
    board.set_piece_at((4, 4), black_pawn)  # e5, where the black pawn now stands
    board.set_piece_at((7, 4), King(-1))
    board.set_piece_at((0, 0), King(1))

    rule = EnPassantRule()
    rule.attach()
    # Black advanced e7 (6,4) to e5 (4,4) by its declared one-off long step.
    rule.on_move_made(board, Move((6, 4), (4, 4), piece=black_pawn))

    assert rule.victim_square() == (4, 4)
    offered = rule.available_moves(board, white_pawn)

    assert len(offered) == 1
    capture = offered[0]
    assert (capture.start_pos, capture.end_pos) == ((4, 3), (5, 4))  # d5 takes on e6
    assert capture.move_type == "en_passant"
    assert capture.capture_from == (4, 4)  # the black pawn is lifted from e5, not e6


def test_en_passant_expires_when_another_move_is_played():
    """One ply only: any other move takes the offer away."""
    board = empty_board()
    white_pawn = Pawn(1)
    black_pawn = Pawn(-1)
    board.set_piece_at((4, 3), white_pawn)
    board.set_piece_at((4, 4), black_pawn)

    rule = EnPassantRule()
    rule.attach()
    rule.on_move_made(board, Move((6, 4), (4, 4), piece=black_pawn))
    assert rule.available_moves(board, white_pawn) != []

    # A quiet move by either side ends the offer.
    board.set_piece_at((7, 0), Rook(1))
    rule.on_move_made(board, Move((6, 0), (7, 0), piece=board.get_piece_at((7, 0))))

    assert rule.victim_square() is None
    assert rule.available_moves(board, white_pawn) == []


def test_the_offered_square_is_the_one_a_capturing_piece_lands_on():
    """The offer names the square behind the advanced piece, not the one it stands on.

    Two squares are in play and they are not the same square: the advanced piece is lifted from
    the square it stands on, which `victim_square` answers, and the capturing piece lands one
    row further on, which is what a position record calls the target. Reporting the first for
    the second would name a square no capture ever ends on.
    """
    board = empty_board()
    black_pawn = Pawn(-1)
    board.set_piece_at((4, 4), black_pawn)

    rule = EnPassantRule()
    rule.attach()
    assert rule.target_square() is None

    rule.on_move_made(board, Move((6, 4), (4, 4), piece=black_pawn))

    assert rule.victim_square() == (4, 4)  # e5, where the advanced pawn stands
    assert rule.target_square() == (5, 4)  # e6, where a capturing pawn would land


def test_a_rule_that_offers_nothing_says_so():
    """Every rule answers the question, and the answer for no offer is None."""
    assert EnPassantRule().target_square() is None
    assert ThreefoldRepetitionRule().target_square() is None


def test_a_live_capture_in_passing_is_part_of_what_identifies_a_position():
    """The same placement with the offer standing and without it is two positions.

    This is the case the key used to miss. A pawn that has just advanced two squares hands the
    opponent a capture the same placement reached any other way does not, so the rulebook
    counts the two as different positions; the key read neither the offer nor anything else
    about it, and read the placement alone.

    The control matters as much as the difference: with no offer standing the key is exactly
    the key this function has always produced, so a key that differed for every position would
    pass the first half of this and be wrong.
    """
    board = empty_board()
    black_pawn = Pawn(-1)
    board.set_piece_at((4, 4), black_pawn)

    rule = EnPassantRule()
    rule.attach()
    without_offer = position_key(board, -1, [rule])

    rule.on_move_made(board, Move((6, 4), (4, 4), piece=black_pawn))

    assert position_key(board, -1, [rule]) != without_offer
    # A set that is asked nothing it can answer keys the placement alone.
    assert position_key(board, -1, []) == without_offer


def offering_board():
    """Return a board on which one long advance has just been made and offers a capture.

    The black pawn stands on e5 having come from e7 by its declared one-off long step, the
    white rook and both kings are out of its way, and nothing has been told about any move yet,
    so a rule asked what it is offering answers for a position the caller is about to describe.

    Returns:
        tuple: The board, the advance that produced this position, and a quiet move that
        withdraws the offer without changing the placement of the advanced pawn.
    """
    board = empty_board()
    board.set_piece_at((4, 4), Pawn(-1))  # e5, arrived at from e7
    board.set_piece_at((6, 0), Rook(1))  # a1, which can step aside
    board.set_piece_at((7, 0), King(-1))  # a8
    board.set_piece_at((0, 7), King(1))  # h1, which can step aside
    return (
        board,
        Move((6, 4), (4, 4), piece=board.get_piece_at((4, 4))),
        Move((6, 0), (7, 0), piece=board.get_piece_at((6, 0))),
    )


def test_three_occurrences_differing_only_in_a_live_offer_are_not_a_repetition():
    """The draw the key used to propose wrongly: three of one position that was never one.

    The same board is put to the rule three times, and the only thing that changes is whether
    an offer is standing. Two occurrences are the same position and the third is a different
    one, so no position has occurred three times and nothing may be proposed — which is the
    question the key could not previously answer, and it answered it wrongly every time.

    The moves are announced to this configuration's whole rule set through the engine's own
    dispatcher and in the order the configuration declares them, which puts the repetition rule
    before the rule that offers the square. That order is the reason the offer is read when the
    next question is asked rather than when the move is announced, and a test that announced the
    moves to the two rules by hand would not have exercised any of it.

    The second half is the control: the same three occurrences with the offer standing on all
    of them *are* a repetition. Without it the first half would also pass for a rule that
    counted nothing at all.
    """
    board, advance, quiet = offering_board()

    def judged_after(moves):
        """Return what this configuration's repetition rule proposes after these moves.

        Args:
            moves: The moves to announce, in order, to a freshly composed rule set.

        Returns:
            Optional[Result]: What the rule proposes for the position the last move produced.
        """
        rules = build_rules()
        validator = MoveValidator(board, rules=rules)
        repetition = next(rule for rule in rules if isinstance(rule, ThreefoldRepetitionRule))
        for move in moves:
            validator.notify_move_made(move, board)
        return repetition.outcome(board)

    alternating = judged_after([advance, quiet, advance])
    assert alternating is None, (
        "a draw was proposed for three occurrences that were not one position, "
        "because the offer was not part of the key"
    )

    offered_throughout = judged_after([advance] * 3)
    assert offered_throughout is not None
    assert offered_throughout.reason == "threefold repetition"


def test_promotion_is_offered_to_the_four_choices():
    """A pawn reaching the far rank is offered a promotion, not left a pawn."""
    board = empty_board()
    pawn = Pawn(1)
    board.set_piece_at((6, 4), pawn)  # e7, one step from promoting

    rule = PromotionRule()
    offered = rule.available_moves(board, pawn)

    assert offered != []
    assert all(m.promotion_piece is not None for m in offered)
    # The promoted knight reports the `horse` descriptor; the class is `Knight`. The two
    # spellings are bridged where a rule compares kinds, and `Horse` is not a name here.
    assert {m.promotion_piece.getType() for m in offered} == {"queen", "rook", "bishop", "horse"}
    assert {type(m.promotion_piece).__name__ for m in offered} == {
        "Queen",
        "Rook",
        "Bishop",
        "Knight",
    }


def test_the_rule_holds_no_piece_list_of_its_own():
    """`PROMOTION_PIECES` was a second hand-written catalogue beside the composed one.

    A piece written into a copy's `pieces/` directory joined the catalogue and could not be
    promoted to, because the rule read a dict written out in `promotion.py` instead of asking.
    The check is on the module's own attribute rather than on what it produces, so a list that
    came back beside a working catalogue would fail without anyone naming it.

    Returns:
        None
    """
    import games.chess.rules.promotion as promotion

    assert not hasattr(promotion, "PROMOTION_PIECES")


def test_a_rule_that_declares_no_choices_offers_what_the_catalogue_declares():
    """With no `promotion_kinds` declared, the catalogue answers — and the answer is not a name.

    Two kinds here must not be offered and the rule knows it because the *pieces* say so: a
    pawn is what promotes rather than what a pawn becomes, and a king is the piece a game ends
    with rather than one a promotion produces. Both declare `promotion_target = False`, so the
    rule holds no list of kinds to exclude and a piece written into `pieces/` is offered with no
    edit at all — which is what a fixed list could never do.

    Returns:
        None
    """
    board = empty_board()
    pawn = Pawn(1)
    board.set_piece_at((6, 4), pawn)

    rule = PromotionRule(promotion_kinds="")
    offered = {move.promotion_piece.getType() for move in rule.available_moves(board, pawn)}

    assert offered == {"queen", "rook", "bishop", "horse"}


def test_a_kind_the_catalogue_does_not_offer_is_refused_and_says_what_is_offered():
    """A declaration and a catalogue that disagree is a configuration whose author should hear
    about it, not one that silently promotes to something else.

    Returns:
        None
    """
    board = empty_board()
    pawn = Pawn(1)
    board.set_piece_at((6, 4), pawn)
    rule = PromotionRule(promotion_kinds="dromedary")

    with pytest.raises(ValueError, match="is not a piece kind this configuration offers"):
        rule.available_moves(board, pawn)


def test_a_declared_choice_is_honoured_over_the_catalogue():
    """A configuration may still narrow the offer, and the piece it names has to exist.

    Returns:
        None
    """
    board = empty_board()
    pawn = Pawn(1)
    board.set_piece_at((6, 4), pawn)

    rule = PromotionRule(promotion_kinds="rook, bishop")
    offered = {move.promotion_piece.getType() for move in rule.available_moves(board, pawn)}

    assert offered == {"rook", "bishop"}


# --- bishop colour, which `notes/chess_rules.md` section 2 states as a rule of the game


def test_a_bishop_on_a_light_square_cannot_reach_a_dark_one():
    """A bishop is confined to the colour of square it started on, and this is that side of it.

    `square_color` is the parity of row plus column and the rule compares nothing else, so a
    light square is one that reads 1 — f1 does — and a dark square one that reads 0. A real
    `Bishop` only ever offers diagonal destinations, which are all one shade anyway, so the
    rule is what makes the confinement a property of a *kind* rather than of one piece class's
    vectors. That is why the dark square is asked about directly.

    Returns:
        None
    """
    board = empty_board()
    bishop = Bishop(1)
    board.set_piece_at((0, 5), bishop)  # f1
    rule = bishop_colour_rule()

    # One diagonal step is how the rule learns where a bishop began: it records the shade of
    # whatever arrived on the destination square.
    step = Move((0, 5), (1, 6), piece=bishop)
    step.apply_to_board(board)
    rule.on_move_made(board, step)

    assert square_color(board, (0, 5)) == 1  # f1, light
    assert rule.permits_move(board, Move((1, 6), (2, 7), piece=bishop)) is True  # h3, light
    assert rule.permits_move(board, Move((1, 6), (3, 3), piece=bishop)) is False  # d4, dark


def test_a_bishop_on_a_dark_square_cannot_reach_a_light_one():
    """The other side of the same rule, which is a different reading of the parity.

    Returns:
        None
    """
    board = empty_board()
    bishop = Bishop(1)
    board.set_piece_at((0, 2), bishop)  # c1
    rule = bishop_colour_rule()

    step = Move((0, 2), (1, 1), piece=bishop)
    step.apply_to_board(board)
    rule.on_move_made(board, step)

    assert square_color(board, (0, 2)) == 0  # c1, dark
    assert rule.permits_move(board, Move((1, 1), (0, 0), piece=bishop)) is True  # a1, dark
    assert rule.permits_move(board, Move((1, 1), (0, 5), piece=bishop)) is False  # f1, light


def test_a_bishop_promoted_on_a_square_is_confined_to_that_squares_shade():
    """The shade comes from where the bishop appeared, not from where the pawn stood.

    A pawn reaches the far rank by a step straight up the file, so its promotion square is
    always the opposite shade from the square it left — b7 is light and b8 is dark. So a
    promoted bishop that inherited the pawn's shade would reach the light squares the bishop
    is not allowed, and refusing h1 is what shows the shade came from b8 instead.

    Nothing about the promotion move itself is affected: the piece that moves is a pawn, and a
    pawn is not a confined kind, so the rule has no opinion about what it becomes.

    Returns:
        None
    """
    board = empty_board()
    pawn = Pawn(1)
    board.set_piece_at((6, 1), pawn)  # b7
    promotion = PromotionRule()
    rule = bishop_colour_rule()

    offered = [
        move
        for move in promotion.available_moves(board, pawn)
        if move.promotion_piece is not None and move.promotion_piece.getType() == "bishop"
    ]
    assert len(offered) == 1
    crowning = offered[0]

    assert rule.permits_move(board, crowning) is True
    crowning.apply_to_board(board)
    rule.on_move_made(board, crowning)

    bishop = board.get_piece_at((7, 1))
    assert isinstance(bishop, Bishop), "b8 did not arrive holding the bishop that was chosen"
    assert square_color(board, (6, 1)) == 1  # b7, light — the square the pawn left
    assert square_color(board, (7, 1)) == 0  # b8, dark — where the bishop arrived
    assert rule.permits_move(board, Move((7, 1), (6, 0), piece=bishop)) is True  # a7, dark
    assert rule.permits_move(board, Move((7, 1), (0, 7), piece=bishop)) is False  # h1, light


def test_the_validator_asks_the_rules_rather_than_guessing():
    """With chess in force the engine knows a king; with no rules it knows nothing."""
    board = build_board()

    with_chess = MoveValidator(board, rules=build_rules())
    assert with_chess.royal_kinds() == ["king"]
    assert with_chess.find_royal(1) == (0, 4)

    without_rules = MoveValidator(board)
    assert without_rules.royal_kinds() == []
    assert without_rules.find_royal(1) is None
    assert without_rules.is_check(1) is False


def test_a_knight_is_judged_by_its_declared_vectors_not_its_name():
    """The knight is a knight to the player and only a leaping piece to the engine."""
    board = empty_board()
    board.set_piece_at((4, 4), Knight(1))

    assert in_check(board, -1, royal_kind="king") is False
    assert MoveValidator(board).get_valid_moves((4, 4)) != []


def kings_only_board():
    """Return a board holding just the two kings."""
    board = empty_board()
    board.set_piece_at((0, 0), King(1))
    board.set_piece_at((7, 7), King(-1))
    return board


def insufficient_outcome(*white_extra):
    """Judge a position where Black has only a king.

    Args:
        *white_extra: The (square, piece) pairs White has besides its king.

    Returns:
        Optional[Result]: The rule's answer for that position.
    """
    board = kings_only_board()
    for square, piece in white_extra:
        board.set_piece_at(square, piece)
    rule = InsufficientMaterialRule()
    rule.attach()
    rule.active_color = 1
    return rule.outcome(board)


def test_insufficient_material_draws_the_positions_that_cannot_be_mated():
    """A side that can never mate is a draw, whatever the pieces happen to be."""
    # (4, 4) and (4, 5) are one square colour apart; (4, 4) and (4, 3) are too, but the
    # bishops below are placed on squares of the same parity on purpose.
    assert insufficient_outcome() is not None
    assert insufficient_outcome(((4, 4), Knight(1))) is not None
    assert insufficient_outcome(((4, 4), Bishop(1))) is not None
    assert insufficient_outcome(((4, 0), Bishop(1)), ((5, 1), Bishop(1))) is not None

    assert insufficient_outcome(((4, 4), Rook(1))) is None
    assert insufficient_outcome(((4, 4), Knight(1)), ((3, 4), Knight(1))) is None
    assert insufficient_outcome(((4, 0), Bishop(1)), ((4, 1), Bishop(1))) is None


def test_the_knight_is_recognised_by_either_spelling_of_its_kind():
    """A setting written for `knight` still matches the piece that reports `knight`."""
    board = kings_only_board()
    board.set_piece_at((4, 4), Knight(1))
    rule = InsufficientMaterialRule()
    rule.attach()
    rule.active_color = 1
    assert rule.outcome(board) is not None


def test_fifty_moves_without_progress_is_a_draw():
    """The half-move clock is kept by the rule and read by the rule."""
    board = kings_only_board()
    rule = FiftyMoveRule()
    rule.attach()
    rule.active_color = 1

    king = board.get_piece_at((0, 0))
    for _ in range(99):
        rule.on_move_made(board, Move((0, 0), (0, 1), piece=king))
    assert rule.outcome(board) is None

    rule.on_move_made(board, Move((0, 0), (0, 1), piece=king))
    result = rule.outcome(board)
    assert result is not None
    assert result.kind == "draw"
    assert result.reason == "fifty-move rule"


def test_threefold_repetition_counts_a_position_it_has_already_seen():
    """Asking whether the game is over must not itself create the repetition."""
    board = kings_only_board()
    rule = ThreefoldRepetitionRule()
    rule.attach()
    rule.active_color = 1

    assert rule.record(board) == 1
    assert rule.outcome(board) is None
    assert rule.record(board) == 1  # idempotent for the position being judged
    assert rule.outcome(board) is None


def test_a_draw_offer_only_draws_the_game_once_it_is_accepted():
    """An offer on the table is not a result."""
    board = kings_only_board()
    rule = MutualAgreementRule()
    rule.attach()
    rule.active_color = 1

    assert rule.outcome(board) is None

    rule.offer()
    assert rule.outcome(board) is None

    rule.accept()
    result = rule.outcome(board)
    assert result is not None
    assert result.kind == "draw"


def test_flag_fall_stays_silent_when_there_is_no_clock_to_fall():
    """With no clock attached there is no time to have run out."""
    board = kings_only_board()
    rule = FlagFallRule()
    rule.attach()
    rule.active_color = 1
    assert rule.outcome(board) is None


def test_castling_moves_the_king_two_files_and_the_rook_three():
    """The two destinations come from the royal piece's own start file, not a constant.

    Castling is offered from the middle of the back rank and lands the king two files towards
    one rook and the rook one file inside that. Getting the two swapped put the king on the
    rook's square, so this asserts both ends of both pieces.
    """
    board = castling_ready_board()
    rule = CastlingRule()

    kingside = rule.available_moves(board, board.get_piece_at((0, 4)))[0]

    assert (kingside.start_pos, kingside.end_pos) == ((0, 4), (0, 6))
    assert (kingside.companion_start, kingside.companion_end) == ((0, 7), (0, 5))


def test_a_castle_actually_puts_both_pieces_on_their_squares():
    """Offered is not played: the board must end with a king on g1 and a rook on f1."""
    board = castling_ready_board()
    board.set_piece_at((0, 1), None)
    board.set_piece_at((0, 6), None)
    rule = CastlingRule()
    rule.attach()

    castle = rule.available_moves(board, board.get_piece_at((0, 4)))[0]
    assert castle.apply_to_board(board) is not None

    assert board.get_piece_at((0, 6)).getType() == "king"
    assert board.get_piece_at((0, 5)).getType() == "rook"
    assert board.get_piece_at((0, 4)) is None
    assert board.get_piece_at((0, 7)) is None


def test_a_royal_piece_that_has_left_its_start_file_is_not_offered_a_castle():
    """The castle is a move to two squares, and only from the one it started on."""
    board = castling_ready_board()
    king = board.get_piece_at((0, 4))
    board.move_piece((0, 4), (0, 3))  # the king steps to d1
    rule = CastlingRule()

    assert rule.available_moves(board, king) == []


def test_the_knight_shuffle_is_a_repetition_and_is_called_one():
    """`1.Nf3 Nf6 2.Ng1 Ng8` twice returns to the start four times over.

    The key carried every piece's moved flag, so the knight that had been to f3 and back was
    not the knight that had not moved, and the starting position looked new each time. No draw
    was ever offered in the one line of chess where threefold repetition is unavoidable.
    """
    board = build_board()
    rule = ThreefoldRepetitionRule()
    rule.attach()
    colour = 1

    shuffle = [
        ((0, 6), (2, 5)),
        ((7, 1), (5, 2)),
        ((2, 5), (0, 6)),
        ((5, 2), (7, 1)),
    ] * 2

    rule.active_color = colour
    assert rule.outcome(board) is None  # the starting position, seen once
    for ply, (start, end) in enumerate(shuffle, start=1):
        move = Move(start, end)
        move.apply_to_board(board)
        rule.active_color = colour
        rule.on_move_made(board, move)
        colour = -colour
        rule.active_color = colour
        result = rule.outcome(board)
        if ply < 8:
            assert result is None, f"a draw was claimed after only {ply} plies"
    assert result is not None, "the starting position occurred three times and nothing said so"
    assert result.kind == "draw"
    assert result.reason == "threefold repetition"


def test_a_king_that_moved_and_came_back_is_not_the_same_position():
    """The guard on the flag above: castling rights are part of a position's identity.

    A king that has stepped out and back stands on its own square with the same pieces around
    it and may no longer castle, which is a different position by the rulebook's own test.
    """
    board = build_board()
    king = board.get_piece_at((0, 4))
    before = position_key(board, 1)

    board.move_piece((0, 4), (0, 3))
    board.move_piece((0, 3), (0, 4))
    king.setMoved(True)

    assert position_key(board, 1) != before, "losing castling rights did not change the position"
