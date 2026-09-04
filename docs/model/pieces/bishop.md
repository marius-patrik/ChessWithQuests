# Bishop (`model/pieces/bishop.py`)

## Diagram Reference
Maps directly to **`Střelec`** in the reference diagram.

## Classes
### `Bishop` (Inherits from `Piece`)
Implements diagonal movement rules.

#### Characteristics
- `vectors`: `[(1, 1), (1, -1), (-1, 1), (-1, -1)]`
- `attack_vectors`: Same as movement vectors.
- `can_jump`: `False` (ray-marching sliding piece).
- `name`: `"Bishop"`.
