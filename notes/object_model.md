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

### 1. English Translation & Czech Backward-Compatibility Aliases
- **Date**: 2026-09-04
- **Context**: The original diagram and starter repository had Czech class, attribute, and method names (e.g. `HerníPlocha`, `Figurka`, `Tah`, `RevizorTahu`, `vyhozene_figurky_b`, `getSmery`). Per user instruction, all classes, methods, and attributes were translated into idiomatic English (`Board`, `Piece`, `Move`, `MoveValidator`, `captured_white`, `getDirections`), while retaining Czech aliases as properties/methods for backward compatibility.
- **Approval**: User requested "change all czech to english".

### 2. Move Validation Architecture (Lazy Core + Aggregator)
- **Date**: 2026-09-04
- **Context**: Box 34 in the reference diagram raised the question of whether move validation should be precomputed eagerly for all pieces on turn start or computed on-demand upon clicking a specific piece.
- **Resolution**: Implemented on-demand validation (`get_valid_moves(piece, board)`) for user clicks/UI highlights, and an aggregator method (`get_all_valid_moves(player, board)`) on `MoveValidator` for checkmate/stalemate game-state evaluations.
- **Approval**: User agreed in planning discussion.
