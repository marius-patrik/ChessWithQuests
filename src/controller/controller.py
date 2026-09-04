from typing import Optional, Tuple, List, Dict, Any

try:
    from model.game.manager import GameManager
    from model.game.move import Move
except ImportError:
    from ..model.game.manager import GameManager
    from ..model.game.move import Move


class GameController:
    def __init__(self, game_manager: Optional[GameManager] = None):
        self.game_manager: GameManager = game_manager or GameManager()
        self.selected_square: Optional[Tuple[int, int]] = None
        self.highlighted_moves: List[Tuple[int, int]] = []

    def select_square(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        piece = self.game_manager.board.get_piece_at(pos)
        if piece is not None and piece.getColor() == self.game_manager.active_player:
            self.selected_square = pos
            self.highlighted_moves = self.game_manager.move_validator.get_valid_moves(
                pos, self.game_manager.board
            )
            return list(self.highlighted_moves)
        self.selected_square = None
        self.highlighted_moves = []
        return []

    def handle_square_click(self, pos: Tuple[int, int]) -> Dict[str, Any]:
        if self.selected_square is None:
            moves = self.select_square(pos)
            return {
                "action": "selected" if self.selected_square else "none",
                "selected": self.selected_square,
                "valid_moves": moves,
            }
        else:
            piece = self.game_manager.board.get_piece_at(pos)
            if piece is not None and piece.getColor() == self.game_manager.active_player:
                moves = self.select_square(pos)
                return {
                    "action": "reselected",
                    "selected": self.selected_square,
                    "valid_moves": moves,
                }

            move = Move(self.selected_square, pos)
            success = self.game_manager.make_move(move)
            prev_selected = self.selected_square
            self.selected_square = None
            self.highlighted_moves = []

            return {
                "action": "moved" if success else "invalid",
                "success": success,
                "from": prev_selected,
                "to": pos,
                "game_state": self.game_manager.get_state(),
            }

    def reset_selection(self) -> None:
        self.selected_square = None
        self.highlighted_moves = []

    def new_game(self) -> None:
        self.game_manager = GameManager()
        self.reset_selection()


Controller = GameController
