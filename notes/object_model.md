# Object Model Reference & Conformance Notes

The governing object model is the reference architecture diagram. Deviations from
it are recorded here with their rationale and approval context, as Rule 3
requires.

## Reference Architecture Diagram

https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D

- **File**: `Šachy - diagram tříd.drawio`
- **Pages**: `Page-1` — the full object model, and `MVC - GameView` — the MVC integration and view bindings.

**Status of this diagram**: it is the assignment specification. Anything it
defines is implemented; anything it does not define is out of scope unless a
user request adds it.

---

## Registered Deviations

### 1. Language and Translation Policy

- **Not a deviation.** Naming and language translation between the Czech diagram
  and the English codebase — `Figurka` → `Piece`, `HerníPlocha` → `Board`,
  `Tah` → `Move`, `RevizorTahu` → `MoveValidator`, `Hrac` → `Player`,
  `Uzivatel` → `User`, `vyhozene_figurky` → `captured_pieces`,
  `zacni_tah` → `start_turn` and the rest — are canonical design standards and
  do not constitute architecture or object model deviations.
- **English is canonical.** All code, class names, method names, attributes,
  variables, comments and docstrings are written in English.
- **Czech aliases are required, not merely permitted.** The classes the
  diagram names in Czech additionally expose a Czech alias bound to the same
  object, so the diagram-to-code mapping is discoverable from the source and
  the generated documentation. Aliases use ASCII spellings without diacritics.
  Comments, docstrings, commit messages and documentation remain English.
- **All fifteen exist.** `PRD.md` section 5 holds the authoritative fifteen-row
  table, and section 19 carries it with the module each alias lives in, checked
  against the code by `tests/test_aliases.py`.
- **Approval**: recorded with user approval, and re-approved for the alias
  allowance on 2026-10-02.

### 2. Move Validation Architecture — Lazy Core and Aggregator

- **Date**: 2026-09-04
- **Context**: Box 34 raised whether move validation should be precomputed for
  every piece at turn start, or computed on demand when a piece is clicked.
- **Resolution**: on-demand validation (`get_valid_moves(piece, board)`) for
  clicks and UI highlights, plus an aggregator (`get_all_valid_moves(player,
  board)`) on `MoveValidator` for checkmate and stalemate evaluation.
- **Approval**: recorded with user approval, 2026-09-04.

### 3. Settings Layer

- **Date**: 2026-10-02
- **Context**: the diagram defines no settings layer. `GUI_mockup.svg` requires a
  SETTINGS tab and states *"No SettingsView or SettingsController"* and *"No
  Settings model/controller/view exists yet."*
- **Deviation**: a settings surface is added to the view layer. **The classes are
  named below, and they are not the two names the mockup uses.**
- **What was actually built, corrected 2026-10-04.** An earlier version of this
  section named `SettingsView`, `SettingsController` and a settings model.
  **Neither `SettingsView` nor `SettingsController` exists, and there is no
  settings model class.** `rg 'class ' view/` returns exactly eight classes:

  | Class | File | What it is |
  |---|---|---|
  | `SettingsDialog` | `view/settings_dialog.py` | the settings form: `SECTIONS`, the corner selector, the five sections, one renderer |
  | `CodeEditor` | `view/code_editor.py` | the editor for rule and quest source |
  | `StartModal` | `view/start_modal.py` | the modal that offers a configuration, Settings and Start |
  | `QuestCard` | `view/quest_view.py` | one quest's progress and reward |
  | `QuestList` | `view/quest_view.py` | the quest panel |
  | `BoardView` | `view/game_view.py` | the drawn board |
  | `PlayerGameView` | `view/player_game_view.py` | the window a game is played in |
  | `PlayerView` | `view/player_view.py` | one player's panel |

  The mockup's two names were its own placeholders — it says they do not exist —
  and they are not reproduced. The surface is a **dialog**, not a view and a
  controller: it holds no game state and calls nothing on the controller except
  through the manager it is handed. What plays the part of the "settings model"
  is the declaration side of `notes/object_model.md` §9 — `Field`, plus
  `Board.value_fields()`, `Piece.value_fields()`, `Rule.value_fields()`,
  `Quest.parameters()` and `model/game/clock_fields.py` — which is data the
  renderer consumes, not a class.
- **Rationale**: the board, pieces, rules, quests and clocks must be
  configurable, and rule logic must be authored. Without a settings layer none
  of that is reachable, and the mockup's configuration surface — the product's
  primary purpose — cannot be delivered.
- **Mitigation**: the settings surface is a thin adapter over the model. It
  holds no game state and adds no rules, so the deviation is additive and does not
  alter the object model the diagram defines.
- **Approval**: recorded with explicit user approval, 2026-10-02. The correction
  to the class names above is a documentation correction, 2026-10-04; it changes
  no code and needs no new approval.

### 4. Rule, Quest, and the Configuration Concept

- **Date**: 2026-10-02
- **Context**: the diagram draws `RevizorTahu` as a fixed class with four
  operations and no configuration surface, and draws `Quest` with `nazev`,
  `popis` and `validate() : bool` but no condition and no parameters. Neither
  has anywhere to record which rules are in force, at what values, with what
  board, pieces, quests or clocks.
- **Deviation**, four things the diagram does not draw:
  - `Rule` — a parent class carrying a configured `value` and per-game `state`,
    with five hooks: `permits_move`, `available_moves`, `outcome`,
    `on_move_made`, `status`, each defaulting permissively. Concrete rules are
    its subclasses.
  - `Quest` — a parent class with subclasses for the built-in quests, declaring
    `when`, `parameters()`, `progress()`, and `validate() -> bool`.
  - A configuration — a named, persisted bundle of board, pieces, rules, quests
    and clocks. `chess` is the default; `checkers` is the second.
  - `ExportWriter` subclasses, one per format, per configuration.
- **Why this is mild rather than foreign**: the diagram already uses this idiom.
  It contains a generalization edge `Kůň → Figurka`, with `Figurka` drawn as the
  parent carrying `název`, `vektory`, `vektory_utoku` and `barva`. One parent
  class per concept with concrete variants as subclasses is the diagram's own
  design, and the generalization is applied to rules and quests.
  - *Recorded for honesty*: the sketch is internally inconsistent. Only `Kůň` is
    explicitly connected to `Figurka`; the other five pieces are siblings that
    each redeclare `vektor`, `vektor_utoku` and `skok` rather than inheriting.
    The intent is unambiguous even though the drawing is not.
- **`Quest.validate() -> bool` matches the drawing exactly**, because quest logic
  lives in the `Quest` subclass rather than in a separate condition object, which
  would have forced the signature to change. There is no condition class.
- **Why the rule hooks are complete for game logic**: in a turn-based game, logic
  can only forbid a move or end the game. `permits_move` and `available_moves`
  cover the first, `outcome` the second, and `on_move_made` the bookkeeping the
  other two depend on. Chess rules, checkers rules, and logic well beyond both
  all map onto these. `status` is display, not logic: it reports something worth
  showing, such as `Check`, while the game continues.
