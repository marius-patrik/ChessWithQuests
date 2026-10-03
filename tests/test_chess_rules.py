"""The chess rules, exercised as rules.

Every case here sets up a position and asks a rule a question. Nothing reaches into a rule's
internals, because the point of the rule layer is that a rule is asked rather than inspected.
"""

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
from games.chess.rules import build_rules
from games.chess.rules.attacks import has_legal_move
from games.chess.rules.check import in_check
from games.chess.rules.castling import CASTLE_KING_SIDE, CASTLE_QUEEN_SIDE, CastlingRule
from games.chess.rules.en_passant import EnPassantRule
from games.chess.rules.draws import (
    FiftyMoveRule,
    InsufficientMaterialRule,
    MutualAgreementRule,
    ThreefoldRepetitionRule,
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
    board.set_piece_at((7, 4), King(-1))
    return board


def test_chess_declares_thirteen_rules_in_a_fixed_order():
    """The set of rules in force is closed, ordered, and written out by hand."""
    rules = build_rules()
    assert [rule.default_name for rule in rules] == [
        "Royal piece",
        "Castling",
        "En passant",
        "Promotion",
        "Bishop colour",
        "Check",
        "Checkmate",
        "Stalemate",
        "Insufficient material",
        "Fifty-move rule",
        "Threefold repetition",
        "Draw by agreement",
        "Flag fall",
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
    """A blocked square means no castle, even though nothing is attacking."""
    board = castling_ready_board()
    board.set_piece_at((0, 5), Bishop(-1))
    rule = CastlingRule()

    assert CASTLE_KING_SIDE not in [
        m.move_type for m in rule.available_moves(board, board.get_piece_at((0, 4)))
    ]


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
