"""Perft for English draughts: how many legal moves a position has, counted to a depth.

`tests/test_perft.py` is the chess equivalent and the reason chess's move generation is
provably correct. This is the same gate for draughts, and it exists because a draughts move
generator has more ways to be quietly wrong than chess's: a man that jumps forwards only, a
king that jumps any distance, a chain that must be carried through, a man that stops the
moment it is crowned, and a jump that is compulsory the instant one exists. A bug in any of
those makes the count wrong and nothing else in the suite would notice.

**Where the expected numbers come from.** They are data, written into this file, and they are
data from outside this repository. Two published series are used, because the one everybody
quotes and the one this configuration plays by default stopped agreeing at depth six:

- `PUBLISHED` — OEIS **A133046**, "starting from the standard 12 against 12 starting position
  in checkers, the number of distinct move sequences after n moves". Its references are Aart
  Bik's engine, Martin Fierz's CheckerBoard, Igor Korshunov's correctness suite, and Schaeffer
  et al.'s *Checkers is solved*, so it is the series the solved game was measured against.
  Values to depth eight: 7, 49, 302, 1469, 7361, 36768, 179740, 845931.
- `PUBLISHED_MAJORITY` — the same game with the maximum-capture restriction switched on, from
  Rein Halbersma's perft table for the recognised draughts variants (the majority-capture
  family on the 8x8 board). Values to depth eight: 7, 49, 302, 1469, 7361, 36473, 177532,
  828783. `games/checkers` ships with that restriction *off*, because the WCDF rulebook says a
  player "may select any one that they wish, not necessarily that which gains the most pieces",
  so `PUBLISHED` is the series the configuration is gated against and `PUBLISHED_MAJORITY` is
  the one the `max_capture` switch is gated against.
- `PUBLISHED_DIVIDE` — Aart Bik's published `divide(6)` for the starting position, the seven
  figures his engine produces after each of the seven opening moves. This is the sharper of
  the two kinds of check, because a wrong count split across seven moves usually gives seven
  wrong figures rather than one wrong total.

Neither is produced by the engine under test. `REFERENCE` below is a second, independent
move generator written from the rules with no engine import at all, and one of the tests here
asserts that it reproduces `PUBLISHED` — so the published figures are corroborated rather than
merely asserted, and the deepest depth either can be checked in a test session is eight.

**A third gate is below all of them**: random playouts from the opening, engine move list
against reference move list, position by position, on a fixed seed. A perft total says that
*somebody* is wrong; the sweep names the position.
"""

import copy
import random
from typing import Any, Dict, List, Tuple

import pytest

from model.game.board import Board
from model.game.validator import MoveValidator

#: Published perft counts for the English draughts starting position, as `PUBLISHED` above.
PUBLISHED: Tuple[Tuple[int, int], ...] = (
    (1, 7),
    (2, 49),
    (3, 302),
    (4, 1469),
    (5, 7361),
    (6, 36768),
    (7, 179740),
    (8, 845931),
)

#: The same counts with the maximum-capture restriction in force.
PUBLISHED_MAJORITY: Tuple[Tuple[int, int], ...] = (
    (1, 7),
    (2, 49),
    (3, 302),
    (4, 1469),
    (5, 7361),
    (6, 36473),
    (7, 177532),
    (8, 828783),
)

#: Aart Bik's published `divide(6)`: the number of six-ply sequences after each opening move.
PUBLISHED_DIVIDE: Dict[str, int] = {
    "9-13": 6638,
    "9-14": 4133,
    "10-14": 4265,
    "10-15": 4659,
    "11-15": 4289,
    "11-16": 6805,
    "12-16": 5979,
}

#: The depths this suite walks the engine to. Seven takes about half a minute and eight
#: takes five minutes, which is the wrong side of a CI budget for a check that adds nothing at
#: that depth: the independent counter reaches eight in seconds and is held to the same
#: figures two tests above.
ENGINE_DEPTHS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)