- **Mitigation**: `RevizorTahu` is retained and *asks* the active rule set rather
  than embedding rule logic, so the drawn class and its role survive. Under the
  default configuration the game behaves as the drawn model describes.
  Its drawn operations map onto the new mechanism as follows: `simulate_Move()`
  is satisfied by `Rule.available_moves`, `check_Šach()` and `check_Mat` and
  `check_Pat` are outcomes proposed through `Rule.outcome`. **See FR-61**, which
  is the requirement that preserves the validator's four drawn operations.
  *Corrected 2026-10-04: this sentence cited FR-60, which is the requirement for
  `Uzivatel` and `User Manager` and has nothing to do with the validator. It is
  the same off-by-one class of error that `PRD.md` §7.10 had and that was corrected
  there on the same pass; every other FR reference in this file has been checked
  against `PRD.md` §7 and §7.11 and resolves correctly.*
- **Correction to an earlier claim in this file**: a previous version asserted
  that the four drawn operations were retained *unchanged*, and that one class per
  export format extends a base in the manner of the diagram's `Extends` relation.
  **Neither is true of the diagram.** `Extends` is a legend label on a
  free-standing line beside the piece row, not a relationship, and no edge in the
  file connects any writer to any other writer or to the `export writers` box.
  `ChessNotationWriter` has zero edges. The base-class-plus-subclasses shape is a
  legitimate inference from the diagram's generalisation idiom, but it is **not**
  something the diagram draws, so it is registered as section 7 rather than
  claimed as conformance.
- **Deliberately not added**: a registration function such as `define_ruleset`, a
  rule registry, or `CustomBoard` / `CustomPiece` / `CustomQuest` types. A
  configuration is composed explicitly, so the set of rule types is closed and
  greppable, and a new rule is a new file plus one reference. The `Custom*` types
  would wrap data that is *already* custom — board dimensions and piece vectors
  are data, and new behaviour is expressed by a `Rule` subclass.
- **Fallback**, recorded so the trade-off stays visible: if a stricter reading is
  preferred, the same values can be held as plain data attributes on
  `GameManager` with no new classes, at the cost of the `Rule` and `Quest`
  hierarchies.
- **Approval**: recorded with explicit user approval, 2026-10-02, most explicitly
  *"we should generalize the configuration pattern across the whole engine"* and
  *"drop the conditions for quests"*.

### 5. Configurations Live Outside the Package

- **Date**: 2026-10-02
- **Context**: the diagram describes classes and their members. It does not say
  where concrete implementations live, and it draws each game concept as its own
  class rather than as a bundle.
- **Deviation**: concrete implementations are grouped into configuration
  directories under `games/` — `games/chess/` and `games/checkers/` — each
  holding `board.py`, `pieces/`, `rules/`, `quests/`, `clocks/` and `export/`.
  The engine retains only the parent classes and the shared machinery.
- **Rationale**: it makes a configuration a copyable unit, so duplication is the
  extension mechanism, and it keeps the diagram's classes findable — one parent
  per concept, with variants beside it rather than scattered through the engine.
- **Mitigation**: the engine's public surface is unchanged in substance.
  `Figurka` is still the parent of the six pieces; only the location of the
  subclasses moves, and a configuration is importable by path, so nothing about
  how a piece is used changes.
- **Consequence recorded**: a configuration is a bundle, so the diagram's classes
  are not one-to-one with directories. The mapping is documented in `PRD.md`
  section 6.
- **Approval**: recorded with explicit user approval, 2026-10-02.

### 6. Piece Symbols and the Absence of a Special King

- **Clarification, not a deviation.**
- **Question**: should the engine hold a table mapping piece types to display
  characters and to FEN letters, and should it treat a "king" as a special piece
  type?
- **Assessment**: neither is required, and both would contradict the diagram's
  own generalisation.
  - **Symbols are data.** Every piece declares its own white and black unicode
    glyphs, so the renderer and the notation writer hold no knowledge of piece
    types at all. This also removes the behaviour where an unrecognised type
    silently serialised as a pawn.
  - **FEN characters are optional data.** A piece declares an FEN character or it
    has no FEN representation. Whether a position has a king is a *rule* — a
    configuration that has kings includes the check and checkmate rules — not a
    lookup by type name.
- **Why this is not a deviation**: `Figurka` carries `název` and colour as
  attributes, so declaring display symbols alongside them extends an attribute
  list rather than introducing a structural relationship. The engine removing
  its own `getType() == "king"` coupling is the diagram's inheritance being used
  rather than bypassed.
- **Approval**: recorded with explicit user approval, 2026-10-02 — *"for pieces we should use
  unicode icons declared with the rest of the data"* — and the checkers
  requirement, which cannot be built while a king is hard-coded.
- **Implemented on the FEN side, 2026-10-03.** The glyph half was already done
  and this section already claimed it removed the pawn fallback; it had not. The
  writer still carried `PIECE_CHARS = {"king": "k", ...}` and still wrote
  `PIECE_CHARS.get(ptype, "p")`, so the sentence above was true of the renderer
  and false of the writer. `ChessNotationWriter` now asks the piece —
  `piece.getFen()` — and raises `ValueError` when a piece declares no character.
  An undeclared piece has no place in a position record, and the record is no
  longer willing to call it a pawn. **No deviation**: this is this section's
  decision being carried out, and the recorded approval covers it.

---

## Non-Deviations Worth Stating

Recorded because the question is fair and the answer is not obvious.

- **Data-driven configuration needs no deviation.** Board dimensions, piece
  movement vectors, jump capability, clock values, rule values and quest
  parameters are all *fields* the diagram already draws: `HerníPlocha` holds the
  board, `Figurka` holds `vektory` and `vektory_utoku`, `Timer` holds the clock,
  `RevizorTahu` holds the validator. Only behaviour that cannot be expressed as a
  field needed a new abstraction, and that is section 4.
- **Special moves ride the ordinary move path.** `Tah` carries
  `typ tahu: string`, a move-type field the diagram draws. Castling, en passant
  and promotion are therefore move types generated and validated like any other,
  not branches in the validator.
- **FEN and PGN belong to chess, not the engine.** The diagram's export writers
  box enumerates the formats, so all are implemented — but FEN and PGN are
  chess formats and live in `games/chess/export/`. A game with no FEN
  representation has no FEN exporter, because the structure says so rather than
  a runtime capability check deciding.
- **A repetition key cannot see a capture in passing.** The rulebook counts two positions as
  the same only when the same moves are available to every piece, and a pawn that has just
  advanced two squares hands the opponent a capture that the same placement without it does
  not. This configuration keeps no en passant target on the board for `position_key` to read —
  the offer lives in `EnPassantRule`'s state — so the key covers the placement, the side to
  move and the castling rights, and not the offer. Reaching the same placement a second time
  *with* a live offer needs a pawn to arrive on that square twice by two different routes,
  which no line of play produces, so nothing measurable is lost. Recorded 2026-10-04; the
  honest fix is for the en passant offer to live on the board, which is a change to that rule
  and not a key.
