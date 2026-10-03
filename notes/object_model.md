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
- **Implemented 2026-10-03, partially — see section 19.** This section listed
  seven alias spellings as though they were the whole set, which they are not:
  they are the seven whose Czech spelling *differs* from the English one. The
  other eight (`Figurka`, `Tah`, `Hrac`, `RevizorTahu`, `Uzivatel`, `Kwest`,
  `HracView`, `HracGameView`) have the same spelling in both languages and were
  never listed at all, which is how all fifteen went unimplemented while this
  section read as if they did not. `PRD.md` section 5 holds the authoritative
  fifteen-row table; section 19 carries it as corrected against the code.
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
- **Deviation**: `SettingsView`, `SettingsController` and a settings model are
  added to the view and controller layers. They have no counterpart in any
  diagram box.
- **Rationale**: the board, pieces, rules, quests and clocks must be
  configurable, and rule logic must be authored. Without a settings layer none
  of that is reachable, and the mockup's configuration surface — the product's
  primary purpose — cannot be delivered.
- **Mitigation**: the settings classes are thin adapters over the model. They
  hold no game state and add no rules, so the deviation is additive and does not
  alter the object model the diagram defines.
- **Approval**: recorded with explicit user approval, 2026-10-02.

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
  `check_Pat` are outcomes proposed through `Rule.outcome`. See FR-60.
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
- **Mitigation**: the diagram's three named members all survive as classes —
  `export writers` becomes the `ExportWriter` base with its `field`, and
  `MetadataWriter` keeps its name and its `method(type): type`. Nothing is
  renamed away.
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
- **Deviation**: a `Field` declaration type and a `Configurable` protocol with
  `spec() -> list[Field]`, conformed to by `Board`, `Piece`, `Clock`, `Rule` and
  `Quest`, plus one form renderer that turns a declaration into widgets.
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
- **Deviation**: `Move` grows a sequence of hops alongside its start and end.
- **Rationale**: a capture chain in checkers is one move the player makes. The
  diagram's `typ tahu` field is a move *type*, so it cannot express hop count.
- **Mitigation**: `Tah`'s existing members are untouched; only a sequence is
  added. A single-hop move is the degenerate case, and both share one code path.
- **Approval**: directed by the user on 2026-10-02, via the checkers requirement.

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
- **Deviation**: the runtime countdown keeps the drawn name `Timer`; a
  configurable parent `Clock` carries the settings a configuration declares — an
  initial time and an increment — and a `Timer` is constructed from it.
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

### 15. HracView Is Not a Class

- **Date**: 2026-10-02
- **Context**: page 2 has no `HracView` box. `+ hrac_view: HracView` appears only
  as an attribute *type* on `GameManagerController`. There is also no
  `GameVeiw`-as-a-class-name match, because the diagram spells it `GameVeiw`.
- **Deviation**: `PlayerView` is created, with the Czech alias `HracView`, as a
  real class; and `GameView` is created as a real class for the diagram's
  `GameVeiw` box. The diagram's spelling is recorded as a typo and not reproduced.
- **Rationale**: the controller attribute names a view it must hold, and the
  requirements render a player panel, so the class has to exist.
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
  1. **The fifteen Czech aliases.** None of the fifteen in `PRD.md` section 5 existed.
     Six now do, in the chess configuration: `Pesak`, `Vez`, `Kun`, `Strelec`, `Dama`
     and `Kral`. The other nine are engine and view classes whose modules were not in
     this work's file list, so they remain missing and are listed by name below.
  2. **`Knight` is canonical and `Horse` is gone.** `games/chess/pieces/horse.py`
     declared `class Horse(Piece)` and ended with `Knight = Horse`, which made the
     English name the alias — the reverse of the decision. The class is now `Knight`,
     the file is `games/chess/pieces/knight.py`, and `Kun` is the alias. There is no
     `Horse` binding anywhere, per the approved outcome above.
  3. **`Tower` and `Controller` are removed.** `games/chess/pieces/tower.py` shipped
     `Tower = Rook` on the reasoning that `Tower` is Czech for the rook; it is not,
     `Věž` is, and `Vez` is its ASCII spelling. `controller/controller.py` shipped
     `Controller = GameController`. Both were approved drops.
  4. **The manager reads `configuration.exporters` and declares no quests.** It no
     longer imports or names `ChessNotationWriter`, and no longer falls back to the
     engine's quest roster.
  5. **`games/chess/rules/` imports relatively**, and `promotion.py` builds the
     promoted piece relatively, so a copied configuration composes its own rules and
     promotes into its own pieces. This closes the gap section 16 recorded.