#: The depth the maximum-capture variant is walked to. One shallower, because it is a
#: variant rather than the game and it exists here to prove the switch is wired to something.
MAJORITY_DEPTHS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)


# --------------------------------------------------------------------------------------
# The independent counter. Written from the rules, importing nothing from the engine.
# --------------------------------------------------------------------------------------
#
# Squares are numbered 1 to 32 in the standard way: four playable squares to a row, rows
# counted from the near side, so 1 to 4 is row zero, 9 to 12 is row two and 29 to 32 is row
# seven. That is the same numbering the published `divide` figures above are written in, and
# it is derived here from the geometry of the dark squares rather than read off the engine.


#: The two colours, and the two kinds of piece.
WHITE: int = 1
BLACK: int = -1
MAN: str = "man"
KING: str = "king"

#: How wide the board is.
WIDTH: int = 8


def square_of(row: int, col: int) -> int:
    """Return the number of the playable square at a coordinate.

    Args:
        row: Zero-based row index.
        col: Zero-based column index.

    Returns:
        int: The square's number, 1 to 32.
    """
    return row * 4 + col // 2 + 1


def coordinates(square: int) -> Tuple[int, int]:
    """Return the coordinate of a numbered square.

    Args:
        square: The square's number, 1 to 32.

    Returns:
        Tuple[int, int]: Its (row, col).
    """
    row = (square - 1) // 4
    index = (square - 1) % 4
    return row, 2 * index + (1 if row % 2 == 0 else 0)


def _ray(square: int, step: Tuple[int, int]) -> List[int]:
    """Return the squares on one diagonal from a square, nearest first.

    Args:
        square: Where the diagonal starts.
        step: (row offset, col offset) per square along it.

    Returns:
        List[int]: The playable squares along the diagonal, in order, nearest first.
    """
    row, col = coordinates(square)
    line: List[int] = []
    row, col = row + step[0], col + step[1]
    while 0 <= row < WIDTH and 0 <= col < WIDTH:
        if (row + col) % 2 == 1:
            line.append(square_of(row, col))
        row, col = row + step[0], col + step[1]
    return line


#: Every diagonal on the board, as (row offset, col offset) to ray from.
DIAGONALS: Dict[Tuple[int, int], Dict[int, List[int]]] = {
    step: {square: _ray(square, step) for square in range(1, 33)}
    for step in ((1, 1), (1, -1), (-1, 1), (-1, -1))
}

#: The squares on which a man of each colour is crowned.
CROWN_ROW: Dict[int, frozenset] = {
    WHITE: frozenset(range(29, 33)),
    BLACK: frozenset(range(1, 5)),
}

#: A position: square number to (colour, kind).
Position = Dict[int, Tuple[int, str]]


def starting_position() -> Position:
    """Return the starting position: twelve men a side on the three rows nearest each side.

    Returns:
        Position: Twelve white men on 1 to 12 and twelve black men on 21 to 32.
    """
    position: Position = {square: (WHITE, MAN) for square in range(1, 13)}
    position.update({square: (BLACK, MAN) for square in range(21, 33)})
    return position


def _forward(colour: int) -> int:
    """Return the row offset a colour's men travel along.

    Args:
        colour: WHITE or BLACK.

    Returns:
        int: 1 for white, -1 for black.
    """
    return 1 if colour == WHITE else -1


def _jumps(position: Position, square: int, colour: int, kind: str) -> List[Tuple[int, int]]:
    """Return every jump available from a square right now.

    A man leaps over the piece immediately beside it and lands on the square immediately
    beyond, forwards only. A king walks over empty squares until it meets the first piece on
    the diagonal: its own ends the diagonal, its opponent's is taken, and every empty square
    beyond that piece may be landed on. Only the first piece is ever taken.

    Args:
        position: The position as it stands, victims already lifted.
        square: Where the jumping piece stands.
        colour: The colour of the jumping piece.
        kind: MAN or KING.

    Returns:
        List[Tuple[int, int]]: One (landing square, captured square) pair per jump.
    """
    options: List[Tuple[int, int]] = []
    for step, ray in DIAGONALS.items():
        line = ray[square]
        if kind == MAN:
            if step[0] != _forward(colour) or len(line) < 2:
                continue
            over, land = line[0], line[1]
            victim = position.get(over)
            if victim is not None and victim[0] != colour and land not in position:
                options.append((land, over))
        else:
            for index, over in enumerate(line):
                victim = position.get(over)
                if victim is None:
                    continue
                if victim[0] == colour:
                    break
                for land in line[index + 1 :]:
                    if land in position:
                        break
                    options.append((land, over))
                break
    return options


