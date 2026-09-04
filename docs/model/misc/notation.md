# Notation Helpers (`model/misc/notation.py`)

Utility functions converting between matrix coordinates `(row, col)` and standard algebraic chess notation (e.g. `(0, 0) <-> "a1"`).

## Functions
- `pos_to_algebraic(position: Tuple[int, int]) -> str`: Converts `(0, 4)` to `"e1"`.
- `algebraic_to_pos(algebraic: str) -> Tuple[int, int]`: Converts `"e4"` to `(3, 4)`.
