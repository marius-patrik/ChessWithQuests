"""Move validation: rules in force, pins, checks, and terminal conditions."""

from typing import Any, Iterable, List, Optional, Tuple

from model.game.board import Board
from model.game.move import Move
from model.game.rule import ROYAL_KIND, Result, Rule, resolve_outcomes
from model.pieces.piece import Piece


def _ray_length(board: Board) -> int:
    """Return the longest ray a sliding piece can travel on this board.

    Args:
        board: The board being measured.

    Returns:
        int: The greater of the two dimensions, which no straight ray can exceed.
    """
    return max(board.rows, board.cols)


class MoveValidator:
    """Validates piece movement legality, checks, checkmates, and stalemates.

    The validator asks and rules answer. It owns no game logic of its own: a rule may permit
    or forbid a move, may offer a move, and may propose an outcome, and the validator is
    what turns those answers into the set of moves a player can actually play.
    """

    def __init__(
        self,
        board: Optional[Board] = None,
        move: Optional[Move] = None,
        rules: Optional[Iterable[Rule]] = None,
    ):
        """Initialize a MoveValidator instance.

        Args:
            board: Optional Board instance to validate moves on.
            move: Optional Move instance being inspected.
            rules: Optional rules in force, composed explicitly by the configuration.
        """
        self.board = board
        self.move = move
        self.rules: List[Rule] = []
        self.legal_candidates: List[Move] = []
        if rules:
            self.set_rules(rules)

    def set_rules(
        self,
        rules: Iterable[Rule],
        clock: Any = None,
        active_color: Optional[int] = None,
        attach: bool = True,
    ) -> None:
        """Replace the rules in force and hand them the game they are joining.

        Args:
            rules: The rules in force, in the order the configuration declared them.
            clock: The game's clock, for a rule about time. One that is not supplied leaves
                each rule holding whatever clock it already had, because a question about
                the game must not take the clock away from the rule that was reading it.
            active_color: Whose turn it is, for a rule that cannot work it out from a board.
            attach: Whether to attach the rules that are in force. Attaching is what a game
                does when it starts: it hands each rule the board it will read and clears
                the history the rule accumulated in the last one. A question asked mid-game
                composes the rules it was given and passes `False` here, because re-attaching
                wipes the very history the question is about — the positions a repetition has
                seen, the colours that have castled, the clock a flag-fall rule reads.

        Returns:
            None
        """
        self.rules = list(rules)
        for rule in self.rules:
            rule.rules = self.rules
            # Handing a rule its clock or whose turn it is only when one was supplied. A
            # question like "does anybody have a legal move" composes the same rules again
            # from a validator that has never seen them, and passing no clock used to strip
            # the clock rule of the clock it was reading, so a flagged player could never
            # lose on time.
            if clock is not None:
                rule.clock = clock
            if active_color is not None:
                rule.active_color = active_color
        if attach:
            for rule in dict.fromkeys(self.rules):
                rule.attach()

    def active_rules(self) -> List[Rule]:
        """Return the rules that are in force.

        Returns:
            List[Rule]: The rules whose `enabled` is True, in declaration order.
        """
        return [rule for rule in self.rules if rule.enabled]

    def resolve_outcome(self, board: Optional[Board] = None) -> Optional[Result]:
        """Ask every rule whether the game is over and settle what they say.

        Args:
            board: Optional Board instance (defaults to self.board).

        Returns:
            Optional[Result]: The outcome that wins, or None when no rule proposes one.
        """
        b = board or self.board
        if b is None:
            return None
        return resolve_outcomes(
            [result for result in (rule.outcome(b) for rule in self.active_rules()) if result]
        )

    def status(self, board: Optional[Board] = None) -> Optional[str]:
        """Ask every rule whether it has something worth showing.

        Args:
            board: Optional Board instance (defaults to self.board).

        Returns:
            Optional[str]: The first thing a rule reports, or None when nothing does.
        """
        b = board or self.board
        if b is None:
            return None
        for rule in self.active_rules():
            message = rule.status(b)
            if message:
                return message
        return None

    def notify_move_made(self, move: Move, board: Optional[Board] = None) -> None:
        """Tell every rule a move has been played.

        Args:
            move: The move that was played.
            board: Optional Board instance (defaults to self.board).

        Returns:
            None
        """
        b = board or self.board
        for rule in self.active_rules():
            rule.on_move_made(b, move)

    def set_board(self, board: Board) -> None:
        """Assign the active chessboard.

        Args:
            board: Board instance.
        """
        self.board = board

    def set_move(self, move: Move) -> None:
        """Assign the active move to evaluate.

        Args:
            move: Move instance.
        """
        self.move = move

    def royal_kinds(self) -> List[str]:
        """Return the piece kinds the rules in force declare royal.

        A rule declares a royal kind by declaring a configured value called `royal_kind`.
        Whether a position has a king is therefore a rule, never a lookup by type name: a
        configuration with no such declaration simply has no royal piece, and a custom piece
        whose kind is not the declared one is just an ordinary piece.

        Returns:
            List[str]: The declared royal kinds, in declaration order. Each kind appears
            once however many rules declare it, since several rules need to know it.
        """
        declared = [
            rule.value[ROYAL_KIND] for rule in self.active_rules() if rule.value.get(ROYAL_KIND)
        ]
        return list(dict.fromkeys(declared))

    def find_royal(self, color: int, board: Optional[Board] = None) -> Optional[Tuple[int, int]]:
        """Find the coordinates of a colour's royal piece.

        Args:
            color: Colour of the player (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            Tuple of (row, col) coordinates, or None when the configuration declares no
            royal piece of that colour or none is on the board.
        """
        b = board or self.board
        kinds = self.royal_kinds()
        if b is None or not kinds:
            return None
        for r in range(b.rows):
            for c in range(b.cols):
                piece = b.get_piece_at((r, c))
                if piece is not None and piece.getColor() == color and piece.getType() in kinds:
                    return (r, c)
        return None

    def is_square_attacked(
        self, target_square: Tuple[int, int], by_color: int, board: Optional[Board] = None
    ) -> bool:
        """Determine whether a given square is under attack by pieces of a given color.

        Args:
            target_square: (row, col) target coordinates.
            by_color: Color of the attacking side (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if target_square is attacked by by_color pieces, False otherwise.
        """
        b = board or self.board
        if b is None:
            return False

        tr, tc = target_square
        for r in range(b.rows):
            for c in range(b.cols):
                piece = b.get_piece_at((r, c))
                if piece is None or piece.getColor() != by_color:
                    continue

                directions = piece.getAttackDirections() or []
                can_jump = piece.canJump()
                max_steps = self._step_limit(piece, b)

                for dr, dc in directions:
                    step = 1
                    while step <= max_steps:
                        nr, nc = r + dr * step, c + dc * step
                        if not b.is_within_bounds(nr, nc):
                            break
                        if (nr, nc) == (tr, tc):
                            return True
                        if not can_jump and b.get_piece_at((nr, nc)) is not None:
                            break
                        step += 1
        return False

    def is_check(self, color: int, board: Optional[Board] = None) -> bool:
        """Report whether a colour's royal piece is under attack.

        Args:
            color: Player color to check (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if the royal piece is attacked, False otherwise, including when the
            configuration declares no royal piece.
        """
        b = board or self.board
        if b is None:
            return False
        royal_pos = self.find_royal(color, b)
        if royal_pos is None:
            return False
        return self.is_square_attacked(royal_pos, self.opponent(color), b)

    @staticmethod
    def opponent(color: int) -> int:
        """Return the other side's colour.

        Args:
            color: One side's colour.

        Returns:
            int: The opposing colour.
        """
        return -color

    def get_pseudo_legal_moves(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Tuple[int, int]]:
        """Compute candidate move destinations, ignoring check constraints.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List[Tuple[int, int]]: Candidate destination squares.
        """
        return [move.end_pos for move in self.get_candidate_moves(start_pos, board)]

    def get_candidate_moves(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Move]:
        """Compute candidate move destinations, ignoring check constraints.

        Destinations come from what the piece declares, never from what the engine knows it
        is. Three shapes cover every game in this configuration and any other: an offset in
        both the move and the attack vectors moves and takes; an offset in the move vectors
        only moves to an empty square; an offset in the attack vectors only takes.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List[Move]: Candidate moves, before the rules in force have forbidden any.
        """
        b = board or self.board
        if b is None:
            return []

        piece = b.get_piece_at(start_pos)
        if piece is None:
            return []

        moves: List[Move] = [
            move
            for move in self._rule_moves(b, piece)
            if move is not None and move.start_pos == tuple(start_pos)
        ]
        seen = {move.end_pos for move in moves}

        quiet = piece.getDirections() or []
        attack = piece.getAttackDirections() or []
        moves_and_takes = [vector for vector in quiet if vector in attack]
        move_only = [vector for vector in quiet if vector not in attack]
        take_only = [vector for vector in attack if vector not in quiet]
        step_limit = self._step_limit(piece, b)

        r, c = start_pos

        def add(destination: Tuple[int, int]) -> None:
            if destination in seen:
                return
            seen.add(destination)
            target = b.get_piece_at(destination)
            if target is not None and target.getColor() == piece.getColor():
                return
            moves.append(
                Move(
                    start_pos=(r, c),
                    end_pos=destination,
                    piece=piece,
                    move_type="capture" if target is not None else "normal",
                )
            )

        for dr, dc in moves_and_takes:
            for destination in self._ray(b, (r, c), dr, dc, step_limit):
                add(destination)
        for dr, dc in move_only:
            for destination in self._ray(b, (r, c), dr, dc, step_limit):
                if b.get_piece_at(destination) is not None:
                    break
                add(destination)
        for dr, dc in take_only:
            nr, nc = r + dr, c + dc
            if not b.is_within_bounds(nr, nc):
                continue
            target = b.get_piece_at((nr, nc))
            if target is not None and target.getColor() != piece.getColor():
                add((nr, nc))

        if not piece.hasMoved():
            for dr, dc in piece.getInitialVectors():
                nr, nc = r + dr, c + dc
                if not b.is_within_bounds(nr, nc) or b.get_piece_at((nr, nc)) is not None:
                    continue
                # A first-only advance is a walk, not a leap: every square between here and
                # there must be empty, or the piece steps over whatever is sitting on it.
                # The square it lands on was just tested, so the squares to test are the
                # ones strictly between — one step along the walk for each square skipped.
                blocked = False
                steps = max(abs(dr), abs(dc))
                for step in range(1, steps):
                    middle = (r + (dr // steps) * step, c + (dc // steps) * step)
                    if b.get_piece_at(middle) is not None:
                        blocked = True
                        break
                if not blocked:
                    add((nr, nc))

        return moves

    @staticmethod
    def _step_limit(piece: Piece, board: Board) -> int:
        """Return how many squares one step of this piece may travel.

        Args:
            piece: The piece being measured.
            board: The board it stands on.

        Returns:
            int: One for a piece that jumps or declares a step length, and the longest ray
            the board allows otherwise.
        """
        if piece.canJump() or piece.getMaxSteps() is not None:
            return 1
        return _ray_length(board)

    @staticmethod
    def _ray(
        board: Board, origin: Tuple[int, int], dr: int, dc: int, limit: int
    ) -> List[Tuple[int, int]]:
        """Walk one offset from a square until something is in the way.

        Args:
            board: The board to walk.
            origin: The (row, col) square to start from.
            dr: Row offset per step.
            dc: Column offset per step.
            limit: How many steps at most.

        Returns:
            List[Tuple[int, int]]: Every in-bounds square along the ray, in order.
        """
        squares: List[Tuple[int, int]] = []
        for step in range(1, limit + 1):
            nr, nc = origin[0] + dr * step, origin[1] + dc * step
            if not board.is_within_bounds(nr, nc):
                break
            squares.append((nr, nc))
            if board.get_piece_at((nr, nc)) is not None:
                break
        return squares

    def _rule_moves(self, board: Board, piece: Piece) -> List[Move]:
        """Collect the moves the rules in force offer for a piece.

        Args:
            board: The board the move would be played on.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The offered moves, kept whole because a rule's move carries what
            makes it special — a move type, a promotion, a rook travelling with its king.
        """
        offered: List[Move] = []
        for rule in self.active_rules():
            for move in rule.available_moves(board, piece) or ():
                if move is not None:
                    offered.append(move)
        return offered

    def get_valid_moves(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Tuple[int, int]]:
        """Get strictly legal move destinations ensuring the friendly king is safe from check.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List of strictly legal destination squares.
        """
        b = board or self.board
        if b is None:
            return []

        piece = b.get_piece_at(start_pos)
        if piece is None:
            return []

        color = piece.getColor()
        candidates = self.get_candidate_moves(start_pos, b)
        legal_moves: List[Tuple[int, int]] = []
        legal: List[Move] = []

        for candidate in candidates:
            target_pos = candidate.end_pos
            if not self.is_permitted(candidate, b):
                continue

            # Put the move on the board the way it would really happen, and take it off again
            # the same way. Swapping the two squares the move names is not enough: an en
            # passant capture also lifts a piece from a third square, and a castle carries a
            # rook to a fourth. A simulation that left either behind was looking at a
            # position with a blocker fewer than reality, and every pin through that blocker
            # was invisible to it.
            applied = candidate.apply_to_board(b)
            in_check = self.is_check(color, b)
            candidate.unapply_from_board(b, applied)

            if not in_check:
                legal_moves.append(target_pos)
                legal.append(candidate)

        self.legal_candidates = legal
        return legal_moves

    def find_move(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        board: Optional[Board] = None,
    ) -> Optional[Move]:
        """Return the legal move from one square to another, as the rule offered it.

        A caller that learns a move from two clicks needs the move the rule built, not a bare
        pair of squares rebuilt into a fresh `Move`. A rule may attach more than a destination
        to a move — a chain of hops, a piece to promote into, a companion rook — and a rebuilt
        move has none of it, so a capture chain or a promotion silently becomes illegal.

        Args:
            start_pos: (row, col) the move begins at.
            end_pos: (row, col) the move ends at.
            board: Optional Board instance (defaults to self.board).

        Returns:
            Optional[Move]: The move the rules offered, or None when none is legal.
        """
        b = board or self.board
        if b is None or not b.is_within_bounds(*start_pos) or not b.is_within_bounds(*end_pos):
            return None
        for move in self.get_legal_moves_for(start_pos, b):
            if tuple(move.end_pos) == tuple(end_pos):
                return move
        return None

    def get_legal_moves_for(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Move]:
        """Return the legal moves for a piece as whole moves, not just destinations.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List[Move]: The legal moves, each carrying whatever its rule attached.
        """
        self.get_valid_moves(start_pos, board)
        return list(self.legal_candidates)

    def is_permitted(self, move: Move, board: Optional[Board] = None) -> bool:
        """Ask every rule whether this move is allowed.

        Args:
            move: The move being considered.
            board: Optional Board instance (defaults to self.board).

        Returns:
            bool: False when any rule in force forbids it, True otherwise.
        """
        b = board or self.board
        if b is None:
            return True
        return all(rule.permits_move(b, move) for rule in self.active_rules())

    def get_all_valid_moves(self, color: int, board: Optional[Board] = None) -> List[Move]:
        """Compute all strictly legal moves for all pieces belonging to a color.

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            List of all strictly legal Move instances.
        """
        b = board or self.board
        if b is None:
            return []
        all_moves: List[Move] = []
        for r in range(b.rows):
            for c in range(b.cols):
                piece = b.get_piece_at((r, c))
                if piece is not None and piece.getColor() == color:
                    all_moves.extend(self.get_legal_moves_for((r, c), b))
        return all_moves

    def is_valid_move(self, move: Move, board: Optional[Board] = None) -> bool:
        """Verify whether a specific Move is strictly legal.

        Args:
            move: Move instance to evaluate.
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if the move is legal, False otherwise.
        """
        b = board or self.board
        if b is None or not move.validate(b):
            return False
        if not self.is_permitted(move, b):
            return False
        valid_destinations = self.get_valid_moves(move.start_pos, b)
        return move.end_pos in valid_destinations

    def is_checkmate(self, color: int, board: Optional[Board] = None) -> bool:
        """Check if the given player is in checkmate.

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if player is in check with zero legal responses, False otherwise.
        """
        b = board or self.board
        if not self.is_check(color, b):
            return False
        return len(self.get_all_valid_moves(color, b)) == 0

    def is_stalemate(self, color: int, board: Optional[Board] = None) -> bool:
        """Check if the given player is stalemated (not in check, but no legal moves).

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if stalemate condition holds, False otherwise.
        """
        b = board or self.board
        if self.is_check(color, b):
            return False
        return len(self.get_all_valid_moves(color, b)) == 0

    def simulate_move(
        self, move: Optional[Move] = None
    ) -> List[Tuple[Tuple[int, int], Optional[Piece]]]:
        """Simulate move execution and return previous state for rollback.

        Args:
            move: Optional Move instance (defaults to self.move).

        Returns:
            List of ((row, col), previous_piece) tuples for restoration.
        """
        m = move or self.move
        b = self.board
        if m is None or b is None:
            return []
        saved_state = [
            (m.start_pos, b.get_piece_at(m.start_pos)),
            (m.end_pos, b.get_piece_at(m.end_pos)),
        ]
        m.execute(b)
        return saved_state


#: Czech alias for `MoveValidator`, as `PRD.md` section 5 and `RevizorTahu` in the diagram
#: require.
RevizorTahu = MoveValidator