def _crowned(colour: int, kind: str, square: int) -> Tuple[int, str]:
    """Return what a piece standing on a square has become.

    Args:
        colour: The piece's colour.
        kind: What it was before it got there.
        square: Where it landed.

    Returns:
        Tuple[int, str]: A king if it was a man that reached the crown row, else unchanged.
    """
    if kind == MAN and square in CROWN_ROW[colour]:
        return colour, KING
    return colour, kind


def _chains(
    position: Position, square: int, colour: int, kind: str
) -> List[Tuple[List[int], List[int]]]:
    """Return every complete chain one piece can play, each carried as far as it goes.

    A chain is recorded only where no further jump is available, which is the rule that a
    chain may not be abandoned part-way, and a man that reaches the crown row stops there
    because a man cannot jump backwards off it.

    Args:
        position: The position to read. It is restored before this returns.
        square: Where the piece stands.
        colour: The piece's colour.
        kind: MAN or KING.

    Returns:
        List[Tuple[List[int], List[int]]]: One (route, victims) pair per chain, where the
        route is the landing square of each jump in order.
    """
    found: List[Tuple[List[int], List[int]]] = []

    def walk(route: List[int], victims: List[int]) -> None:
        here = route[-1]
        crowned_here = kind == MAN and here in CROWN_ROW[colour]
        options = [] if crowned_here else _jumps(position, here, colour, kind)
        if not options:
            if victims:
                found.append((list(route), list(victims)))
            return
        for land, over in options:
            taken = position.pop(over)
            walk(route + [land], victims + [over])
            position[over] = taken

    walk([square], [])
    return found


def reference_moves(position: Position, colour: int, max_capture: bool = False) -> List[Any]:
    """Return every legal move for a colour, each as (from, to, victims, new position).

    Args:
        position: The position to read.
        colour: The colour to move.
        max_capture: Whether only the chains taking the most pieces may be played. False is
            English draughts; True is the international, Brazilian, Czech, Italian and Spanish
            rule.

    Returns:
        List[Any]: One (from square, to square, captured squares, resulting position) per
        legal move, in a stable order.
    """
    captures: List[Tuple[int, List[int], List[int], str]] = []
    for square in sorted(position):
        if position[square][0] != colour:
            continue
        kind = position[square][1]
        for route, victims in _chains(position, square, colour, kind):
            captures.append((square, route, victims, kind))

    moves: List[Any] = []
    if captures:
        best = max(len(victims) for _, _, victims, _ in captures)
        for origin, route, victims, kind in captures:
            if max_capture and len(victims) != best:
                continue
            after = dict(position)
            del after[origin]
            for victim in victims:
                del after[victim]
            after[route[-1]] = _crowned(colour, kind, route[-1])
            moves.append(((origin, route[-1]), tuple(victims), after))
        return moves

    for square in sorted(position):
        piece_colour, kind = position[square]
        if piece_colour != colour:
            continue
        for step, ray in DIAGONALS.items():
            if kind == MAN:
                if step[0] != _forward(colour):
                    continue
                targets = ray[square][:1]
            else:
                targets = ray[square]
            for land in targets:
                if land in position:
                    break
                after = dict(position)
                del after[square]
                after[land] = _crowned(colour, kind, land)
                moves.append(((square, land), (), after))
    return moves


