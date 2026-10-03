# Reference Architecture Diagram

## Link to the live diagram

[Draw.io Architecture Diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)

- **File**: `Šachy - diagram tříd.drawio`
- **Pages**: `Page-1` — the full object model, and `MVC - GameView` — the MVC
  integration and the view bindings.

**Status**: this diagram is the assignment specification. Anything it defines is
implemented; anything it omits is out of scope unless a user request adds it.

## What this document is

An inventory of the diagram, transcribed from the draw.io file. It records what
the diagram **actually draws**, including where the diagram is inconsistent or
incomplete, so that conformance claims elsewhere are checkable against it.

Deviations from this inventory are recorded in `notes/object_model.md`.

---

## Page-1 — class inventory

| Diagram class | Declared members | Declared operations |
|---|---|---|
| `Uzivatel` | `uzivatelske_jmeno : string`, `jmeno : string`, `email : string`, `elo : integer`, `splnene_kwesty : List(Kwest)` | `pridej_quest(quest : Quest)` |
| `Quest` | `nazev`, `popis` | `validate() : bool` |
| `HerníPlocha` | `+rozmery: Tuple = (8,8)`, `herni_deska: List(List(Figurka))`, `vyhozene_figurky_b: List(Figurka)`, `vyhozene_figurky_c: List(Figurka)` | `+vrat_obsah(souradnice): Figurka`, `posun_figurky(Tah): bool`, `nahrad_figurku(Figurka, Tah)` |
| `Figurka` | `název: string`, `vektory_utoku: List(Vektor)`, `barva(tým): integer`, `vektory: List(Vektor)` | none |
| `Hrac` | `+barva : integer`, `+uzivatel : Uzivatel` | `getEloRating: integer` |
| `GameManager` | `plocha: HerníPlocha`, `aktivni_hrac: int`, `hraci: List(Hrac)`, `aktualni_tah: Tah`, `casovac: Timer`, `game_logger: GameLogger`, `+revizor_tahu: RevizorTahu` | `zacni_tah(): Tah`, `mozne_tahy(): List(Tah)`, `zrus_tah(): None`, `uloz_log(): void`, `get_stav(): int`, `najdi_uzivatele(id: integer): Uzivatel` |
| `Tah` | `vychozi pozice: seznam`, `cilova pozice: seznam`, `figurka: Figurka`, `typ tahu: string` | `over platnost(): bool`, `proved tah(): void` |
| `RevizorTahu` | `herni_plocha: HerníPlocha`, `tah: Tah` | `simulate_Move() = seznam`, `check_Šach() = bool`, `check_Mat = bool`, `check_Pat = bool` |
| `Kůň` | `vektor: seznam`, `vektor_utoku: seznam`, `skok: bool = true` | none |
| `Král` | `vektor`, `vektor_utoku`, `skok: bool = false` | none |
| `Dáma` | `vektor`, `vektor_utoku`, `skok: bool = false` | none |
| `Věž` | `vektor`, `vektor_utoku`, `skok: bool = false` | none |
| `Pěšák` | `vektor`, `vektor_utoku`, `skok: bool = false` | none |
| `Střelec` | `vektor`, `vektor_utoku`, `skok: bool = false` | none |
| `User Manager` | `Id_uzivatele: hrac`, `log_uzivatelu: string`, `historie_uzivatele: string` | `proveď_tah: () bool` |
| `export writers` | `+field: type` | none — the operation compartment is empty |
| `ChessNotationWriter` | `+item: attribute` | none named; the operation compartment holds prose (see below) |
| `MetadataWriter` | none; the attribute compartment reads `no parameters` | `+method(type): type` |
| `GameLogger` | `soubor: File` | `+uloz_tah(Tah): None`, `+vytvor_soubor(String): None` |
| `Timer` | `+cas_hrac: List(int)` | `+nuluj_cas(): None`, `+pocitej_cas(hrac: int): None` |
| `QuestManager` | `+field: type` | `+method(type): type` |

### The `ChessNotationWriter` format list

Its operation compartment is prose rather than named operations, and enumerates:
*letter*, *PGN*, *FEN*, *Field - Field - Extra*, *Stenographic* — annotated
"(Standard or custom compression)" — together with **the game transcript**,
described as arriving "as a single parameter".

The **`export writers`** box does **not** contain this list. It holds one field.
Both facts are load-bearing: see `notes/object_model.md` section 7.

### Free-standing notes on Page-1

- **Validation timing**, still posed as an open question in the diagram:
  *"Validace tahu — Rozhodněme se, zda je lepší rozhodnout o proveditelnosti tahu
  pro každou figuru před tahem, nebo bezprostředně po kliknutí na konkrétní a pro
  konkrétní figuru."* Resolved by `notes/object_model.md` section 2 and FR-15.
- *"Integer bude buď 1 nebo -1 podle barvy"*
- *"Pro pěšáka se vektor vynásobí barvou"*

---

## Page-1 — relationships

**Exactly one generalisation edge exists in the whole file**: `Kůň → Figurka`,
drawn with a hollow triangle.

**Composition**: `Quest` into `Uzivatel.splnene_kwesty`.

**Associations** (no arrowhead, with multiplicity where drawn):

`Uzivatel` ↔ `Hrac` · `GameManager.plocha` → `HerníPlocha` · `HerníPlocha` →
`Figurka` · `GameManager.hraci` → `Hrac` · `Tah.figurka` → `Figurka` ·
`RevizorTahu.herni_plocha` → `HerníPlocha` · `RevizorTahu.tah` → `Tah` ·
`GameManager.revizor_tahu` → `RevizorTahu` · `GameManager.game_logger` →
`GameLogger` · `GameManager.casovac` → `Timer`

