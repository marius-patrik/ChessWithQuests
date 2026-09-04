# Rook (`model/pieces/rook.py`)

## Diagram Reference
Maps directly to **`Věž`** in the reference diagram.

## Classes
### `Rook` (Inherits from `Piece`)
Orthogonal ray-marching sliding piece.

#### Characteristics
- `vectors`: `[(0, 1), (0, -1), (1, 0), (-1, 0)]`.
- `attack_vectors`: Same as movement vectors.
- `can_jump`: `False` (sliding piece).
- `name`: `"Rook"`.
- `has_moved`: Boolean flag tracking castling eligibility.
