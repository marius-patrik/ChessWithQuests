# Piece Base Class (`model/pieces/piece.py`)

## Diagram Reference
Maps directly to **`Figurka`** in the reference architecture diagram.

## Classes
### `Piece` (Alias: `Figurka`)
Base class for all chess pieces.

#### Attributes
- `__color`: Encapsulated private player color (`1` / `-1` / string).
- `_type`: Piece type descriptor (e.g. `"pawn"`, `"king"`).
- `_vectors`: Movement direction coordinate offsets.
- `_attack_vectors`: Attack direction coordinate offsets.
- `_can_jump`: Boolean indicator if piece leaps over obstacles.
- `_name`: Human-readable piece name.

#### Methods
- `getColor() -> Any` (`getBarva`): Returns color identifier.
- `getType() -> Any` (`getTyp`): Returns type string.
- `getName() -> str`: Returns piece name.
- `getDirections() -> Optional[List[Tuple[int, int]]]` (`getSmery`): Returns move directions.
- `getAttackDirections() -> List[Tuple[int, int]]`: Returns attack directions.
- `canJump() -> bool`: Returns jumping capability.
