"""Game manager coordinating board state, turn alternation, clock ticks, and game rules.

Nothing here names a piece, a board size or a notation. Which pieces are in play, how large
the board is, which quests exist and which notations can be written are all questions the
configuration answers, and the manager reads those answers rather than carrying defaults of
its own. An engine default is a claim about every game, and a variant that does not share it
gets it anyway.
"""

from datetime import datetime
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
from model.misc.quest_manager import QuestManager
from model.users.manager import UserManager
from model.users.user import User


class UnsupportedExportFormat(ValueError):
    """Raised when a game is asked for a notation its configuration does not export.

    Which notations exist is the configuration's answer, so the engine cannot answer this
    question and must not pretend to. It used to pretend: an unknown format went to a
    hard-coded chess writer, which returned an empty string — indistinguishable from a game
    that genuinely had nothing to say, and silently empty in the transcript.
    """


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

        Attributes:
            opening_position: An independent copy of the position this game was dealt, which
                is what a notation read from a position has to be read against. It is a
                snapshot rather than `self.board`, for the reason `new_game` records and not
                for this one: a board is the position the game is *in*, and a writer that was
                handed it would be reading a game's last move to explain its first.
        """
        self.configuration: Optional[Configuration] = configuration or load_default_configuration()
        self.board: Board = (
            board or (self.configuration.board if self.configuration else None) or Board()
        )
        # Taken here and in `new_game`, and nowhere else: those are the two moments a game is
        # dealt, and between them the board is the position being played rather than the
        # position a game began in. `configuration.new_board()` is deliberately not used — it
        # falls back to returning the board a configuration already holds, which for a
        # configuration that declared no factory is this very board, so asking it during a game
        # would hand a writer the position it is trying to write. A snapshot of the dealt
        # board is the position, and it is taken before a single move is played.
        self.opening_position: Optional[Board] = self.board.snapshot()

        self.players: List[Player] = players or [Player(1), Player(-1)]
        self.active_player: int = 1
        self.current_move: Optional[Move] = None
        self.turn_started: Optional[float] = None
        self.clock = self._configuration_clock()
        self.timer: Timer = timer or getattr(self.clock, "timer", None) or Timer()
        self.game_logger: GameLogger = logger or GameLogger()
        self.move_validator: MoveValidator = validator or MoveValidator(self.board)

        # The subsystems the game drives. A game that plays but keeps no quest progress, no
        # clock credit, no transcript and no player behind the pieces is a board with a
        # counter on it, so all four are held here rather than left for a caller to wire.
        self.users: UserManager = UserManager()
        # The configuration's quests, exactly as it declared them, and no roster the engine
        # made up for it. A configuration that declares no quests has none: falling back to
        # the engine's roster gave a variant quests nobody asked it to play, drawn from a
        # roster that cannot even be built without a piece type it has no way to supply.
        self.quest_manager: QuestManager = QuestManager(
            list(self.configuration.quests) if self.configuration is not None else []
        )
        # The writers the configuration offers, and the first of them for a caller that just
        # wants a notation. There is no writer if the configuration declared none, and
        # `transcript` says so rather than reaching for a chess one.
        self.exporters: List[Any] = list(self.configuration.exporters) if self.configuration else []
        self.notation: Optional[Any] = self.exporters[0] if self.exporters else None
        # The record of who played, when and how the game ended, is the configuration's to
        # supply and the manager's only to carry. It used to build a header here and pass it
        # down, which made the header a thing the engine knew the shape of: the tags it wrote
        # and the tag it updated after every game were a game's own vocabulary, living in a
        # module that is supposed to name no game. A configuration that declares none has
        # none, and a writer that needs one says so rather than being handed a substitute.
        self.metadata: Optional[Any] = self.configuration.metadata if self.configuration else None
        self.started_at: datetime = datetime.now()
        self.move_events: List[MoveEvent] = []
        self.completed_quests: List[Any] = []
        self.result: Optional[Result] = None
        self.elapsed_seconds: int = 0
        self.increment_seconds: int = getattr(self.clock, "increment_seconds", 0)

        self.link_default_users()
        self.start_turn_clock()
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
        # The position the new game begins in is snapshotted here rather than in `__init__`
        # alone, because this is the other moment a game is dealt. It is taken immediately,
        # before anything is played on it: `new_board` returns the configuration's own board
        # when no factory was declared, and for such a configuration that board is the live
        # one — so asking for it *during* a game would hand a writer the position it is
        # trying to write, and the notation would describe a game that was never played.
        self.opening_position = self.board.snapshot()
        self.active_player = 1
        self.current_move = None
        self.result = None
        self.move_events = []
        self.completed_quests = []
        self.elapsed_seconds = 0
        self.started_at = datetime.now()
        self.timer.reset_time()
        self.start_turn_clock()
        self.game_logger = GameLogger()
        self.quest_manager.reset()
        if self.configuration is not None:
            # `reset`, not re-attaching: `attach` is a rule's own chance to seed its state, and
            # a rule that seeds nothing keeps the last game's. Only `reset` clears the dict
            # first, so a new game cannot inherit a castling right already spent, an en passant
            # offer still standing, or a move list nobody asked it to forget. Every shipped rule
            # happens to reseed in `attach`, so nothing tested this until a rule did not.
            self.configuration.reset()
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
        self.elapsed_seconds += self.charge_turn(mover)
        self.credit_increment(mover)
        # Charge the mover for the time their move actually took, then credit the increment
        # their completed move earns. Counting one second per move meant a clock that only ever
        # moved when somebody played, which is not a clock.
        self.charge_turn(mover)

        self.move_events.append(self._describe(move, mover))
        self.quest_manager.observe_move(self.move_events[-1])

        self.active_player = -mover
        for rule in self.move_validator.active_rules():
            rule.active_color = self.active_player
        self.start_turn_clock()
        return True

    def _configuration_clock(self):
        """Return the clock this configuration offers, if it offers one.

        Returns:
            Any: The configuration's first clock, or None when it declares none. The engine
            must not invent one: what a game's clocks are is the configuration's decision.
        """
        if self.configuration is None:
            return None
        clocks = list(getattr(self.configuration, "clocks", None) or [])
        return clocks[0] if clocks else None

    def start_turn_clock(self, monotonic: Optional[float] = None) -> None:
        """Begin charging the player to move for the time they spend.

        Args:
            monotonic: A monotonic clock reading, in seconds. Defaults to `time.monotonic`.

        Returns:
            None
        """
        import time

        self.turn_started = monotonic if monotonic is not None else time.monotonic()

    def charge_turn(self, color: Optional[int] = None, monotonic: Optional[float] = None) -> int:
        """Charge the active player for the time their turn has lasted, and end that turn.

        Args:
            color: The player to charge. Defaults to the player whose turn it is.
            monotonic: A monotonic clock reading, in seconds. Defaults to `time.monotonic`.

        Returns:
            int: The whole seconds charged, which is zero for a turn shorter than a second or
            a game that has not begun.
        """
        import time

        if self.turn_started is None:
            return 0
        now = monotonic if monotonic is not None else time.monotonic()
        elapsed = now - self.turn_started
        # Carry the remainder rather than discarding it. Rounding each call to whole seconds
        # loses up to a second per call, so a clock asked four times a second fell roughly four
        # times slower than real time. The turn is still *ended* — a move charges it once and
        # hands the turn on — but asking mid-turn must not throw away what has accrued.
        whole = int(elapsed)
        # Keep the fraction that has not been charged yet, by moving the start forward by only
        # what was charged. Rounding each call to whole seconds and restarting from now lost up
        # to a second per call, so a clock asked four times a second fell about four times
        # slower than real time.
        self.turn_started = now - (elapsed - whole)
        if whole > 0:
            self.timer.tick(color if color is not None else self.active_player, whole)
        return whole

    def credit_increment(self, color: int) -> None:
        """Add the increment a player earns by completing a move.

        Args:
            color: The player who moved.

        Returns:
            None
        """
        if self.increment_seconds:
            self.timer.add_time(color, self.increment_seconds)

    def _describe(self, move: Move, mover: int) -> MoveEvent:
        """Build the event the quests judge a move by.

        Args:
            move: The move that was played.
            mover: The colour that played it.

        Returns:
            MoveEvent: What happened, as the quests want to hear it.
        """
        # Both come off the Move, which recorded them while the board still held the position
        # before the move. Reading the board here would read the position after it, where the
        # destination holds the piece that just arrived and every move looks like a capture.
        piece = move.piece
        # A move that chains several captures carries them all, and a quest counting captures
        # must count each one. Reading the single `captured_piece` scored a three-jump
        # draughts capture as one.
        taken = getattr(move, "captured_pieces", None)
        if taken is None:
            taken = [move.captured_piece] if move.captured_piece is not None else []
        captured = taken[0] if taken else None
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

    def offered_formats(self) -> List[str]:
        """Return every notation this configuration can write a game in.

        Returns:
            List[str]: The format names the configuration's writers declare, in declaration
            order and without repeats.
        """
        offered: List[str] = []
        for writer in self.exporters:
            for name in writer.formats():
                if name not in offered:
                    offered.append(name)
        return offered

    def default_format(self) -> Optional[str]:
        """Return the notation a game is written in when nothing is asked for.

        Returns:
            Optional[str]: The first format the configuration offers, or None when it offers
            none. There is no fallback: the engine does not know a single notation name, so
            it has nothing to fall back to.
        """
        offered = self.offered_formats()
        return offered[0] if offered else None

    def writer_for(self, fmt: Optional[str] = None) -> Any:
        """Return the writer that produces a notation.

        The writers are asked in declaration order and each is judged by what it says it
        writes, rather than the first writer being handed every format and expected to cope.
        A configuration whose second writer writes a format its first does not now reaches
        that writer.

        Every writer is handed the same things: the moves, the board, the position the game
        began in, the configuration's metadata record if it declared one, both players, the
        result and the date the game began. Which of those a notation needs, and what it calls
        them, is the writer's answer — the engine passes the game and names no tag. The opening
        position is among them because a notation cannot work it out from the board: a question
        about the position the moves were played in needs that position, and the board handed
        over is the one the game ended in.

        Args:
            fmt: The notation wanted, matched without regard to case. Defaults to the first
                the configuration offers.

        Returns:
            Any: The writer that writes that notation.

        Raises:
            UnsupportedExportFormat: If no writer the configuration offered writes it. An
                unknown notation is a question nothing can answer, and answering it with an
                empty transcript said otherwise.
        """
        wanted = (fmt if fmt is not None else self.default_format() or "").strip().lower()
        for writer in self.exporters:
            if wanted in {str(name).strip().lower() for name in writer.formats()}:
                return writer
        offered = self.offered_formats()
        configuration = self.configuration.name if self.configuration is not None else "this game"
        raise UnsupportedExportFormat(
            f"{fmt!r} is not a notation {configuration} exports; it offers "
            f"{', '.join(offered) if offered else 'no notation at all'}"
        )

    def transcript(self, fmt: Optional[str] = None) -> str:
        """Render the game so far in a notation this configuration exports.

        Args:
            fmt: The notation to write. Defaults to the first the configuration offers.

        Returns:
            str: The game as that notation writes it.

        Raises:
            UnsupportedExportFormat: If the configuration exports no such notation.
        """
        writer = self.writer_for(fmt)
        wanted = fmt if fmt is not None else self.default_format()
        moves = [event.move for event in self.move_events]
        # The game, described: what was played, who was playing, how it ended and when it
        # started. A writer decides what of that its notation records and how — which tags
        # exist, what they are called and what they are set to is a writer's business, and
        # the manager's is to hand over what actually happened rather than to write it down.
        # Whose turn it is is handed over for the same reason: a record of a position says
        # who is to move, and the writer cannot know it from the board. So is the position the
        # game began in, for the same reason and one step further: a notation read from a
        # position is read against that position, and the board is where the game ended.
        #
        # A copy, every time, because a writer that reads a position replays the game on it:
        # that is how a question about the position a move was played in is answered at all.
        # The manager's own snapshot is the record of where the game began and is never played
        # on, so a second transcript does not begin where the first one ended — which is what
        # handing the same snapshot to every writer would have made it do.
        return writer.export(
            wanted,
            moves=moves,
            board=self.board,
            metadata=self.metadata,
            players=list(self.players),
            result=self.result,
            date=self.started_at,
            active_color=self.active_player,
            opening_position=(
                self.opening_position.snapshot() if self.opening_position is not None else None
            ),
        )

    def save_log(self, path: Optional[str] = None) -> str:
        """Write the transcript of this game to a file.

        Args:
            path: Where to write it. Defaults to a timestamped file under `logs/`, named for
                the notation it is written in.

        Returns:
            str: The path written to.

        Raises:
            UnsupportedExportFormat: If the configuration exports no notation, so there is
                nothing to write and nothing to name the file after.
        """
        import os

        wanted = self.default_format()
        if not wanted:
            raise UnsupportedExportFormat("this game exports no notation, so it cannot be saved")
        moves = len(self.game_logger.get_moves())
        directory = path or os.path.join("logs", f"game-{moves}.{wanted.lower()}")
        parent = os.path.dirname(directory)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(directory, "w", encoding="utf-8") as handle:
            handle.write(self.transcript(wanted))
        return directory
