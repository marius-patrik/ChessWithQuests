from typing import Optional, Tuple, Dict, Any

try:
    from controller.controller import GameController
except ImportError:
    from .controller import GameController


class WindowController:
    def __init__(
        self,
        game_controller: Optional[GameController] = None,
        title: str = "ChessWithQuests",
        dimensions: Tuple[int, int] = (800, 600),
    ):
        self.game_controller: GameController = game_controller or GameController()
        self.title: str = title
        self.width, self.height = dimensions
        self.is_running: bool = False
        self.status_message: str = "Welcome to ChessWithQuests"
        self.active_dialog: Optional[str] = None

    def start(self) -> None:
        self.is_running = True
        self.status_message = "Game Started"

    def stop(self) -> None:
        self.is_running = False
        self.status_message = "Game Stopped"

    def set_status(self, message: str) -> None:
        self.status_message = message

    def show_dialog(self, message: str) -> None:
        self.active_dialog = message

    def close_dialog(self) -> None:
        self.active_dialog = None

    def on_square_clicked(self, position: Tuple[int, int]) -> Dict[str, Any]:
        result = self.game_controller.handle_square_click(position)
        if result["action"] == "moved":
            self.set_status(f"Move played to {position}")
        elif result["action"] == "selected":
            self.set_status(f"Square selected at {position}")
        elif result["action"] == "invalid":
            self.set_status("Invalid move!")
        return result

    def tick_timer(self) -> None:
        active_color = self.game_controller.game_manager.active_player
        self.game_controller.game_manager.timer.tick(active_color, 1)
        if self.game_controller.game_manager.timer.is_expired(active_color):
            self.set_status("Time Expired!")
