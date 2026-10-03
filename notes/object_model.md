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
- **Czech aliases are permitted.** The classes the diagram names in Czech
  additionally expose a Czech alias bound to the same object, so the
  diagram-to-code mapping is discoverable from the source and the generated
  documentation. Aliases use ASCII spellings without diacritics:
  `HerniPlocha`, `Kun`, `Kral`, `Dama`, `Strelec`, `Pesak`, `Vez`. Comments,
  docstrings, commit messages and documentation remain English.
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
  - Inside `games/chess/`, every module this change touched now imports
    relatively (`from .board import …`, `from .pieces.horse import Horse`), so a
    copy's imports resolve inside the copy. The modules under
    `games/chess/rules/` still import absolutely and are listed as the remaining
    gap below.
  - `model/game/configuration.py` registers a loaded configuration as a *package*
    rooted at its own directory (`spec_from_file_location(..., submodule_search_locations=[directory])`).
    Without that search path a relative import fails outright, and the tempting
    repair — an absolute `games.chess.…` import inside a copy — loads the
    original. The synthetic module name stays path-derived and unique, so a
    variant named `house` never shadows the shipped `games.chess` package.
- **Deviation**: none beyond section 10, which already registers the loading
  mechanism and its bounding. This is that mechanism working for a copy rather
  than only for the shipped directory.
- **Remaining gap, recorded so it is not mistaken for done**: `games/chess/rules/__init__.py`,
  `attacks.py`, `bishop_colour.py`, `castling.py`, `check.py`, `draws.py`,
  `en_passant.py`, `flag.py`, `promotion.py` and `royal.py` import each other by
  absolute path, so a copied configuration currently composes *chess's* rules. A
  consequence beyond the imports themselves:
  `games/chess/rules/promotion.py` builds the promoted piece from
  `games.chess.pieces.…`, so a promotion in a copy yields a piece class belonging
  to the original configuration. `tests/test_configuration_copying.py` pins this
  gap in a test that fails the day it is closed.

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
  than adding structure. The roster is still the fallback
  `model/game/manager.py` reaches for when a configuration declares no quests,
  which is the only reason it cannot simply be deleted — and that fallback should
  go with the manager's other chess defaults.

### 18. Dead Configuration State Is Populated, Not Dropped

- **Date**: 2026-10-03
- **Context**: `Configuration.pieces` and `Configuration.exporters` were written
  as empty lists by every configuration and read by nothing.
- **Change**: populated rather than dropped. `games/chess/pieces/__init__.py`
  declares `PIECES` and `build_pieces()`, and `games/chess/__init__.py` declares
  `build_exporters()`. Section 4 registers a configuration as a bundle of *pieces*
  and per-configuration export writers, so removing either attribute would
  contradict a registered decision while filling them in carries it out.
- **Consequence recorded**: `Configuration.exporters` is populated but still read
  by nothing, because `model/game/manager.py` hard-codes `ChessNotationWriter()`
  instead of taking the first exporter from `configuration.exporters`. The writer
  class itself also still lives in the engine module
  `model/misc/export_writers.py`, and section 7 registers that it belongs in
  `games/chess/export/`; `model/game/manager.py`'s import by name is what blocks
  the move, and the same file blocks deleting `model/misc/notation.py`, which is
  now a re-export shim for the moved algebraic conversion.

---

## Naming decisions requiring approval context

Recorded here because they are deviations from what the diagram draws and
`AGENTS.md` Rule 3 requires their approval to be on record.

| Decision | Outcome | Approved |
|---|---|---|
| `Kůň` maps to `Knight`, not `Horse` | `Knight` is canonical, `Kun` is its Czech alias, `Horse` is removed | 2026-10-02 |
| `Tower` | Dropped. No box in the diagram carries that name, and `Věž` maps to `Rook` | 2026-10-02 |
| `Controller` | Dropped. No box carries that name; the diagram's controller box is `GameManagerController` | 2026-10-02 |
| Czech aliases carry no diacritics | ASCII spellings only | 2026-10-02 |
| `HracView` is created as `PlayerView` | See section 15 | 2026-10-02 |
| `KingOnlyGame` keeps its chess name | **Not renamed, and recommended for renaming.** The class judges a game in which only one kind of piece ever moved, which is not chess-specific, so `SingleKindGame` would be the honest name — but `royal_kind` is the constructor keyword configurations pass and `tests/test_quest.py` calls with it, and renaming either needs that test updated and every player-authored quest file to change with it. Renaming the class while keeping the keyword would leave the vocabulary in place anyway, so the name stays until the keyword can move with it. | Recorded 2026-10-03; **not approved** |
| `ChessNotationWriter` keeps its name in the engine | **Not moved, and registered for moving.** Section 7 already places per-format writers in `games/chess/export/`, and section 7's approval covers it. `model/game/manager.py` imports the class by name from the engine module, so the move is blocked on that one import. Moving it while leaving a shim behind would make the engine module import the configuration that imports the engine module, which fails on a cycle as soon as any variant configuration is loaded. | Recorded 2026-10-03; **not approved** |
