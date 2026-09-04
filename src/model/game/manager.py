"""Game manager coordinating board state, turn alternation, clock ticks, and game rules."""

from typing import List, Optional, Any

try:
    from model.game.board import Board
    from model.game.move import Move
    from model.game.player import Player
    from model.game.timer import Timer
    from model.game.logger import GameLogger
    from model.game.validator import MoveValidator
except ImportError:
    from .board import Board
    from .move import Move
    from .player import Player
    from .timer import Timer
    from .logger import GameLogger
    from .validator import MoveValidator


class GameManager:
    """Core game orchestrator managing turns, clocks, moves, and terminal game conditions."""

    STATE_IN_PROGRESS = 0
    STATE_CHECK = 1
    STATE_CHECKMATE = 2
    STATE_STALEMATE = 3
    STATE_TIMEOUT = 4

    def __init__(
        self,
        board: Optional[Board] = None,
        players: Optional[List[Player]] = None,
        timer: Optional[Timer] = None,
        logger: Optional[GameLogger] = None,
        validator: Optional[MoveValidator] = None,
    ):
        """Initialize a GameManager instance.

        Args:
            board: Optional Board instance (defaults to standard 8x8 Board).
            players: Optional list of Player instances (defaults to White and Black players).
            timer: Optional Timer instance (defaults to standard 600s timer).
            logger: Optional GameLogger instance.
            validator: Optional MoveValidator instance.
        """
        self.board: Board = board or Board()
        self.players: List[Player] = players or [Player(1), Player(-1)]
        self.active_player: int = 1
        self.current_move: Optional[Move] = None
        self.timer: Timer = timer or Timer()
        self.game_logger: GameLogger = logger or GameLogger()
        self.move_validator: MoveValidator = validator or MoveValidator(self.board)

    def start_turn(self) -> Optional[Move]:
        """Begin a new turn, clearing any pending move selection.

        Returns:
            Always None indicating no pending move.
        """
        self.current_move = None
        return self.current_move

    def get_valid_moves(self) -> List[Move]:
        """Compute all legal moves available to the active player.

        Returns:
            List of legal Move instances for the active player.
        """
        return self.move_validator.get_all_valid_moves(self.active_player, self.board)

    possible_moves = get_valid_moves

    def cancel_move(self) -> None:
        """Cancel or reset the currently selected move."""
        self.current_move = None

    def save_log(self) -> None:
        """Save the game log (stub implementation)."""
        pass

    def get_state(self) -> int:
        """Evaluate and return the current state of the game.

        Returns:
            Integer state constant: STATE_TIMEOUT, STATE_CHECKMATE,
            STATE_STALEMATE, STATE_CHECK, or STATE_IN_PROGRESS.
        """
        if self.timer.is_expired(self.active_player):
            return self.STATE_TIMEOUT
        if self.move_validator.is_checkmate(self.active_player, self.board):
            return self.STATE_CHECKMATE
        if self.move_validator.is_stalemate(self.active_player, self.board):
            return self.STATE_STALEMATE
        if self.move_validator.is_check(self.active_player, self.board):
            return self.STATE_CHECK
        return self.STATE_IN_PROGRESS

    def make_move(self, move: Move) -> bool:
        """Validate and execute a move, log it, and switch the active player.

        Args:
            move: Move instance to execute.

        Returns:
            True if the move was valid and successfully executed, False otherwise.
        """
        if not self.move_validator.is_valid_move(move, self.board):
            return False
        piece = self.board.get_piece_at(move.start_pos)
        if piece is None or piece.getColor() != self.active_player:
            return False

        success = move.execute(self.board)
        if not success:
            return False

        self.current_move = move
        self.game_logger.log_move(move)
        self.active_player = -1 if self.active_player == 1 else 1
        return True
