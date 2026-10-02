from games.chess.board import build_board, starting_placement
import pytest

from model.game.board import Board
from model.game.move import Move
from model.game.validator import MoveValidator
from model.misc.export_writers import ChessNotationWriter
from games.chess.pieces.king import King
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen
from games.chess.pieces.rook import Rook

SIZES = [(8, 8), (10, 10), (5, 7)]


def test_board_of_any_size_can_be_constructed_and_populated():
    """The board is a rectangle. Nothing outside `Board` may assume it is a square, and
    nothing may assume it is eight by eight either."""
    for rows, cols in SIZES:
        board = Board((rows, cols), setup_pieces=False)

        assert (board.rows, board.cols) == (rows, cols)
        assert len(board.board) == rows
        assert all(len(rank) == cols for rank in board.board)

        board.set_piece_at((0, 0), Rook(1))
        board.set_piece_at((rows - 1, cols - 1), Rook(-1))

        assert board.get_piece_at((0, 0)).getColor() == 1
        assert board.get_piece_at((rows - 1, cols - 1)).getColor() == -1


def test_a_board_carries_no_starting_position_of_its_own():
    """A starting position is a fact about a game, so the configuration supplies one."""
    assert build_board().dimensions == Board.DEFAULT_DIMENSIONS

    # The engine's board starts empty rather than guessing a game's pieces.
    assert Board((10, 10)).get_piece_at((0, 0)) is None

    # Asking for the old behaviour says why it cannot be served, instead of quietly
    # handing back an empty board that reads like a starting position.
    with pytest.raises(ValueError, match="placement"):
        Board((10, 10), setup_pieces=True)


def test_the_chess_configuration_is_the_only_thing_that_knows_the_starting_position():
    """Deleting a piece file changes chess without the engine noticing or caring."""
    board = build_board()

    files = {position[1] for position, _ in starting_placement()}
    assert sorted(files) == list(range(board.cols))
    rows = {position[0] for position, _ in starting_placement()}
    assert sorted(rows) == [0, 1, board.rows - 2, board.rows - 1]

    # The placement is 32 pieces: two back ranks and two ranks of pawns.
    assert len(starting_placement()) == 32


def test_a_board_too_small_for_chess_says_so():
    """A narrow board is legal and playable; it simply has no chess starting position."""
    with pytest.raises(ValueError, match="files wide"):
        starting_placement(8, 7)
    with pytest.raises(ValueError, match="ranks"):
        starting_placement(3, 8)


def test_an_explicit_placement_populates_a_board_of_any_size():
    rows, cols = 10, 10
    board = Board((rows, cols), placement=[((9, 0), Rook(1)), ((0, 0), Rook(-1))])

    assert board.get_piece_at((9, 0)).getName() == "Rook"
    assert board.get_piece_at((0, 0)).getColor() == -1


def test_apply_placement_clears_what_was_there():
    board = build_board()
    board.apply_placement([((4, 4), Queen(1))])

    assert board.get_piece_at((0, 0)) is None
    assert board.get_piece_at((4, 4)).getName() == "Queen"

    board.apply_placement([])
    assert board.get_piece_at((4, 4)) is None


def test_the_starting_position_is_built_from_the_board_not_from_a_literal():
    """A back rank and a rank of pawns, placed against the board's own size."""
    board = build_board()

    assert len(board.board) == board.rows
    # Every square of the back rank and the pawn rank carries exactly one piece.
    for row in (0, 1, board.rows - 2, board.rows - 1):
        occupied = [board.get_piece_at((row, col)) for col in range(board.cols)]
        assert all(piece is not None for piece in occupied), f"rank {row} is not full"

    # White's and Black's back ranks differ only in colour.
    white_back = [board.get_piece_at((0, col)).getColor() for col in range(board.cols)]
    black_back = [board.get_piece_at((board.rows - 1, col)).getColor() for col in range(board.cols)]
    assert white_back == [1] * board.cols
    assert black_back == [-1] * board.cols


