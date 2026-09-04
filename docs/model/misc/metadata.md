# MetadataWriter (`model/misc/metadata.py`)

## Diagram Reference
Maps directly to **`MetadataWriter`** in the reference diagram.

## Classes
### `MetadataWriter`
Stores and formats PGN standard seven-tag-roster metadata (`Event`, `Site`, `Date`, `Round`, `White`, `Black`, `Result`).

#### Methods
- `set_header(key: str, value: str) -> None`: Sets tag value.
- `get_header(key: str, default: str = "") -> str`: Reads tag value.
- `format_pgn_headers() -> str`: Emits standard bracketed header lines.
- `export() -> Dict[str, str]`: Returns dictionary of metadata tags.
