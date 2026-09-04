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
        self.plocha: Board = board or Board()
        self.hraci: List[Player] = players or [Player(1), Player(-1)]
        self.aktivni_hrac: int = 1
        self.aktualni_tah: Optional[Move] = None
        self.casovac: Timer = timer or Timer()
        self.game_logger: GameLogger = logger or GameLogger()
        self.revizor_tahu: MoveValidator = validator or MoveValidator(self.plocha)

    def zacni_tah(self) -> Optional[Move]:
        self.aktualni_tah = None
        return self.aktualni_tah

    def mozne_tahy(self) -> List[Move]:
        return self.revizor_tahu.get_all_valid_moves(self.aktivni_hrac, self.plocha)

    def zrus_tah(self) -> None:
        self.aktualni_tah = None

    def uloz_log(self) -> None:
        pass

    def get_stav(self) -> int:
        if self.casovac.is_expired(self.aktivni_hrac):
            return self.STATE_TIMEOUT
        if self.revizor_tahu.is_checkmate(self.aktivni_hrac, self.plocha):
            return self.STATE_CHECKMATE
        if self.revizor_tahu.is_stalemate(self.aktivni_hrac, self.plocha):
            return self.STATE_STALEMATE
        if self.revizor_tahu.is_check(self.aktivni_hrac, self.plocha):
            return self.STATE_CHECK
        return self.STATE_IN_PROGRESS

    def make_move(self, move: Move) -> bool:
        if not self.revizor_tahu.is_valid_move(move, self.plocha):
            return False
        piece = self.plocha.get_piece_at(move.start_pos)
        if piece is None or piece.getColor() != self.aktivni_hrac:
            return False

        success = move.execute(self.plocha)
        if not success:
            return False

        self.aktualni_tah = move
        self.game_logger.uloz_tah(move)
        self.aktivni_hrac = -1 if self.aktivni_hrac == 1 else 1
        return True

    # English aliases
    start_turn = zacni_tah
    possible_moves = mozne_tahy
    cancel_move = zrus_tah
    save_log = uloz_log
    get_state = get_stav