def reference_perft(position: Position, colour: int, depth: int, max_capture: bool = False) -> int:
    """Count the leaf nodes of the legal move tree to a depth.

    Args:
        position: The position to start from.
        colour: The side to move.
        depth: How many plies to search.
        max_capture: Whether the maximum-capture restriction is in force.

    Returns:
        int: The number of move sequences of exactly `depth` plies.
    """
    if depth == 0:
        return 1
    moves = reference_moves(position, colour, max_capture)
    if depth == 1:
        return len(moves)
    return sum(reference_perft(after, -colour, depth - 1, max_capture) for _, _, after in moves)


def reference_divide(position: Position, colour: int, depth: int, max_capture: bool = False):
    """Split the leaf count of a position across its legal moves.

    Args:
        position: The position to start from.
        colour: The side to move.
        depth: How many plies to count, counting the first one.
        max_capture: Whether the maximum-capture restriction is in force.

    Returns:
        Dict[str, int]: Move name to leaf count, where the name is `from-to` in the standard
        numbering.
    """
    split: Dict[str, int] = {}
    for (origin, land), _, after in reference_moves(position, colour, max_capture):
        split[f"{origin}-{land}"] = reference_perft(after, -colour, depth - 1, max_capture)
    return split


# --------------------------------------------------------------------------------------
# The engine side. A draughts capture chain is one move, so a walk is one rule set told
# about every move, exactly as in tests/test_perft.py.
# --------------------------------------------------------------------------------------


def build_rules(max_capture: bool = False) -> List[Any]:
    """Build one instance of every checkers rule.

    Args:
        max_capture: Whether to switch the maximum-capture restriction on.

    Returns:
        List[Any]: The rules in force, in declaration order.
    """
    from games.checkers.rules import build_rules as compose

    rules = compose()
    rules[0].value["max_capture"] = max_capture
    return rules


def starting_board() -> Board:
    """Return the checkers starting position.

    Returns:
        Board: A freshly dealt eight by eight board with twelve men a side.
    """
    from games.checkers.board import build_board

    return build_board()


def engine_moves(board: Board, colour: int, rules: List[Any]) -> List[Tuple[int, int, Any]]:
    """Return every legal move for a side, each with the position it produces.

    The position is read by playing the move and taking it off again through the engine's own
    `apply_to_board`/`unapply_from_board` pair, so what is compared is what the game would
    really reach rather than what the move object claims.

    Args:
        board: The position to read.
        colour: The side to move.
        rules: The rules in force.

    Returns:
        List[Tuple[int, int, Any]]: (from square, to square, position afterwards) per move.
    """
    validator = MoveValidator(board)
    validator.set_rules(rules, attach=False)
    found: List[Tuple[int, int, Any]] = []
    for move in validator.get_all_valid_moves(colour, board):
        before = snapshot(board)
        applied = move.apply_to_board(board)
        after = snapshot(board)
        move.unapply_from_board(board, applied)
        assert snapshot(board) == before, "asking whether a move is legal left the board dirty"
        found.append((square_of(*move.start_pos), square_of(*move.end_pos), after))
    return found


def snapshot(board: Board) -> Tuple[Any, ...]:
    """Record everything about a position that playing a move can change.

    Args:
        board: The position to record.

    Returns:
        Tuple[Any, ...]: The pieces as (square, colour, kind, has_moved) quadruples.
    """
    found: List[Tuple[int, int, str, bool]] = []
    for row in range(board.rows):
        for col in range(board.cols):
            piece = board.get_piece_at((row, col))
            if piece is not None:
                found.append(
                    (square_of(row, col), piece.getColor(), piece.getType(), piece.has_moved)
                )
    return tuple(found)


def as_position(record: Tuple[Any, ...]) -> Position:
    """Read a snapshot as a position the independent counter understands.

    Args:
        record: A snapshot.

    Returns:
        Position: Square number to (colour, kind).
    """
    return {square: (colour, kind) for square, colour, kind, _ in record}