- **`SurviveWithoutCapture` asks for quiet moves, not for moves that cost you nothing.**
  Its description read "Play the required number of moves without losing a piece",
  while `observe_move` counts a move only when `not event.is_capture` — that is, when the
  player captured nothing. The two readings are different games: a player cannot lose a
  piece on their own move, so the description's reading makes this quest a copy of
  `SurvivePlies`, which already exists. The class name, the `Untouchable` display name and
  the long-standing test all say quiet moves, so the description was the record that was
  wrong, and it was corrected on 2026-10-04. **The behaviour was not changed**: choosing
  between the two readings is a product decision, and if the intent really is "survive
  untouched" then `SurvivePlies` should be dropped instead. Recorded here rather than
  settled in code, and open for the maintainer to rule on.

- **Experience is derived, not stored.** The mockup shows quests carrying an XP
  reward, but `reward_points` appears on neither the diagram's `Quest` nor
  `Uzivatel`. `Uzivatel.splnene_kwesty: List(Kwest)` already holds the completed
  quests, so total experience is the sum of their rewards and `Uzivatel` gains no
  new field.

### 7. Export Base Class and Per-Format Subclasses

- **Date**: 2026-10-02
- **Context**: the diagram's `export writers` box holds one field, `field: type`.
  `ChessNotationWriter` holds a format list and one field, `item: attribute`.
  `MetadataWriter` holds `method(type): type`. **No edge in the diagram connects
  any writer to any other writer, or to `export writers`.** `ChessNotationWriter`
  has no edges at all. The word `Extends` appears in the diagram only as an
  `edgeLabel` on a free-standing line positioned beside the six piece boxes.
- **Deviation**: the writers become a class hierarchy — an `ExportWriter` base
  with one subclass per format — and each subclass moves into the configuration
  that needs it, so `games/chess/export/` holds `ExportAlgebraic`, `ExportPGN`,
  `ExportFEN`, `ExportStenographic` and `ExportMetadata`.
- **Rationale**: the diagram's format list is a single parameter accepted by one
  writer, which means a format switch. Polymorphism removes the switch, and
  per-configuration placement is what lets a game have exactly the formats that
  mean something for it.
- **Why this is recorded rather than claimed as conformance**: the same
  parent-and-subclasses shape is registered as a deviation in section 4 for
  `Rule` and `Quest`. Applying one test consistently means applying it here too.
  The difference is that section 4 rests on a generalization edge the diagram
  genuinely draws (`Kůň → Figurka`), while this one does not.
- **Mitigation**: the diagram's three named members do **not** all survive.
  Corrected 2026-10-04; the earlier text claimed all three did, and two of the
  three do not exist in any form:

  | Drawn member | In the code |
  |---|---|
  | `export writers` · `field: type` | **present** — `ExportWriter.field` (`model/misc/export_writers.py:46`) |
  | `MetadataWriter` · `method(type): type` | **absent** — `MetadataWriter` has `set_header`, `get_header`, `format_pgn_headers` and `export`, and no `method` |
  | `ChessNotationWriter` · `item: attribute` | **absent** — `ChessNotationWriter` has `formats`, `_fen_letter`, `to_fen`, `to_pgn`, `to_stenographic` and `export`, and no `item` |

  `MetadataWriter` keeps its **name**, and no writer is renamed away. The two
  absent members are registered in §23. `QuestManager`'s drawn `field` and
  `method(type): type` are absent as well; `QuestManager` itself survives.
- **Approval**: directed by the user on 2026-10-02 — *"maybe have export
  generalized same way"*.

### 8. Result — the Outcome Type

- **Date**: 2026-10-02
- **Context**: `GameManager.get_stav(): int` is the diagram's only game-state
  accessor, and it returns a bare integer. It cannot express *who* won, *why*
  the game ended, or what to do when two rules end the game at once.
- **Deviation**: outcomes become a `Result` carrying a kind (win, loss, draw), a
  precedence, and an optional winner.
- **Rationale**: without a precedence, two rules ending a game simultaneously is
  ambiguous, and "any conceivable logic" would collapse on the first collision.
  `get_stav()` is retained and reports from `Result`, so the drawn member
  survives.
- **Approval**: directed by the user on 2026-10-02.

### 9. Configurable — the Field Declaration Framework

- **Date**: 2026-10-02
- **Context**: the diagram has no declaration or rendering layer. The mockup
  requires every configurable surface to be editable.
- **Deviation**: a `Field` declaration type, a `value_fields()` declaration hook
  that `Board`, `Piece` and `Rule` each declare, `Quest.parameters()` for a quest,
  a `clock_fields()` function for a clock, and one form renderer that turns a
  declaration into widgets.
- **Correction, 2026-10-04: there is no `Configurable` class and no `spec()`.**
  This section previously registered "a `Configurable` protocol with
  `spec() -> list[Field]`, conformed to by `Board`, `Piece`, `Clock`, `Rule` and
  `Quest`". Neither exists. `rg 'def spec|class Configurable'` over the tree
  returns nothing. What exists is four separate declarations and one renderer:

  | Type | Declaration | Where |
  |---|---|---|
  | `Board` | `value_fields()` | `model/game/board.py:68` |
  | `Piece` | `value_fields()` and `apply_values()` | `model/pieces/piece.py:123,160` |
  | `Rule` subclass | `value_fields()` | `model/game/rule.py:191` |
  | `Quest` subclass | `parameters()` | `model/game/quest.py` |
  | a clock | `clock_fields(clock)` | `model/game/clock_fields.py:28` |
  | the renderer | `SECTIONS`, `_WIDGETS`, the section builders | `view/settings_dialog.py:37` |

  **`Clock` is not among them because there is no `Clock` class** — §13 registered
  one as the intention and §20 records that it is unbuilt. That is why a clock is
  declared by a function rather than by a method: there is no parent for the hook
  to hang off. A clock that *does* declare its own `value_fields()` is asked first
  (`clock_fields.py:43`), so a configuration with a richer clock gets a richer form
  for free.
- **Rationale**: it is what lets one settings screen serve every surface, so a new
  field is one widget rather than one bespoke form. Without it the settings
  surface duplicates itself five times.
- **Approval**: directed by the user on 2026-10-02 — *"we should generalize the
  configuration pattern across the whole engine that will also allow us to reuse
  the same ui for the entire settings"*.

### 10. Execution of Player-Authored Code

- **Date**: 2026-10-02
- **Context**: the diagram has no loading, registration or evaluation mechanism of
  any kind.
- **Deviation**: the product loads and runs Python the player writes in its rule
  and quest editors, importing from within the configuration directory being
  edited and from nowhere else.
- **Rationale**: it is the only way to satisfy "customisation in any way" — a
  teleporting piece or an unforeseen draw condition is behaviour, not data, and
  the diagram's idiom for behaviour is a subclass.
- **Bounding**: loading is restricted to the configuration directory, never an
  arbitrary path or environment variable; the editor validates before code may
  join a configuration; and a refused path is tested.
- **Approval**: directed by the user on 2026-10-02.

### 11. Multi-Hop Moves