@pytest.mark.parametrize("rows,cols", SIZES)
def test_a_move_is_validated_against_the_board_it_is_played_on(rows, cols):
    board = Board((rows, cols), setup_pieces=False)
    board.set_piece_at((0, 0), Rook(1))

    assert Move((0, 0), (0, cols - 1)).validate(board) is True
    assert Move((0, 0), (rows - 1, cols - 1)).validate(board) is True
    assert Move((0, 0), (0, cols)).validate(board) is False
    assert Move((0, 0), (rows, 0)).validate(board) is False


def test_a_move_without_a_board_uses_the_default_size():
    """No board means the size nothing else declared, which is `Board`'s own default."""
    board = build_board()

    assert Move((0, 0), (board.rows - 1, board.cols - 1)).validate() is True
    assert Move((0, 0), (board.rows, 0)).validate() is False


@pytest.mark.parametrize("rows,cols", SIZES)
def test_a_sliding_piece_reaches_across_the_whole_board(rows, cols):
    board = Board((rows, cols), setup_pieces=False)
    board.set_piece_at((0, 0), Rook(1))

    destinations = MoveValidator(board).get_pseudo_legal_moves((0, 0))

    assert (0, cols - 1) in destinations
    assert (rows - 1, 0) in destinations
    assert (rows, 0) not in destinations


@pytest.mark.parametrize("rows,cols", SIZES)
def test_a_move_a_capture_and_a_promotion_on_every_size(rows, cols):
    """One test, three board sizes: a move, a capture and a promotion each go through the
    same code the real game uses, so a size that only works for quiet moves cannot pass."""
    board = Board((rows, cols), setup_pieces=False)

    # A move.
    board.set_piece_at((0, 0), Rook(1))
    assert Move((0, 0), (0, 1)).execute(board) is True
    assert board.get_piece_at((0, 1)).getName() == "Rook"
    assert board.get_piece_at((0, 0)) is None

    # A capture.
    board.set_piece_at((1, 1), Pawn(-1))
    capture = Move((0, 1), (1, 1), move_type="capture")
    assert capture.execute(board) is True
    assert capture.captured_piece is not None
    assert board.get_piece_at((1, 1)).getColor() == 1
    assert [piece.getColor() for piece in board.captured_black] == [-1]

    # A promotion, on the far rank of whatever size this board is.
    far_row = rows - 1
    board.set_piece_at((far_row, 2), Pawn(1))
    promotion = Move((far_row, 2), (far_row - 1, 2), promotion_piece=Queen(1))
    assert promotion.execute(board) is True
    assert board.get_piece_at((far_row - 1, 2)).getName() == "Queen"

    # And a FEN export over the same board.
    record = ChessNotationWriter().to_fen(board)
    placement_field = record.split(" ")[0]

    assert len(placement_field.split("/")) == rows


def test_a_fen_export_never_reports_more_files_than_the_board_has():
    rows, cols = 5, 7
    board = Board((rows, cols), setup_pieces=False)
    board.set_piece_at((0, 0), King(1))

    record = ChessNotationWriter().to_fen(board)
    placement_field = record.split(" ")[0]
    ranks = placement_field.split("/")

    assert len(ranks) == rows
    for rank in ranks:
        width = sum(int(ch) if ch.isdigit() else 1 for ch in rank)
        assert width == cols


def test_the_shipped_board_still_serialises_unchanged():
    """Board generalisation must not move a single piece on the size that ships."""
    board = build_board()
    record = ChessNotationWriter().to_fen(board)

    assert record.split(" ")[0] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    assert board.get_piece_at((0, 1)).getName() == "Horse"
    assert board.get_piece_at((7, 7)).getName() == "Rook"


def test_every_size_yields_a_distinct_board_and_a_distinct_record():
    records = set()
    for rows, cols in SIZES:
        board = Board((rows, cols), setup_pieces=False)
        board.set_piece_at((0, 0), King(1))
        records.add(ChessNotationWriter().to_fen(board).split(" ")[0])

    assert len(records) == len(SIZES)