def perft(board: Board, rules: List[Any], colour: int, depth: int) -> int:
    """Count the leaf nodes of the legal move tree to a depth, through the engine.

    Every move is taken off the board again through the engine's own
    `unapply_from_board`, never by rebuilding the board from a snapshot. That is not a style
    choice. `Move` records the piece that moved, and `HopMove` refuses a chain unless the
    piece standing on its starting square is that very object; a walk that put a fresh, equal
    looking piece back on the square instead silently invalidated every move it had already
    generated, and counted a different tree without saying so. Chess's perft restores the
    original objects for the same reason.

    One rule set is kept for the whole walk and told about every move, so a rule that
    remembers something sees the same history a game would give it. Whatever it remembered is
    snapshotted and put back afterwards.

    Args:
        board: The position to start from.
        rules: The rules in force.
        colour: The side to move.
        depth: How many plies to search.

    Returns:
        int: The number of move sequences of exactly `depth` plies.
    """
    if depth == 0:
        return 1
    moves = _composed(rules, board).get_all_valid_moves(colour, board)
    if depth == 1:
        return len(moves)
    total = 0
    for move in moves:
        states = [copy.deepcopy(rule.state) for rule in rules]
        applied = move.apply_to_board(board)
        assert applied is not None, f"{move} was offered and then could not be played"
        for rule in rules:
            rule.on_move_made(board, move)
        total += perft(board, rules, -colour, depth - 1)
        move.unapply_from_board(board, applied)
        for rule, state in zip(rules, states):
            rule.state = copy.deepcopy(state)
    return total


def divide(board: Board, rules: List[Any], colour: int, depth: int) -> Dict[str, int]:
    """Split the leaf count of a position across its legal moves, through the engine.

    Args:
        board: The position to start from.
        rules: The rules in force.
        colour: The side to move.
        depth: How many plies to count, counting the first one.

    Returns:
        Dict[str, int]: Move name to leaf count, written as `from-to`.
    """
    split: Dict[str, int] = {}
    for move in _composed(rules, board).get_all_valid_moves(colour, board):
        states = [copy.deepcopy(rule.state) for rule in rules]
        applied = move.apply_to_board(board)
        for rule in rules:
            rule.on_move_made(board, move)
        name = f"{square_of(*move.start_pos)}-{square_of(*move.end_pos)}"
        split[name] = perft(board, rules, -colour, depth - 1)
        move.unapply_from_board(board, applied)
        for rule, state in zip(rules, states):
            rule.state = copy.deepcopy(state)
    return split


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


def _build(kind: str, colour: int) -> Any:
    """Build a piece of a kind and colour.

    Args:
        kind: The piece's kind, `man` or `king`.
        colour: The piece's colour.

    Returns:
        Any: The piece.
    """
    from games.checkers.pieces.king import King
    from games.checkers.pieces.man import Man

    return Man(colour) if kind == "man" else King(colour)


# --------------------------------------------------------------------------------------
# The gates.
# --------------------------------------------------------------------------------------


def test_the_independent_counter_reproduces_the_published_series():
    """The figures asserted below are corroborated before anything is measured against them.

    `REFERENCE` is a second move generator written from the rules, importing nothing from this
    repository's engine. It reaches depth eight in a few seconds and it lands on OEIS A133046
    exactly, so the numbers the engine is held to are the published ones and not the engine's
    opinion of them. It also reaches depth eight in the majority-capture variant, which is the
    series the `max_capture` switch is held to.

    Returns:
        None
    """
    assert [reference_perft(starting_position(), WHITE, depth) for depth, _ in PUBLISHED] == [
        count for _, count in PUBLISHED
    ]
    assert [
        reference_perft(starting_position(), WHITE, depth, max_capture=True)
        for depth, _ in PUBLISHED_MAJORITY
    ] == [count for _, count in PUBLISHED_MAJORITY]


def test_the_independent_counter_reproduces_the_published_divide():
    """The same corroboration one level finer, on the figure that is hardest to hit by luck.

    Seven opening moves whose six-ply counts all land exactly. A counter that had a rule
    wrong would not agree with a published divide on all seven at once, and a counter that had
    mis-numbered the squares would not produce these seven names either.

    Returns:
        None
    """
    assert reference_divide(starting_position(), WHITE, 6) == PUBLISHED_DIVIDE


