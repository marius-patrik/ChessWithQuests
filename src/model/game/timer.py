from typing import List, Union


class Timer:
    def __init__(self, initial_time: int = 600):
        self.initial_time = initial_time
        self.player_times: List[int] = [initial_time, initial_time]

    def _get_player_index(self, player: Union[int, str]) -> int:
        if player == 1 or player == "white":
            return 0
        elif player == -1 or player == "black":
            return 1
        elif player in (0, 1):
            return player
        return 0

    def reset_time(self) -> None:
        self.player_times = [self.initial_time, self.initial_time]

    def tick(self, player: int, elapsed_seconds: int = 1) -> None:
        idx = self._get_player_index(player)
        self.player_times[idx] = max(0, self.player_times[idx] - elapsed_seconds)

    countdown = tick

    def add_time(self, player: int, increment_seconds: int) -> None:
        idx = self._get_player_index(player)
        self.player_times[idx] += increment_seconds

    def get_time(self, player: int) -> int:
        idx = self._get_player_index(player)
        return self.player_times[idx]

    def is_expired(self, player: int) -> bool:
        return self.get_time(player) <= 0
