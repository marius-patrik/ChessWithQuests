# Complete FIDE Chess Rules Reference

This reference document serves as the authoritative rules baseline for ChessWithQuests, ensuring our engine, validator (`MoveValidator`), board model (`Board`), and game manager (`GameManager`) faithfully adhere to standard international chess rules.

---

## 1. Board & Initial Setup
- The game is played on an $8 \times 8$ grid of 64 alternating light and dark squares.
- **Ranks**: Rows numbered 1 through 8 (Rank 1 is the White back rank; Rank 8 is the Black back rank).
- **Files**: Columns lettered `a` through `h` (from White's left to right).
- **Orientation**: The board is placed so that each player has a light square on their bottom-right corner (`h1` for White, `a8` for Black).
- **Initial Placement**:
  - White pieces occupy Rank 1 (Rook on `a1`/`h1`, Knight on `b1`/`g1`, Bishop on `c1`/`f1`, Queen on `d1`, King on `e1`) and Rank 2 (Pawns on `a2`–`h2`).
  - Black pieces occupy Rank 8 (Rook on `a8`/`h8`, Knight on `b8`/`g8`, Bishop on `c8`/`f8`, Queen on `d8`, King on `e8`) and Rank 7 (Pawns on `a7`–`h7`).
  - *"Queen on her color"*: White Queen begins on light square `d1`; Black Queen begins on dark square `d8`.

---

## 2. Standard Piece Movements

### King (K)
- Moves exactly **1 square** in any direction: horizontally, vertically, or diagonally.
- May never move into a square attacked by an enemy piece (moving into check is strictly illegal).
- May not be placed adjacent to the opposing King.

### Queen (Q)
- Moves any number of vacant squares along ranks, files, or diagonals (combines the movement vectors of the Rook and Bishop).
- Cannot leap over intervening pieces.

### Rook (R)
- Moves any number of vacant squares horizontally or vertically along ranks or files.
- Cannot leap over intervening pieces.

### Bishop (B)
- Moves any number of vacant squares along diagonals.
- Each Bishop remains confined throughout the game to squares of its initial color (one light-squared Bishop, one dark-squared Bishop per side).
- Cannot leap over intervening pieces.

### Knight (N / Horse)
- Moves in an **L-shape**: 2 squares along a rank/file and 1 square perpendicularly, or 1 square along a rank/file and 2 squares perpendicularly (8 potential target coordinates).
- **Jumping capability**: The Knight is the only piece permitted to leap over intervening pieces on its path.

### Pawn (P)
- **Normal Advance**: Moves 1 square straight forward along its file if the target square is unoccupied.
- **Initial Two-Square Advance**: From its starting rank (Rank 2 for White, Rank 7 for Black), a pawn may optionally advance 2 squares forward, provided both intermediate and destination squares are vacant.
- **Capture**: Captures 1 square diagonally forward (left or right). A pawn cannot capture directly forward.

---

## 3. Special Moves

### Castling (O-O and O-O-O)
A simultaneous movement of the King and a Rook of the same color along the player's first rank:
- **Kingside (Short) Castling `O-O`**: King moves from `e1` to `g1` (`e8` to `g8`), and the `h`-rook moves to `f1` (`f8`).
- **Queenside (Long) Castling `O-O-O`**: King moves from `e1` to `c1` (`e8` to `c8`), and the `a`-rook moves to `d1` (`d8`).
- **Mandatory Requirements**:
  1. Neither the King nor the chosen Rook has moved earlier in the game.
  2. All squares between the King and the Rook must be empty.
  3. The King is **not** currently in check.
  4. The square the King passes across is **not** attacked by an enemy piece.
  5. The square the King lands upon is **not** attacked by an enemy piece.

### En Passant
- When a pawn advances 2 squares from its starting position and lands directly adjacent horizontally to an enemy pawn on that pawn's 5th rank (for White) or 4th rank (for Black).
- The enemy pawn may capture this advanced pawn "in passing" by moving diagonally forward into the square the advanced pawn just skipped over.
- **Immediate Requirement**: En passant must be claimed immediately on the turn following the two-square advance. If not played on that turn, the right to capture en passant on that pawn is permanently lost.

### Pawn Promotion
- When a pawn reaches the eighth rank (Rank 8 for White, Rank 1 for Black), it is immediately converted to a Queen, Rook, Bishop, or Knight of the same color as chosen by the player.
- Promotion takes effect instantly and is not constrained by whether pieces of that type were previously captured (e.g. multiple Queens are permitted).

---

## 4. Check, Discovered Check & Checkmate

### Check
- A King is in check when it is under direct attack by at least one opposing piece.
- A player whose King is in check must eliminate the check on that turn. A check can be resolved by:
  1. **Moving** the King to an unattacked square.
  2. **Capturing** the checking piece.
  3. **Blocking** (interposing) a friendly piece along the line of attack between the checking piece and the King (blocking is not possible against Knight checks or double checks).

### Discovered Check & Double Check
- **Discovered Check**: Moving a piece unmasks an attack by a friendly piece standing behind it.
- **Double Check**: Moving a piece both delivers check itself and discovers check from another piece. The defending King **must move**, as no single move can capture or block two attackers at once.

### Checkmate
- A position where a King is in check and there are no legal moves available to escape the attack.
- The game terminates immediately and the checking side wins.

---

## 5. Draw Conditions

1. **Stalemate**: The player whose turn it is has no legal moves available and their King is **not** in check. The game ends in an immediate draw.
2. **Insufficient Material**: Neither player possesses material sufficient to checkmate under any legal sequence of moves:
   - King vs. King
   - King and Bishop vs. King
   - King and Knight vs. King
   - King and Bishop vs. King and Bishop (where both Bishops are on the same square color)
3. **Threefold Repetition**: The exact identical board position occurs 3 times with the same player to move, same legal move set, castling rights, and en passant rights.
4. **Fifty-Move Rule**: 50 consecutive full moves (50 by White and 50 by Black) have elapsed without a pawn advance or piece capture.
5. **Mutual Agreement**: Both players agree to a draw.

---

## 6. Time Controls
- A game played under clock control terminates in a loss on time ("flag fall") if a player's remaining time reaches zero, provided the opponent has sufficient material to checkmate. If the opponent lacks mating material, the result is a draw.
