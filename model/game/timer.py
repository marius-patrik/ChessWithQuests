from typing import List, Union


class Timer:
    def __init__(self, initial_time: int = 600):
        self.initial_time = initial_time
        self.cas_hrac: List[int] = [initial_time, initial_time]

    def _get_player_index(self, player: Union[int, str]) -> int:
        if player == 1 or player == "white":
            return 0
        elif player == -1 or player == "black":
            return 1
        elif player in (0, 1):
            return player
        return 0

    def nuluj_cas(self) -> None:
        self.cas_hrac = [self.initial_time, self.initial_time]

    def pocitej_cas(self, hrac: int, elapsed_seconds: int = 1) -> None:
        idx = self._get_player_index(hrac)
        self.cas_hrac[idx] = max(0, self.cas_hrac[idx] - elapsed_seconds)

    def add_time(self, hrac: int, increment_seconds: int) -> None:
        idx = self._get_player_index(hrac)
        self.cas_hrac[idx] += increment_seconds

    def get_time(self, hrac: int) -> int:
        idx = self._get_player_index(hrac)
        return self.cas_hrac[idx]

    def is_expired(self, hrac: int) -> bool:
        return self.get_time(hrac) <= 0

    # English aliases
    reset_time = nuluj_cas
    tick = pocitej_cas
    count_time = pocitej_cas
    player_times = property(lambda self: self.cas_hrac)
