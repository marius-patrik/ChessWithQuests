"""Game controller mediating UI user interactions, piece selections, and game flow."""

from typing import Optional, Tuple, List, Dict, Any

try:
    from model.game.manager import GameManager
    from model.game.move import Move
except ImportError:
    from ..model.game.manager import GameManager
    from ..model.game.move import Move


class GameController:
    """Handles board square selections, move executions, and UI dispatch."""

    def __init__(self, game_manager: Optional[GameManager] = None):
        """Initialize a GameController instance.

        Args:
            game_manager: Optional GameManager instance (defaults to new instance).
        """
        self.game_manager: GameManager = game_manager or GameManager()
        self.selected_square: Optional[Tuple[int, int]] = None
        self.highlighted_moves: List[Tuple[int, int]] = []

    def select_square(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Select a piece at the position and calculate its legal destination squares.

        Args:
            pos: (row, col) coordinates to select.

        Returns:
            List of valid destination (row, col) coordinate tuples.
        """
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
        """Process a board square click from the UI layer.

        Args:
            pos: (row, col) coordinates of the clicked square.

        Returns:
            Dictionary describing result action ("selected", "reselected", "moved", "invalid", "none").
        """
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
        """Clear current piece selection and move highlights."""
        self.selected_square = None
        self.highlighted_moves = []

    def new_game(self) -> None:
        """Start a new game session and reset selections."""
        self.game_manager = GameManager()
        self.reset_selection()


Controller = GameController
