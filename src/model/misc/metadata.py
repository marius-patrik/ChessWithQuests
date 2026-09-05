"""PGN metadata generation and header management for chess matches."""

from typing import Dict, Optional
from datetime import datetime


class MetadataWriter:
    """Manages seven-tag roster and custom PGN metadata key-value pairs."""

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """Initialize a MetadataWriter instance.

        Args:
            headers: Optional dictionary of metadata headers to override defaults.
        """
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
        """Set or update a metadata header tag.

        Args:
            key: Header tag name (e.g. "White", "Round").
            value: Tag string value.
        """
        self.headers[key] = str(value)

    def get_header(self, key: str, default: str = "") -> str:
        """Retrieve a metadata header tag value.

        Args:
            key: Header tag name.
            default: Fallback string if key is absent.

        Returns:
            Header tag value string.
        """
        return self.headers.get(key, default)

    def format_pgn_headers(self) -> str:
        """Format headers as standard PGN tag pairs: [Tag "Value"].

        Returns:
            Multiline string of bracketed PGN tag pairs.
        """
        return "\n".join([f'[{k} "{v}"]' for k, v in self.headers.items()])

    def export(self) -> Dict[str, str]:
        """Export all current metadata headers.

        Returns:
            Dictionary copy of all header pairs.
        """
        return dict(self.headers)
