# Horse / Knight (`model/pieces/horse.py`)

## Diagram Reference
Maps directly to **`Kůň`** in the reference diagram.

## Classes
### `Horse` (Alias: `Knight`, Inherits from `Piece`)
Implements L-shaped jumping rules.

#### Characteristics
- `vectors`: 8 L-shape coordinates (`(1, 2)`, `(2, 1)`, `(-1, -2)`, etc.).
- `attack_vectors`: Same as movement vectors.
- `can_jump`: `True` (jumps over intervening pieces).
- `name`: `"Horse"`.