---

## Page 2 — MVC integration

| Diagram class | Declared members | Declared operations |
|---|---|---|
| `GameManagerController` | `+game_manager: GameManager`, `+herni_plocha: HerniPlocha`, `+game_view: GameView`, `+hrac_view: HracView` | `+vyber_pole(souradnice)` |
| `GameManager` | `+herni_plocha: HerniPlocha`, `+aktivni_hrac: int`, `+hraci: List(Uzivatele)`, `+revizor_tahu: RevizorTahu` | `+je_vlastni_figurka(souradnice): bool` |
| `HerniPlocha` | `+hraci_plocha: List(List(Figurka))`, `+rozmery: Tuple(int,int)` | `+vrat_obsah(souradnice): Figurka` |
| `GameVeiw` | `+controller: GameManagerController` | `+aktualizuj_plochu: None` |
| `HracGameView` | `+controller: GameManagerController` | `+akutalizuj_hrace(hrac): None` |

All four edges are plain associations. **Page 2 draws no generalisation.**

---

## Recorded defects in the diagram

Recorded because conformance claims depend on them, and because silently
smoothing them over would make the deviations unverifiable.

### Naming

| Drawn | Note |
|---|---|
| `GameVeiw` | missing `r`. No class carries this name in the code; the drawn spelling is not reproduced, and `notes/object_model.md` section 15 records what stands in its place |
| `check_Pat` | Czech *patová* — stalemate. Retained as the drawn operation name's meaning, spelled correctly in code |
| `intger` | misspelling of `integer` on `get_stav()` |
| `akutalizuj_hrace` | missing `l` |
| `Id_uzivatele: hrac` | a user id typed as a player |
| `proveď_tah`, `over platnost` | Czech with diacritics inside member names |
| `HracView` | **no class box exists.** It appears only as an attribute *type* on `GameManagerController`. The class is created as `PlayerView` — `notes/object_model.md` section 15 |

### Structural inconsistency

- **Only `Kůň` is connected to `Figurka`.** The other five pieces have an edge
  with a source and **no target**, and each redeclares `vektor`, `vektor_utoku`
  and `skok` rather than inheriting them. The intent is that all six extend
  `Figurka`, and the code does that; the drawing is simply unfinished.
- **`skok` is declared on the six subclasses, not on `Figurka`.** `Figurka` has
  `název`, `vektory`, `vektory_utoku` and `barva`.
- **`Extends` is not a relationship.** It is an `edgeLabel` on a free-standing
  line inside a zero-height legend group positioned beside the piece row.
- **`ChessNotationWriter`, `MetadataWriter`, `QuestManager` and `User Manager`
  have no edges at all.**
- **`get_stav()` is drawn in transparent zero-size text** wrapping a nested
  `mxGraphModel` — a copy-paste leftover that concealed the operation. It is the
  diagram's only game-state accessor and is retained.

### The two pages contradict each other

| Member | Page-1 | Page 2 |
|---|---|---|
| board field on the game manager | `plocha` | `herni_plocha` |
| player collection | `hraci: List(Hrac)` | `hraci: List(Uzivatele)` |
| board grid field | `herni_deska` | `hraci_plocha` |
| board dimensions | `rozmery: Tuple = (8,8)` | `rozmery: Tuple(int,int)` |
| operations on the game manager | six | one |

`List(Hrac)` and `List(Uzivatele)` cannot both hold. Page-1 is followed,
because it is the full object model and page 2 is the integration sketch — see
`notes/object_model.md` section 14.

Page-1 also writes `rozmery: Tuple = (8,8)`, hard-coding the default board size.
That default is kept; nothing may rely on it.

---

## Canonical translation

Czech-to-English translation is canonical and is not a deviation. Names not
listed here are already English in the diagram.

| Diagram | English | Note |
|---|---|---|
| `Figurka` | `Piece` | parent of the six pieces |
| `Pěšák` | `Pawn` | |
| `Věž` | `Rook` | the diagram has no `Tower` box |
| `Kůň` | `Knight` | the diagram has no `Horse` box; the Czech alias is `Kun` |
| `Střelec` | `Bishop` | |
| `Dáma` | `Queen` | |
| `Král` | `King` | |
| `HerníPlocha` / `HerniPlocha` | `Board` | the diagram uses both spellings |
| `Tah` | `Move` | |
| `Hrac` | `Player` | |
| `RevizorTahu` | `MoveValidator` | |
| `Uzivatel` | `User` | |
| `User Manager` | `UserManager` | |
| `Quest` | `Quest` | already English |
| `Kwest` | `Quest` | appears only inside `splnene_kwesty` |
| `Timer` | `Timer` | the configurable parent is `Clock` — `notes/object_model.md` section 13 |
| `GameManagerController` | `GameManagerController` | already English; the diagram has no `GameController` or `WindowController` box |
| `GameVeiw` | no class of that name | diagram typo. The board is `BoardView` in `view/game_view.py` and the window is `PlayerGameView` in `view/player_game_view.py` — `notes/object_model.md` section 15 |
| `HracGameView` | `PlayerGameView` | the `Hrac` part is Czech. `HracView` is `PlayerView` |

The full alias table the code must satisfy is in `PRD.md` section 5.