- **Date**: 2026-10-02
- **Context**: `Tah` carries `vychozi pozice`, `cilova pozice`, `figurka` and
  `typ tahu` — one start, one end, one piece. There is no structure for a move
  that visits several squares.
- **Deviation**: a move that visits several squares is a subclass of the drawn
  move. `HopMove(Move)` in `games/checkers/moves.py` carries the hop sequence, and
  it is declared by the configuration whose game needs it.
- **Correction, 2026-10-04: `Move` is not untouched.** This section said "`Move` is
  unchanged", and so did `SCRATCHPAD.md` §4.7 and its planned-PR-12 section before
  this pass. `Move`
  gained four members after this section was written, none of them draughts-shaped
  and all of them needed by chess: `captured_piece`, `capture_from`,
  `companion_start` and `companion_end` (`model/game/move.py:67-72`). The first
  records a taken piece while the board still holds it, the second the square a
  distant capture's victim stood on, and the last two the second square pair a
  castling rook needs. **What is true is the narrower claim this section makes in
  its own Mitigation: no *hop-sequence* member was added to `Tah`, and nothing
  under `model/`, `controller/` or `view/` grew a draughts-shaped member.** The
  claim is about the hop sequence, not about the class.
- **What the subclass carries**: `hops`, the landing square of each jump in
  order, of which the last is the move's `end_pos`; `captures`, the square each
  taken piece stood on, one per hop, which cannot be derived because a king's
  victim is whatever piece stands first along the diagonal; `captured_pieces` in
  the order they were taken; and `route`, the starting square followed by each
  landing square.
- **How it executes**: `HopMove` overrides `apply_to_board` and reuses the
  engine's `unapply_from_board` verbatim, because it returns the engine's own
  `Applied` record. The validator's legality test, the game's move execution and
  every caller between them already go through that pair polymorphically, so a
  three-jump chain is put on and taken off the board by the same code that plays a
  castling move. A single jump is the degenerate case of both sequences, and there
  is no separate path for it.
- **Rationale**: a capture chain in draughts is one move the player makes, and the
  diagram's `typ tahu` field is a move *type*, so it cannot express a hop count.
  Putting the sequence on a subclass rather than on `Tah` is the stronger form of
  the deviation: nothing under `model/`, `controller/` or `view/` grows a
  draughts-shaped member, which is the same requirement FR-55 states and the same
  one the checkers configuration exists to test.
- **Mitigation**: `Tah`'s hop-related members are untouched; a subclass is added.
  One caller does not survive: a caller that rebuilds the board from a snapshot
  rather than undoing, because `Move` records the mover and `HopMove` checks it by
  identity. `tests/test_draughts_perft.py` walks by undoing for that reason.
- **Approval**: directed by the user on 2026-10-02, via the checkers requirement.
- **Stale code docstring, recorded 2026-10-04.** `games/checkers/moves.py`'s
  module docstring says this section "should be amended to say a `Move` subclass
  carries the hops; it is not, and this docstring is the honest record until it
  is". **This section was amended on 2026-10-02 and does say exactly that.** The
  docstring is the stale half, not this section. Correcting it is a code change and
  is owed; it was not made in the documentation pass that amended this file.

### 12. FEN Import

- **Date**: 2026-10-02
- **Context**: the diagram defines only writers. Nothing in it reads a position.
- **Deviation**: an importer is added alongside the FEN writer.
- **Rationale**: the round-trip conformance requirement needs a reader. Import is
  the direction the diagram does not draw.
- **Approval**: directed by the user on 2026-10-02.

### 13. Timer to Clock, and the Clock Parent

- **Date**: 2026-10-02
- **Context**: the diagram's class is `Timer`, with `cas_hrac: List(int)`,
  `nuluj_cas()` and `pocitej_cas(hrac)`. **No increment is drawn anywhere.**
- **Deviation, as registered**: the runtime countdown keeps the drawn name
  `Timer`; a configurable parent `Clock` is to carry the settings a configuration
  declares — an initial time and an increment — and a `Timer` is constructed from
  it.
- **Status: registered, not built.** There is **no `Clock` class** in this
  repository. Both shipped clocks — `games/chess/clocks/fischer.py` and
  `games/checkers/clocks/fischer.py` — derive from nothing. What exists instead is
  `model/game/clock_fields.py`, a function that declares a clock's fields by asking
  what the clock object holds; see §20 for why it is a function and not a method.
  `PRD.md` §4 and §6 have been corrected not to name `Clock` as a parent class
  that exists. **A real `Clock` parent remains unbuilt and is recommended.**
- **Rationale**: the increment is required by the configuration surface and has
  no drawn home. Splitting the drawn countdown from the configurable settings
  leaves the drawn class intact rather than renaming it away.
- **Approval**: directed by the user on 2026-10-02.

### 14. The Two Pages Disagree — Recorded, Not Resolved

- **Date**: 2026-10-02
- **Context**: the diagram's two pages model the same class names with
  incompatible members.
  | Member | Page-1 | Page-2 |
  |---|---|---|
  | board field on the game manager | `plocha` | `herni_plocha` |
  | player collection | `hraci: List(Hrac)` | `hraci: List(Uzivatele)` |
  | board grid field | `herni_deska` | `hraci_plocha` |
  | board dimensions | `rozmery: Tuple = (8,8)` | `rozmery: Tuple(int,int)` |
- **Deviation**: neither reading can be satisfied simultaneously, so one is
  chosen and recorded. **Page-1 is followed** for the shared members, because it
  is the full object model and page 2 is the MVC integration. `hraci` is
  `List(Hrac)`; a player carries a reference to its user, so a player list can
  reach users without the list being a list of users.
- **Also noted**: `rozmery: Tuple = (8,8)` on page 1 hard-codes the default board
  size. That default is kept, but nothing may rely on it — see FR-1 and FR-15.
- **Approval**: recorded for visibility on 2026-10-02.

### 15. The View Classes the Diagram Draws Are Not Three Classes

- **Date**: 2026-10-02
- **Context**: page 2 has no `HracView` box. `+ hrac_view: HracView` appears only
  as an attribute *type* on `GameManagerController`. There is also no `GameVeiw`-as-a-class-name
  match, because the diagram spells it `GameVeiw`.
- **Deviation**: `PlayerView` is created, with the Czech alias `HracView`, as a
  real class; the diagram's spelling of `GameVeiw` is recorded as a typo and not
  reproduced.
- **There is no `GameView` class.** This section previously recorded one as
  created, and no such class exists in any form. What is there:
  - `view/game_view.py` declares `BoardView`, the only part of the program that
    knows what a square looks like. It draws the grid, the pieces, the
    coordinates, the selection and legal-move highlights, and the check marker.
  - `view/player_game_view.py` declares `PlayerGameView`, the window a game is
    played in. It holds a `BoardView` as `board_view` and composes it with the
    player panels, the move history, the turn indicator, the status footer and the
    quest cards.
