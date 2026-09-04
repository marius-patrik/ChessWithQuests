# King (`model/pieces/king.py`)

## Diagram Reference
Maps directly to **`Král`** in the reference diagram.

## Classes
### `King` (Inherits from `Piece`)
The central piece whose capture defines checkmate.

#### Characteristics
- `vectors`: 8 adjacent coordinates (orthogonal + diagonal).
- `attack_vectors`: Same as movement vectors.
- `can_jump`: `False` (step limited to 1 square).
- `name`: `"King"`.
- `has_moved`: Boolean flag tracking castling eligibility.
