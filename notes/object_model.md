# Object Model Reference & Conformance Notes

## Reference Architecture Diagram
The source of truth for the project object model is defined at:
https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D

## Strict Conformance Requirement
The object model in the codebase must strictly match the reference diagram. 
Any structural, behavioral, or naming deviation from this diagram must:
1. Be explicitly proposed to and approved by the user before implementation.
2. Be recorded and documented in this notes file with the rationale, date, and user approval context.

---

## Registered Deviations & Clarifications

### 1. Language and Translation Policy (Not a Deviation)
- **Policy**: Naming and language translations between the Czech reference diagram and the English codebase (e.g. `Figurka` -> `Piece`, `HerníPlocha` -> `Board`, `Tah` -> `Move`, `RevizorTahu` -> `MoveValidator`, `Hra` -> `GameManager`, `Hrac` -> `Player`, `Uzivatel` -> `User`, `vyhozene_figurky` -> `captured_pieces`, `zacni_tah` -> `start_turn`, etc.) are canonical design standards and do NOT constitute architecture or object model deviations.
- **Pure English Standard**: All code, class names, method names, attributes, variables, comments, and docstrings must be written exclusively in English with no Czech identifiers or aliases.
- **Approval**: Explicitly clarified and approved by the user.

### 2. Move Validation Architecture (Lazy Core + Aggregator)
- **Date**: 2026-09-04
- **Context**: Box 34 in the reference diagram raised the question of whether move validation should be precomputed eagerly for all pieces on turn start or computed on-demand upon clicking a specific piece.
- **Resolution**: Implemented on-demand validation (`get_valid_moves(piece, board)`) for user clicks/UI highlights, and an aggregator method (`get_all_valid_moves(player, board)`) on `MoveValidator` for checkmate/stalemate game-state evaluations.
- **Approval**: User agreed in planning discussion.