- **How the drawn operations are served**: `GameView.aktualizuj_plochu()` —
  refresh the board when the controller reports a change — is
  `PlayerGameView.refresh`, which calls `board_view.refresh` and then
  `board_view.set_in_check`. `PlayerGameView.reload` (`player_game_view.py:186-187`)
  and `on_new_game` (`:207-208`) call `board_view.refresh` and
  `board_view.set_selection` instead. `GameManagerController.game_view: GameView`
  is satisfied by the `PlayerGameView` that holds the board view.
  *Corrected 2026-10-04: this section said `refresh` calls `board_view.refresh`
  and `board_view.set_selection`, and that `reload` and `on_new_game` "call the
  same pair". Neither half was right. `refresh` calls `set_in_check`
  (`player_game_view.py:223`); `set_selection` is called from
  `on_square_clicked` (`:157,159`), `reload` (`:187`) and `on_new_game` (`:207`),
  never from `refresh`.*
- **Why composition rather than a third class**: the diagram's own
  generalisation idiom settles what the parent is. `BoardView` is the piece the
  diagram has no box for, `PlayerGameView` is the `HracGameView` it does, and a
  `GameView` that wrapped the first inside the second would hold no state and
  forward every call — a class with a name and no behaviour. FR-65 and FR-66 are
  satisfied by the two classes that exist.
- **Rationale**: the controller attribute names a view it must hold, and the
  requirements render a board and a player panel, so both classes have to exist.
- **Approval**: directed by the user on 2026-10-02.

### 16. A Configuration Loads as a Package in Its Own Right

- **Date**: 2026-10-03
- **Context**: section 5 makes a configuration a copyable directory, and
  `SCRATCHPAD.md` section 2 makes duplication the extension mechanism: `cp -r
  games/chess games/house`, change what differs, a variant exists. Nothing about
  that works. Every module inside a configuration imported `games.chess.…` by
  absolute path, so a copy loaded the *original* configuration's board, pieces,
  clocks and quests while looking like it had loaded its own — no error, no
  warning, and a variant that plays orthodox chess after being edited into
  something else.
- **Change**: two halves, both needed together.
  - Inside `games/chess/`, every module now imports relatively
    (`from .board import …`, `from .pieces.knight import Knight`), so a copy's
    imports resolve inside the copy. The gap that was left here — the modules
    under `games/chess/rules/` importing each other by absolute path — was
    closed on 2026-10-03; see section 19.
  - `model/game/configuration.py` registers a loaded configuration as a *package*
    rooted at its own directory (`spec_from_file_location(..., submodule_search_locations=[directory])`).
    Without that search path a relative import fails outright, and the tempting
    repair — an absolute `games.chess.…` import inside a copy — loads the
    original. The synthetic module name stays path-derived and unique, so a
    variant named `house` never shadows the shipped `games.chess` package.
- **Deviation**: none beyond section 10, which already registers the loading
  mechanism and its bounding. This is that mechanism working for a copy rather
  than only for the shipped directory.
- **Gap closed 2026-10-03.** The remaining gap recorded below is closed;
  section 19 carries the change. Nothing in a copied configuration reaches back
  into `games/chess` any more — with one exception outside the configuration:
  `model/misc/export_writers.py` reaches `games.chess.export.algebraic` by
  absolute path inside `_to_algebraic()`, so a copy that keeps using the shipped
  writer still borrows the original's square naming. That is harmless for a
  chess-derived copy and wrong for a copy whose squares are not chess's, and it
  disappears when the writer itself moves to `games/chess/export/` as section 7
  already decided.

### 17. The Engine Quest Roster Names No Piece

- **Date**: 2026-10-03
- **Context**: `SCRATCHPAD.md` constraint 1.4 says the engine holds no chess, and
  the module docstring of `model/game/quests.py` said its quests name none. The
  roster it exports contradicted both: it composed `CaptureOfType("queen")` and
  `KingOnlyGame("king")`.
- **Change**: the roster is seventeen quests rather than nineteen. `CaptureOfType`
  and `KingOnlyGame` are absent for the same stated reason `CompositeQuest` is —
  a roster entry must be decidable without a configuration, and these two cannot
  be, because both *require* a piece type and raise without one. `games/chess/`
  names both, with chess's own piece names, so chess loses no quest.
- **Deviation**: none. The roster is not drawn in the diagram; quests themselves
  are registered in section 4, and this narrows what the engine volunteers rather
  than adding structure. The roster was the fallback
  `model/game/manager.py` reached for when a configuration declared no quests,
  and that fallback is gone as of 2026-10-03 — a configuration that declares no
  quests now gets none. `model/game/quests.py` remains as a library of quest
  classes a configuration composes from, and `BUILT_IN_QUESTS` remains a
  catalogue a caller may read, but nothing in the engine hands it to a game.

### 18. Dead Configuration State Is Populated, Not Dropped

- **Date**: 2026-10-03
- **Context**: `Configuration.pieces` and `Configuration.exporters` were written
  as empty lists by every configuration and read by nothing.
- **Change**: populated rather than dropped. `games/chess/pieces/__init__.py`
  declares `PIECES` and `build_pieces()`, and `games/chess/__init__.py` declares
  `build_exporters()`. Section 4 registers a configuration as a bundle of *pieces*
  and per-configuration export writers, so removing either attribute would
  contradict a registered decision while filling them in carries it out.
- **Consequence recorded, and closed on 2026-10-03.** `Configuration.exporters`
  is now read: `model/game/manager.py` takes its writers from it instead of
  constructing `ChessNotationWriter()` unconditionally, so the engine no longer
  names a chess writer at all and the move section 7 describes is unblocked —
  see section 19. `model/misc/notation.py` is still a re-export shim for the
  moved algebraic conversion, but no longer for the manager's sake: its one
  remaining consumer outside this repository's configuration layer is
  `view/player_game_view.py`.

### 19. The Engine Names No Notation, and a Copy Keeps Its Own Rules

- **Date**: 2026-10-03
- **Context**: two recorded decisions and one wiring gap, all in the same direction —
  a class name, a spelling and an import list that the plan wrote down and the code did
  not follow.
- **Change, five parts.**
  1. **The fifteen Czech aliases all exist.** Six are in the chess configuration
     (`Pesak`, `Vez`, `Kun`, `Strelec`, `Dama`, `Kral`) and nine are in the engine
     and view modules that own the class each names (`Figurka`, `HerniPlocha`,
     `Tah`, `Hrac`, `RevizorTahu`, `Uzivatel`, `Kwest`, `HracView`,
     `HracGameView`). Each is a one-line binding next to the class it names, and
     each is the same object rather than a lookalike.
  2. **`Knight` is canonical and `Horse` is gone.** The class is `Knight`, the file
     is `games/chess/pieces/knight.py`, and `Kun` is the alias. There is no `Horse`
     binding anywhere, per the approved outcome below.
  3. **`Tower` and `Controller` are removed.** `Tower` was shipped as `Tower = Rook`
     on the reasoning that `Tower` is Czech for the rook; it is not, `Věž` is, and
     `Vez` is its ASCII spelling. `Controller` was shipped as
     `Controller = GameController`. Both were approved drops, and
     `games/chess/pieces/tower.py` is deleted.
  4. **The manager reads `configuration.exporters` and declares no quests.** It does
     not import or name `ChessNotationWriter`, and does not fall back to the engine's
     quest roster.
  5. **`games/chess/rules/` imports relatively**, and `promotion.py` builds the
     promoted piece relatively, so a copied configuration composes its own rules and
     promotes into its own pieces. This closes the gap section 16 recorded.