@pytest.mark.parametrize("depth,expected", PUBLISHED[: len(ENGINE_DEPTHS)])
def test_the_starting_position_has_exactly_as_many_moves_as_checkers_says(depth, expected):
    """The published counts, asserted exactly at every depth this suite walks.

    Returns:
        None
    """
    assert perft(starting_board(), build_rules(), WHITE, depth) == expected


def test_the_engine_divide_matches_the_published_divide():
    """The seven opening moves, each held to its own published count.

    Returns:
        None
    """
    assert divide(starting_board(), build_rules(), WHITE, 6) == PUBLISHED_DIVIDE


@pytest.mark.parametrize("depth,expected", PUBLISHED_MAJORITY[: len(MAJORITY_DEPTHS)])
def test_the_maximum_capture_variant_counts_as_the_published_table_says(depth, expected):
    """The switch is wired to a real difference, and to the published figures for it.

    This is the half of the rule that English draughts does not have. Switching it on has to
    change the count, and it has to change it to the numbers published for the game that does
    have it — otherwise the switch is a decoration that happens to remove some moves.

    Returns:
        None
    """
    assert perft(starting_board(), build_rules(max_capture=True), WHITE, depth) == expected


# --------------------------------------------------------------------------------------
# The differential sweep. A total says that somebody is wrong; this says where.
# --------------------------------------------------------------------------------------

#: How many games the sweep plays, and how far into each one it compares every position.
SWEEP_GAMES: int = 12
SWEEP_PLIES: int = 44

#: The seed, fixed because a test that finds a bug only when it feels like it is not a test.
SWEEP_SEED: int = 20261003


def _same_moves(engine: List[Tuple[int, int, Any]], reference: List[Any]) -> bool:
    """Report whether the engine and the reference offer the same moves.

    Args:
        engine: What the engine offered, as (from, to, position afterwards).
        reference: What the reference offered, as ((from, to), victims, position).

    Returns:
        bool: True when both lists describe the same set of moves.
    """
    mine = sorted(
        (origin, land, tuple(sorted(as_position(after).items()))) for origin, land, after in engine
    )
    theirs = sorted(
        (origin, land, tuple(sorted(after.items()))) for (origin, land), _, after in reference
    )
    return mine == theirs


@pytest.mark.parametrize("game", range(SWEEP_GAMES))
def test_the_engine_and_the_reference_agree_through_a_whole_game(game):
    """Play a random game, comparing every position against the independent counter.

    Sixty per cent of the rules of draughts are about jumps, chains and crowning, and the
    perft totals above only reach a handful of those situations from the opening position.
    Random play reaches the rest — kings that jump three times, a man crowned mid-chain, a
    chain that has to be carried through whether the player wants to or not — and every single
    ply is compared move list against move list and resulting position against resulting
    position.

    The walk is driven by the reference, so the positions visited are positions the reference
    believes in, and the engine is asked about each one in turn.

    Args:
        game: Which game of the sweep this is, so a failure names it.

    Returns:
        None
    """
    rng = random.Random(SWEEP_SEED + game)
    position = starting_position()
    colour = WHITE
    for ply in range(SWEEP_PLIES):
        expected = reference_moves(position, colour)
        board = _to_board(position)
        found = engine_moves(board, colour, build_rules())
        assert _same_moves(found, expected), (
            f"game {game} ply {ply}: {as_position(snapshot(board))}\n"
            f"engine {[ (o, l) for o, l, _ in found ]}\n"
            f"reference {[ (o, l) for (o, l), _, _ in expected ]}"
        )
        if not expected:
            break
        position = rng.choice(expected)[2]
        colour = -colour


