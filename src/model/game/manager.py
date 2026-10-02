"""Game manager coordinating board state, turn alternation, clock ticks, and game rules."""

from typing import Any, List, Optional

from model.game.board import Board
from model.game.configuration import Configuration, load_default_configuration
from model.game.events import MoveEvent, ResultEvent
from model.game.move import Move
from model.game.player import Player
from model.game.rule import Result
from model.game.timer import Timer
from model.game.logger import GameLogger
from model.game.validator import MoveValidator
from model.game.quests import build_quests
from model.misc.export_writers import ChessNotationWriter
from model.misc.metadata import MetadataWriter
from model.misc.quest_manager import QuestManager
from model.users.manager import UserManager
from model.users.user import User


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
        configuration: Optional[Configuration] = None,
    ):
        """Initialize a GameManager instance.

        Args:
            board: Optional Board instance. A configuration's board wins over this.
            players: Optional list of Player instances (defaults to White and Black players).
            timer: Optional Timer instance (defaults to standard 600s timer).
            logger: Optional GameLogger instance.
            validator: Optional MoveValidator instance.
            configuration: Optional configuration to play. Its board and its rules in force
                are what the game runs on. When none is given the shipped default
                configuration is loaded, so a manager with no arguments plays the default
                game rather than an empty rectangle.
        """
        self.configuration: Optional[Configuration] = configuration or load_default_configuration()
        self.board: Board = (
            board or (self.configuration.board if self.configuration else None) or Board()
        )
        self.players: List[Player] = players or [Player(1), Player(-1)]
        self.active_player: int = 1
        self.current_move: Optional[Move] = None
        self.timer: Timer = timer or Timer()
        self.game_logger: GameLogger = logger or GameLogger()
        self.move_validator: MoveValidator = validator or MoveValidator(self.board)

        # The subsystems the game drives. A game that plays but keeps no quest progress, no
        # clock credit, no transcript and no player behind the pieces is a board with a
        # counter on it, so all four are held here rather than left for a caller to wire.
        self.users: UserManager = UserManager()
        self.quest_manager: QuestManager = QuestManager(build_quests())
        self.notation: ChessNotationWriter = ChessNotationWriter()
        self.metadata: MetadataWriter = MetadataWriter()
        self.move_events: List[MoveEvent] = []
        self.completed_quests: List[Any] = []
        self.result: Optional[Result] = None
        self.elapsed_seconds: int = 0
        self.increment_seconds: int = 0

        self.link_default_users()
        if self.configuration is not None:
            self.move_validator.set_rules(
                self.configuration.enabled_rules(),
                clock=self.timer,
                active_color=self.active_player,
            )

    def link_default_users(self) -> None:
        """Give each side a user, so a player is a person and not a colour.

        Returns:
            None
        """
        if len(self.players) < 2:
            return
        for index, (username, colour) in enumerate((("white", 1), ("black", -1))):
            player = self.players[index] if index < len(self.players) else None
            if player is None:
                continue
            user = player.getUser() or User(username=username, name=username.capitalize())
            player.setUser(user)
            user_id = self.users.register_user(user)
            self.users.link_player(user_id, player)

    def new_game(self) -> None:
        """Return every subsystem to its starting state and deal a fresh board.

        Returns:
            None
        """
        if self.configuration is not None:
            self.board = self.configuration.new_board()
        self.active_player = 1
        self.current_move = None
        self.result = None
        self.move_events = []
        self.completed_quests = []
        self.elapsed_seconds = 0
        self.timer.reset_time()
        self.game_logger = GameLogger()
        self.quest_manager.reset()
        if self.configuration is not None:
            self.move_validator.set_rules(
                self.configuration.enabled_rules(),
                clock=self.timer,
                active_color=self.active_player,
            )

    def get_result(self) -> Optional[Result]:
        """Ask the rules in force whether the game is over.

        Returns:
            Optional[Result]: The outcome that wins, or None when the game continues.
        """
        for rule in self.move_validator.active_rules():
            rule.active_color = self.active_player
        return self.move_validator.resolve_outcome(self.board)

    def status(self) -> Optional[str]:
        """Ask the rules in force whether they have something worth showing.

        Returns:
            Optional[str]: The first thing a rule reports, or None.
        """
        return self.move_validator.status(self.board)

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

        mover = self.active_player
        self.current_move = move
        self.game_logger.log_move(move)
        self.move_validator.notify_move_made(move, self.board)
        self.elapsed_seconds += 1
        self.timer.tick(mover, 1)
        self.timer.add_time(mover, self.increment_seconds)

        self.move_events.append(self._describe(move, mover))
        self.quest_manager.observe_move(self.move_events[-1])

        self.active_player = -mover
        for rule in self.move_validator.active_rules():
            rule.active_color = self.active_player
        return True

    def _describe(self, move: Move, mover: int) -> MoveEvent:
        """Build the event the quests judge a move by.

        Args:
            move: The move that was played.
            mover: The colour that played it.

        Returns:
            MoveEvent: What happened, as the quests want to hear it.
        """
        piece = move.piece or self.board.get_piece_at(move.start_pos)
        captured = move.captured_piece or self.board.get_piece_at(move.end_pos)
        return MoveEvent(
            move=move,
            position=self.board,
            color=mover,
            piece_type=piece.getType() if piece is not None else "",
            captured_piece_type=captured.getType() if captured is not None else None,
            is_check=self.move_validator.is_check(-mover, self.board),
            in_check=self.move_validator.is_check(mover, self.board),
            is_castling=move.move_type == "castling",
            is_en_passant=move.move_type == "en_passant",
            is_promotion=move.promotion_piece is not None,
            index=len(self.move_events),
        )

    def finish_game(self) -> Optional[Result]:
        """Close the game, judge the quests that judge a finished game, and credit the users.

        Returns:
            Optional[Result]: The result, or None while the game is still going.
        """
        if self.result is not None:
            return self.result
        self.result = self.get_result()
        if self.result is None:
            return None

        event = ResultEvent(
            outcome=self.result.kind,
            winner=self.result.winner,
            reason=self.result.reason,
            history=list(self.move_events),
            position=self.board,
            players={player.getColor(): player for player in self.players},
        )
        self.quest_manager.observe_result(event)

        for quest in self.quest_manager.get_completed_quests():
            if quest in self.completed_quests:
                continue
            self.completed_quests.append(quest)
            for player in self.players:
                user = player.getUser()
                if user is not None:
                    user.add_quest(quest)
        return self.result

    def transcript(self, fmt: str = "PGN") -> str:
        """Render the game so far in a notation this configuration exports.

        Args:
            fmt: One of `PGN`, `FEN` or `Stenographic`.

        Returns:
            str: The game as that notation writes it.
        """
        moves = [event.move for event in self.move_events]
        self.metadata.set_header("Result", self.result.reason if self.result else "*")
        return self.notation.export(fmt, moves=moves, board=self.board, metadata=self.metadata)

    def save_log(self, path: Optional[str] = None) -> str:
        """Write the transcript of this game to a file.

        Args:
            path: Where to write it. Defaults to a timestamped file under `logs/`.

        Returns:
            str: The path written to.
        """
        import os

        moves = len(self.game_logger.get_moves())
        directory = path or os.path.join("logs", f"game-{moves}.pgn")
        parent = os.path.dirname(directory)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(directory, "w", encoding="utf-8") as handle:
            handle.write(self.transcript())
        return directory