- **The fifteen-row alias table, as implemented.** `PRD.md` section 5 is
  authoritative; this is that table with the module each alias lives in.

  | Diagram | Canonical | Czech alias | Where the alias lives |
  |---|---|---|---|
  | `Figurka` | `Piece` | `Figurka` | `model/pieces/piece.py` |
  | `Pěšák` | `Pawn` | `Pesak` | `games/chess/pieces/pawn.py` |
  | `Věž` | `Rook` | `Vez` | `games/chess/pieces/rook.py` |
  | `Kůň` | `Knight` | `Kun` | `games/chess/pieces/knight.py` |
  | `Střelec` | `Bishop` | `Strelec` | `games/chess/pieces/bishop.py` |
  | `Dáma` | `Queen` | `Dama` | `games/chess/pieces/queen.py` |
  | `Král` | `King` | `Kral` | `games/chess/pieces/king.py` |
  | `HerníPlocha` | `Board` | `HerniPlocha` | `model/game/board.py` |
  | `Tah` | `Move` | `Tah` | `model/game/move.py` |
  | `Hrac` | `Player` | `Hrac` | `model/game/player.py` |
  | `RevizorTahu` | `MoveValidator` | `RevizorTahu` | `model/game/validator.py` |
  | `Uzivatel` | `User` | `Uzivatel` | `model/users/user.py` |
  | `Kwest` | `Quest` | `Kwest` | `model/game/quest.py` |
  | `HracView` | `PlayerView` | `HracView` | `view/player_view.py` |
  | `HracGameView` | `PlayerGameView` | `HracGameView` | `view/player_game_view.py` |

  `tests/test_aliases.py` holds this table against the source: it asserts every name
  resolves from its stated module, that each alias `is` its canonical class, that
  the table has exactly fifteen rows, and that `ALIASES_OUTSTANDING` is exactly the
  set of aliases which do not resolve. That set is empty, so the table cannot drift
  from the code without the suite failing.
- **A piece's class name is not its configured kind.** `Knight` declares
  `piece_type="horse"` and that is deliberate. `piece_type` is data a configuration
  chooses and writes into `configuration.json`, so renaming it would silently repoint
  every stored configuration that says `horse` at nothing. `games/chess/rules/draws.py`
  already accepted both spellings for exactly this reason, and still does. The
  display name did change to `Knight`, because a display name is not persisted.
- **What this departs from, recorded as required.** Three departures, none of which
  is a diagram deviation:
  1. **`ExportWriter.formats()` is new.** The engine must be able to tell "this
     configuration does not export that notation" from "this writer had nothing to
     write", and the two used to be indistinguishable because both arrived as `""` —
     a stenographic record of a game with no moves really is empty. A writer declaring
     what it writes is therefore the base class's business, not a chess detail.
     `model/misc/export_writers.py` is an engine module this work was not given; the
     addition is `ExportWriter.formats()` returning `()` and `ChessNotationWriter`
     overriding it.
  2. **`GameManager.transcript()` lost its default argument.** It was `fmt: str =
     "PGN"`, which was chess in a signature, and it now defaults to the first notation
     the configuration offers; `save_log()` names its default file from that notation
     instead of hard-coding `.pgn`. A caller that passed a format is unaffected.
  3. **A dead duplicate was removed.** `GameManager` defined `save_log` twice, the
     first as a no-argument stub shadowed by the real one. Nothing called the stub;
     it was a trap for anyone who did.

### 20. The Settings Surface Gains What the Plan Recorded

- **Date**: 2026-10-03
- **Context**: sections 3 and 9 registered the settings layer and the field declaration
  framework, and both shipped as `view/settings_dialog.py` rendering per-rule fields and
  nothing else. The plan records more: a corner selector (FR-30), five sections (FR-31), a
  code editor for logic (FR-33, FR-34), and configurations that can be created, renamed,
  duplicated and deleted (FR-28). Of those, only the per-rule form existed, and
  `SCRATCHPAD.md` item 18 — the default configuration cannot be edited or deleted — was
  unenforced: `Configuration.save_values()` wrote into the configuration directory with no
  guard at all.
- **Change, four things.**
  1. **The default configuration refuses to be written to.** `Configuration.is_default` names
     the case and `save_values()` refuses a target inside that directory's own tree. The guard
     is scoped to the directory rather than to writing: exporting the default's values
     elsewhere is a read, not an edit. `copy_configuration`, `rename_configuration` and
     `delete_configuration` are the directory moves FR-28 asks for, and all three refuse the
     default.
  2. **The code editor, and the check it stands on.** `view/code_editor.py` is a text area
     over one file in the configuration directory being edited, and it refuses to save what
     `model/game/source_validation.py` refuses. This is section 10's bounding being carried
     out rather than a new mechanism: the validator executes the code it checks, which is what
     the product does anyway when it loads a configuration.
  3. **Five sections and the corner selector.** One tab per configurable surface — Board,
     Pieces, Rules, Quests, Clocks — each assembled from what its subject declares, plus a
     selector in the corner with a plus button that duplicates the configuration being edited.
  4. **Declarations where there were none.** `Board.value_fields()`, `Piece.value_fields()`
     and `Piece.apply_values()`, and `model/game/clock_fields.py`. None of the three declared
     anything before, so the sections had nothing to render from.
- **Deviation**: none beyond sections 3, 9 and 10, which already register the settings layer,
  the declaration framework and the execution of authored code. Everything here is those three
  being finished.
- **What this departs from, recorded as required.** Three departures, none of which is a
  diagram deviation:
  1. **`model/game/clock_fields.py` is new and has no diagram counterpart.** A clock is the
     one configurable type that is a plain object rather than a parent class with subclasses —
     both shipped configurations ship a `Fischer` and neither derives from anything — so there
     is no `Clock` class for a declaration to hang off. The module declares a clock's fields
     from what the clock holds, and asks the clock first if it declares its own. Section 13
     registered a `Clock` parent as the intention; this is a declaration function standing in
     for the class that has not been written. **A real `Clock` parent remains unbuilt and is
     recommended.**
  2. **`Piece.apply_values()` is new.** `value_fields()` is a declaration; something has to
     write the values back, and two of the declared values are not single attributes — the two
     symbols are one tuple, and the vectors are a list of pairs shown as text. Parsing them in
     the piece rather than in the view is what keeps the form a renderer.
  3. **`Configuration.package` is new.** A configuration now carries the module name it is
     registered under, so a relative import inside a file being checked resolves against the
     package the file belongs to. Without it every file in a configuration that imports its
     siblings reports an ImportError that is an artefact of checking rather than a fault in
     the code.