def _to_board(position: Position) -> Board:
    """Build a board from a position the independent counter produced.

    Args:
        position: Square number to (colour, kind).

    Returns:
        Board: The board, eight by eight, with those pieces on it.
    """
    board = Board((WIDTH, WIDTH))
    for square, (colour, kind) in position.items():
        board.set_piece_at(coordinates(square), _build(kind, colour))
    return board


# --------------------------------------------------------------------------------------
# Regression positions. Each is the smallest reproducible form of what the counts above are
# made of, and each names one way a draughts generator invents or withholds a move.
#
# The counts below are the independent counter's, not a published series: every published
# figure for this game is from the starting position. The counter itself is anchored by
# `test_the_independent_counter_reproduces_the_published_series` and by the eight published
# depths above, so a counter with a rule wrong is caught long before it reaches these.
# --------------------------------------------------------------------------------------

#: **A man crowned by a jump.** White's man on 21 is one square from the crown row with the
#: black man on 25 beside it, so its only move is a jump that lands on 30 and makes it a king.
#: Three ways to be wrong here, and the count moves for each: a generator that crowns it as a
#: man, one that carries the chain on past the crown row as a king, and one that refuses the
#: crowning altogether.
CROWNING: Position = {
    11: (BLACK, MAN),
    16: (BLACK, MAN),
    20: (BLACK, MAN),
    21: (WHITE, MAN),
    25: (BLACK, MAN),
}

#: The independent counter's counts for `CROWNING`, white to move.
CROWNING_PERFT: Dict[int, int] = {1: 1, 2: 3, 3: 8, 4: 27}


@pytest.mark.parametrize("depth,expected", sorted(CROWNING_PERFT.items()))
def test_a_position_where_a_man_is_crowned_by_a_jump_counts_as_the_rules_say(depth, expected):
    """The one move is 21x30 and it arrives a king; the rest of the tree follows from that.

    Returns:
        None
    """
    assert reference_perft(CROWNING, WHITE, depth) == expected
    assert perft(_to_board(CROWNING), build_rules(), WHITE, depth) == expected


#: **A chain that has to be carried through.** Black's man on 19 may jump the white man on 15
#: and land on 10, and from 10 there is a second jump available over the white man on 6 onto
#: 1. The rule is that the second jump is not optional, so this position has exactly one move
#: and not two and not a quiet one. A generator that stops a chain as soon as it has taken
#: something it was offered, or that offers the half-finished 19x10 as well, is wrong here.
CHAIN: Position = {
    2: (WHITE, MAN),
    3: (WHITE, MAN),
    4: (WHITE, MAN),
    5: (WHITE, MAN),
    6: (WHITE, MAN),
    7: (WHITE, MAN),
    8: (WHITE, MAN),
    11: (WHITE, MAN),
    12: (WHITE, MAN),
    15: (WHITE, MAN),
    19: (BLACK, MAN),
    21: (BLACK, MAN),
    24: (BLACK, MAN),
    25: (BLACK, MAN),
    27: (BLACK, MAN),
    28: (BLACK, MAN),
    29: (BLACK, MAN),
    30: (BLACK, MAN),
    31: (BLACK, MAN),
    32: (BLACK, MAN),
}

#: The independent counter's counts for `CHAIN`, black to move.
CHAIN_PERFT: Dict[int, int] = {1: 1, 2: 6, 3: 40, 4: 190}


@pytest.mark.parametrize("depth,expected", sorted(CHAIN_PERFT.items()))
def test_a_position_with_one_mandatory_two_jump_chain_counts_as_the_rules_say(depth, expected):
    """One move, not two: the chain may not be abandoned half way.

    Returns:
        None
    """
    assert reference_perft(CHAIN, BLACK, depth) == expected
    assert perft(_to_board(CHAIN), build_rules(), BLACK, depth) == expected


def test_a_chain_that_may_be_abandoned_half_way_is_not_offered():
    """The half-chain is not in the list at all, which is what the count above rests on.

    Returns:
        None
    """
    offered = {f"{a}-{b}": victims for (a, b), victims, _ in reference_moves(CHAIN, BLACK)}
    assert offered == {"19-1": (15, 6)}
