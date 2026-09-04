from typing import Dict, Optional
from datetime import datetime


class MetadataWriter:
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self.headers: Dict[str, str] = {
            "Event": "Chess Match",
            "Site": "ChessWithQuests",
            "Date": datetime.now().strftime("%Y.%m.%d"),
            "Round": "1",
            "White": "Player 1",
            "Black": "Player 2",
            "Result": "*",
        }
        if headers:
            self.headers.update(headers)

    def set_header(self, key: str, value: str) -> None:
        self.headers[key] = str(value)

    def get_header(self, key: str, default: str = "") -> str:
        return self.headers.get(key, default)

    def format_pgn_headers(self) -> str:
        return "\n".join([f'[{k} "{v}"]' for k, v in self.headers.items()])

    def export(self) -> Dict[str, str]:
        return dict(self.headers)