- **Recorded as a limit, not finished**: the Pieces section reads each piece class from a
  probe instance and writes back to that instance. A configuration's `pieces` are *classes*,
  so a symbol changed in the form changes the probe and not the class the configuration
  composes. Making a piece's identity configurable therefore needs the configuration to hold
  piece instances or declared overrides, which is not built.

---

### 21. `games/checkers` Was Not WCDF English Draughts, and Now Is

  - **Date**: recorded 2026-10-04, closed 2026-10-04
  - **Context**: `PRD.md` FR-54 requires "a complete, correct **English draughts**
    configuration", naming twelve pieces a side, one-square men, kings moving one
    square diagonally, mandatory capture including chains, promotion on reaching
    the far rank, and a win by immobilisation or by losing all pieces. FR-55 requires
    it to need no engine change.
  - **The engine half held throughout.** No file under `model/`, `controller/` or
    `view/` changed to add `games/checkers/`, and closing these five gaps changed
    none of them either. That is the requirement FR-55 states and it is satisfied.
  - **Five places where the configuration was not the rulebook's game.** None of
    them was recorded anywhere before this section, and each was a departure from
    what FR-54 describes, which `AGENTS.md` Rule 3 requires here:

    | # | FR-54 asks for | What shipped | Now |
    |---|---|---|---|
    | 1 | a king **steps** one square | the king **slid** any distance — flying kings, which is international, Brazilian, Czech and Dutch draughts | `max_steps=1`. Rule 1.17: "from one square diagonally forward or backward, left or right to an immediately neighbouring vacant square"; rule 1.21 gives its capturing move as a man's in any direction |
    | 2 | the WCDF forty-move draw | `plies` defaulted to **100** — fifty moves each side, the international figure | `plies` defaults to **80**, rule 1.32.2's "previous 40 moves" by each side |
    | 3 | threefold repetition is one of the rulebook's draws | **no repetition rule existed** | `ThreefoldRepetitionRule`, rule 1.32.1 |
    | 4 | insufficient material is not an English draughts rule | `InsufficientMaterialRule` was in force and drew any position where neither side held a man — which is two-kings-against-one, a game that is still winnable | **removed**. Article 1.32 lists three draws and this was not one of them |
    | 5 | two non-English variants are not in force | `LimitedKingsRule` capped kings per side, which no rulebook does | unchanged in class, but its shipped value is a side's full complement, so it forbids nothing until somebody lowers it |

  - **One divergence from the rulebook remains, deliberately.** Rule 1.32.1 is a
    *claim*: a player demonstrates to the referee that their next move would create
    the position for the third time. The engine has no referee and no claim to make,
    so `ThreefoldRepetitionRule` proposes the draw itself. The chess configuration's
    own repetition rule diverges in the same way and for the same reason.
  - **The perft gate could not see any of this, and says so.**
    `tests/test_draughts_perft.py` measured a man needs more than eight plies to crown
    from the starting position — its own two rows are in the way — so no king exists
    anywhere in the tree it walks. A king that slides and a king that steps produce
    identical counts at every depth it checks; both were measured at depth eight and
    both gave 845931. The rulebook, not the numbers, is what decided the king's reach.
    The gate's own docstring now records that blind spot, and `tests/test_checkers.py`
    is what pins the king.
  - **What closing this cost in counts**: two self-consistent baselines in
    `tests/test_draughts_perft.py` — `CHAIN_PERFT` and `CROWNING_PERFT` — changed,
    because they are the only figures in that file a crowned king can reach within four
    plies. The independent counter and the engine moved to the same new figures
    together, which is what holding a position where the two differ is for.
  - **Also absent, and not a departure**: `games/checkers` declares **zero**
    exporters. `build_configuration()` passes `exporters=[]`. FR-54 and planned PR
    17 ask for *letter* and the metadata header; neither exists. This is a
    requirement not yet met rather than a departure from the diagram, and it is
    recorded here so it is not mistaken for a writer that exists and is wrong.
  - **Mitigation**: none of this touches the engine or the diagram's classes. Each
    departure was a rule's configured value, a piece's declared step length, or an
    absent rule inside one configuration directory, which is exactly where
    `SCRATCHPAD.md` §2 says the variation between games lives. Closing them was a
    change to `games/checkers/` and nothing else — the strongest evidence yet that
    the abstraction holds. A variant that wants the international king changes one
    number, `max_steps`, in one piece.
  - **Approval**: recorded 2026-10-04 as a measured discrepancy between `PRD.md`
    FR-54 and `games/checkers/`, and closed the same day against FR-54 as written.
    **approved by the maintainer on 2026-10-04**. The ruling covered all five gaps, the
    one divergence kept on purpose (1.32.1 proposed rather than claimed), and leaving
    `LimitedKingsRule` and `CaptureRule` declared and inert.

  ---

  ### 22. A Configuration Composes Its Quests Instead of Declaring Quest Files

- **Date**: 2026-10-04
- **Context**: `PRD.md` §6 states, as a fact about the layout, that
  `games/<config>/quests/` is "one file per quest: logic and parameters". Neither
  shipped configuration keeps a quest file there. `games/chess/quests/__init__.py`
  is one docstring line and nothing else; `build_quests()` is declared in
  `games/chess/__init__.py`. `games/checkers/quests/__init__.py` declares its own
  `build_quests()` and its directory holds no quest file either.
- **Deviation**: the twenty quest classes live in `model/game/quests.py` as one
  library, and a configuration's `quests/` package composes the handful it ships.
- **Rationale**: a configuration ships a handful of quests — chess composes six,
  checkers four — and the whole library is twenty classes that would otherwise be
  duplicated or split across directories without being made more configurable. The
  classes are the unit; a configuration names which of them it plays.
- **Why it needs recording at all**: `SCRATCHPAD.md` §2 called this "one declared
  deviation from 'one file per entry'" before any deviation was declared anywhere,
  and `PRD.md` §6 stated the layout with no annotation. Both are corrected on the
  same pass: §2 now points here and `PRD.md` §6 now annotates the line.
- **Not a diagram deviation.** The diagram draws `Quest` and `Kwest` and nothing
  about file layout, so this is a departure from `PRD.md` §6 rather than from the
  assignment specification.
- **Approval**: **not approved.** Recorded 2026-10-04 as the correction of a claim
  that had no record behind it.

---

### 23. Members the Diagram Draws That the Code Does Not Have, and Members the Code Has That the Diagram Does Not Draw

- **Date**: 2026-10-04
- **Context**: `AGENTS.md` Rule 3 makes an unrecorded departure a defect in both
  directions. §7's mitigation claimed the diagram's three named export members all
  survive. They do not. Separately, a sweep of the tree against
  `notes/reference_diagram.md`'s inventory found members the diagram does not draw
  and no section registered.

**Drawn, and absent from the code.** Three members, four declarations:

| Drawn member | Class | Status |
|---|---|---|
| `method(type): type` | `MetadataWriter` | **no `method` member.** `MetadataWriter` has `set_header`, `get_header`, `format_pgn_headers`, `export` |
| `item: attribute` | `ChessNotationWriter` | **no `item` member.** The class has `formats`, `_fen_letter`, `to_fen`, `to_pgn`, `to_stenographic`, `export` |
| `field: type` | `QuestManager` | **no `field` member** |
| `method(type): type` | `QuestManager` | **no `method` member** |

  §7's Mitigation has been corrected to say so. All three classes survive by name;
  what is absent is these four declarations. `ExportWriter.field` — the `export
  writers` box's one member — **is** present at `model/misc/export_writers.py:46`,
  so the box the diagram draws smallest is the one that survived whole.