- **The fifteen-row alias table, as implemented.** `PRD.md` section 5 is
  authoritative; this is that table checked against the code on 2026-10-03.

  | Diagram | Canonical | Czech alias | Where the alias lives | State |
  |---|---|---|---|---|
  | `Figurka` | `Piece` | `Figurka` | `model/pieces/piece.py` | **missing** |
  | `Pěšák` | `Pawn` | `Pesak` | `games/chess/pieces/pawn.py` | present |
  | `Věž` | `Rook` | `Vez` | `games/chess/pieces/rook.py` | present |
  | `Kůň` | `Knight` | `Kun` | `games/chess/pieces/knight.py` | present |
  | `Střelec` | `Bishop` | `Strelec` | `games/chess/pieces/bishop.py` | present |
  | `Dáma` | `Queen` | `Dama` | `games/chess/pieces/queen.py` | present |
  | `Král` | `King` | `Kral` | `games/chess/pieces/king.py` | present |
  | `HerníPlocha` | `Board` | `HerniPlocha` | `model/game/board.py` | **missing** |
  | `Tah` | `Move` | `Tah` | `model/game/move.py` | **missing** |
  | `Hrac` | `Player` | `Hrac` | `model/game/player.py` | **missing** |
  | `RevizorTahu` | `MoveValidator` | `RevizorTahu` | `model/game/validator.py` | **missing** |
  | `Uzivatel` | `User` | `Uzivatel` | `model/users/user.py` | **missing** |
  | `Kwest` | `Quest` | `Kwest` | `model/game/quest.py` | **missing** |
  | `HracView` | `PlayerView` | `HracView` | `view/player_view.py` | **missing** |
  | `HracGameView` | `PlayerGameView` | `HracGameView` | `view/player_game_view.py` | **missing** |

  Each missing alias is one line — the binding, next to the class it names — in a
  module this work was not given. `tests/test_aliases.py` asserts that this table's
  *missing* half is still exactly the set that does not resolve, so the gap is
  tracked rather than forgotten.
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

---

## Naming decisions requiring approval context

Recorded here because they are deviations from what the diagram draws and
`AGENTS.md` Rule 3 requires their approval to be on record.

| Decision | Outcome | Approved |
|---|---|---|
| `Kůň` maps to `Knight`, not `Horse` | `Knight` is canonical, `Kun` is its Czech alias, `Horse` is removed. **Implemented 2026-10-03** — see section 19. | 2026-10-02 |
| `Tower` | Dropped. No box in the diagram carries that name, and `Věž` maps to `Rook`. **Implemented 2026-10-03**: `games/chess/pieces/tower.py` deleted. | 2026-10-02 |
| `Controller` | Dropped. No box carries that name; the diagram's controller box is `GameManagerController`. **Implemented 2026-10-03**: the alias is gone from `controller/controller.py`. | 2026-10-02 |
| Czech aliases carry no diacritics | ASCII spellings only | 2026-10-02 |
| `HracView` is created as `PlayerView` | See section 15. The class exists; its `HracView` alias does not yet. | 2026-10-02 |
| A piece's configured `piece_type` is not renamed with its class | `Knight` declares `piece_type="horse"`. `piece_type` is persisted configuration data, so renaming it would repoint every stored value. **New, 2026-10-03**; approval not yet on record. | Recorded 2026-10-03; **not approved** |
| `KingOnlyGame` keeps its chess name | **Not renamed, and recommended for renaming.** The class judges a game in which only one kind of piece ever moved, which is not chess-specific, so `SingleKindGame` would be the honest name — but `royal_kind` is the constructor keyword configurations pass and `tests/test_quest.py` calls with it, and renaming either needs that test updated and every player-authored quest file to change with it. Renaming the class while keeping the keyword would leave the vocabulary in place anyway, so the name stays until the keyword can move with it. | Recorded 2026-10-03; **not approved** |
| `ChessNotationWriter` keeps its name in the engine | **Not moved, and registered for moving.** Section 7 already places per-format writers in `games/chess/export/`, and section 7's approval covers it. The blocker was `model/game/manager.py`'s import by name, and that is gone as of 2026-10-03, so the move is now unblocked and unperformed. Moving it while leaving a shim behind would make the engine module import the configuration that imports the engine module, which fails on a cycle as soon as any variant configuration is loaded. | Recorded 2026-10-03; **not approved** |
