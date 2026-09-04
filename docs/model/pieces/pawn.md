# Pawn (`model/pieces/pawn.py`)

## Diagram Reference
Maps directly to **`Pěšák`** in the reference diagram.

## Classes
### `Pawn` (Inherits from `Piece`)
Forward-stepping piece with asymmetric diagonal attack vectors.

#### Characteristics
- `vectors`: `[(1 * color, 0)]` (White moves `+1`, Black moves `-1`).
- `attack_vectors`: `[(1 * color, 1), (1 * color, -1)]`.
- `initial_vectors`: `[(2 * color, 0)]` on first move.
- `can_jump`: `False`.
- `name`: `"Pawn"`.