**Not drawn, and present in the code.** Thirteen additions. None is registered
anywhere before this section. None alters the diagram's classes or their
relationships; each is an extension of a mechanism an earlier section registered.

| Addition | What it is | Registered by |
|---|---|---|
| `MoveValidator.find_move` | `validator.py:490`. The move the rules offered between two squares, with whatever a rule attached to it — a capture chain, a promotion piece, a companion rook. **Required by the engine**: `controller/controller.py:70` uses it, and rebuilding a `Move` from two squares silently drops everything a rule attached | none — new here |
| `Move.capture_from` | `move.py:55`. The square a taken piece stands on when it is not the destination | none — new here |
| `Move.companion_start` / `companion_end` | `move.py:57,59`. The second square pair, for a move that carries a piece along — a castling rook | none — new here |
| `Board.set_dimensions` / `is_within_bounds` / `apply_placement` | `board.py:85,120,194`. Board-size generalisation (FR-1, FR-15): the board exposes its own bounds instead of every caller taking them from a literal | §5, §16 — the *capability* is registered; the three methods were not named |
| `MoveEvent`, `ResultEvent` | `model/game/events.py`. The two event records quests are handed. §4 registers `Quest` with a `validate()` that takes no arguments; without an event there is nothing for `observe_move`/`observe_result` to receive | §4 by implication; the classes were not named |
| `Quest.observe_move` / `observe_result` | `quests.py:88,672`. How the event reaches a quest, since `validate()` takes nothing | none — new here |
| `UnsupportedExportFormat` | `manager.py:27`. Raised when no declared writer offers the notation asked for, so "this configuration does not write that" is not an empty string that reads like a game with nothing to say | §19 part 1 covers `ExportWriter.formats()`; the exception was not named |
| `QuestManager.field` | **not present** — see the table above | — |
| `model/game/games.py` | Where the shipped configurations are resolved, the default is named and an unknown name is refused. §5 puts configurations in `games/`; this is the module that finds them | §5 by implication |
| `view/code_editor.py` | The editor itself. §10 registered the *execution* of authored code; §20 part 2 registered the check | §10, §20 — the module was not named in either |
| `model/game/clock_fields.py` | A clock's declared fields. §9 now records why it is a function and not a method | §9, §20 part 1 — named in §20 only |
| `model/game/source_validation.py` | The check that runs before code joins a configuration | §10, §20 part 2 — the module was not named in either |

- **Approval**: **not approved.** Recorded 2026-10-04 by a sweep of the tree
  against `notes/reference_diagram.md`. None of the thirteen changes a class the
  diagram draws, and none of them is the diagram being wrong about something it
  does draw; they are additions to it, which is what this section is for. The four
  absent members are a different matter and need the maintainer's decision: either
  the diagram member is implemented, or this section stands as the record that it
  was consciously not.

---

### 24. Two Docstrings in `games/checkers` Misdescribe the Rulebook and These Notes

- **Date**: 2026-10-04
- **Context**: two statements inside `games/checkers/` are false against the code
  beside them. They are recorded here because this pass may not edit code under
  `games/`, and because `AGENTS.md` Rule 2 makes the source docstrings the
  documentation.
- **`games/checkers/rules/draws.py:17`** states "The rulebook draws by agreement,
  by threefold repetition, and by the rule above, and nothing else." **No
  repetition rule is configured in `games/checkers/`** — see §21 item 3 — and the
  module itself declares three rules, one of which (`InsufficientMaterialRule`) the
  same sentence says the rulebook does not have. The sentence describes the
  rulebook rather than the module, in a module that is the rulebook's
  implementation; as written it reads as a description of the shipped rules and is
  not one. **Correction owed**: it should say the rulebook draws by agreement, by
  threefold repetition and by the fifty-move rule; that this configuration
  implements the last two and not the third; and that its third rule is not the
  rulebook's.
- **`games/checkers/moves.py`** module docstring states that
  `notes/object_model.md` §11 "should be amended to say a `Move` subclass carries
  the hops; it is not, and this docstring is the honest record until it is."
  **§11 was amended on 2026-10-02 and does say exactly that.** The docstring is
  self-referential and stale. **Correction owed**: it should point at §11 as the
  record rather than describing §11 as unamended.
- **Approval**: not applicable — both are corrections of fact, not decisions. They
  are owed as code changes under planned PR 12 and PR 17 respectively.

---

## Naming decisions requiring approval context

Recorded here because they are deviations from what the diagram draws and
`AGENTS.md` Rule 3 requires their approval to be on record.

| Decision | Outcome | Approved |
|---|---|---|
| `Kůň` maps to `Knight`, not `Horse` | `Knight` is canonical, `Kun` is its Czech alias, `Horse` is removed — see sections 15 and 19. | 2026-10-02 |
| `Tower` | Dropped. No box in the diagram carries that name, and `Věž` maps to `Rook`. `games/chess/pieces/tower.py` is deleted. | 2026-10-02 |
| `Controller` | Dropped. No box carries that name; the diagram's controller box is `GameManagerController`. The alias is gone from `controller/controller.py`. The module is still `controller.py`, not `game_manager_controller.py` — see `SCRATCHPAD.md` planned PR 20. | 2026-10-02 |
| Czech aliases carry no diacritics | ASCII spellings only | 2026-10-02 |
| `HracView` is created as `PlayerView` | See section 15. The class exists, and its `HracView` alias does too. | 2026-10-02 |
| A piece's configured `piece_type` is not renamed with its class | `Knight` declares `piece_type="horse"`. `piece_type` is persisted configuration data, so renaming it would repoint every stored value. **New, 2026-10-03**; approval not yet on record. | Recorded 2026-10-03; **not approved** |
| `KingOnlyGame` keeps its chess name | **Not renamed, and recommended for renaming.** The class judges a game in which only one kind of piece ever moved, which is not chess-specific, so `SingleKindGame` would be the honest name — but `royal_kind` is the constructor keyword configurations pass and `tests/test_quest.py` calls with it, and renaming either needs that test updated and every player-authored quest file to change with it. Renaming the class while keeping the keyword would leave the vocabulary in place anyway, so the name stays until the keyword can move with it. | Recorded 2026-10-03; **not approved** |
| `ChessNotationWriter` keeps its name in the engine | **Not moved, and registered for moving.** Section 7 already places per-format writers in `games/chess/export/`, and section 7's approval covers it. The blocker was `model/game/manager.py`'s import by name, and that is gone as of 2026-10-03, so the move is now unblocked and unperformed. Moving it while leaving a shim behind would make the engine module import the configuration that imports the engine module, which fails on a cycle as soon as any variant configuration is loaded. | Recorded 2026-10-03; **not approved** |
