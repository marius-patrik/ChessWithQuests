# Queen (`model/pieces/queen.py`)

## Diagram Reference
Maps directly to **`Dáma`** in the reference diagram.

## Classes
### `Queen` (Inherits from `Piece`)
Most powerful piece, combining orthogonal and diagonal ray-marching.

#### Characteristics
- `vectors`: All 8 directions (Rook + Bishop vectors).
- `attack_vectors`: Same as movement vectors.
- `can_jump`: `False` (sliding piece).
- `name`: `"Queen"`.
