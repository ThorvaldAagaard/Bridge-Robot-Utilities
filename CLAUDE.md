# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bridge-Robot-Utilities is a collection of utilities for arranging and displaying results of bridge matches between robots. The tools handle PBN (Portable Bridge Notation) and LIN (BridgeBase format) files, connect bridge engines to table managers, and generate HTML reports.

## Build Commands

### Build all executables (Windows)
```cmd
cd Install
build.cmd
```
`build.cmd` creates a dedicated virtual environment (`Install/.buildenv`), installs the
pinned dependencies from `Install/requirements.txt`, then runs PyInstaller for every spec
and `pkg` for the Node.js tools. **Build in this clean environment** — a polluted global
Python pulls scipy/pandas/Jupyter/etc. into every executable and bloats them to ~99 MB;
the clean build is ~37 MB.

### Build individual Python utilities
```cmd
cd Install
.buildenv\Scripts\python -m PyInstaller <utility_name>.spec
```
The build venv is based on miniconda, which keeps `tcl86t.dll`/`tk86t.dll`/`ffi-8.dll` in
`<base>\Library\bin`. `build.cmd` puts that folder on PATH; when running PyInstaller by hand, do the
same (`set PATH=C:\ProgramData\miniconda3\Library\bin;%PATH%`) or the exe builds fine but dies at
startup with `DLL load failed while importing _tkinter` (tell-tale: MergePBNFiles ~7.5 MB instead of ~11 MB).

Spec files are in `Install/`. Each corresponds to a Python source file in `src/`. All specs
share the exclude list in `Install/build_excludes.py` (via `from build_excludes import EXCLUDES`),
which strips libraries no shipped tool uses. matplotlib is a hard dependency of `endplay`
(eager import in `endplay/__init__.py`) and cannot be excluded, so ~37 MB is the size floor.

### Build Node.js utilities
```cmd
call pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
call pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
call pkg -t node16 ..\src\TMWbridge5.js -o dist/TMWbridge5.exe
call pkg -t node16 ..\src\ExtractLinks.js -o dist/ExtractLinks.exe
```

### Run Python utilities directly
```cmd
python src/<utility_name>.py [arguments]
```

### Packaging notes
- The build env installs **stock** endplay from PyPI, which may differ from a locally patched endplay in the global Python: a script that works from source can still fail as an exe. Test PBN parsing with `Install\.buildenv\Scripts\python`.
- `benchmark.py` is **not** shipped as an executable (TensorFlow makes it ~530 MB); run it from source.
- `ComputeDDTables.py`, `ComputeDatumScores.py` and `CheckDatumScores.py` are **not** shipped (developer-side steps around `DatumScores.pkl`); run them from source.
- `.gitattributes` normalizes line endings (`text=auto`); avoid re-introducing whole-file CRLF churn.
- Every utility prints its version on start (`"<Name>, Version X.Y.Z"`); keep these in sync when bumping.

## Architecture

### Two Technology Stacks

**Python (src/*.py)**: File conversion utilities and HTML report generators
- Uses `endplay` library for PBN/LIN parsing
- Uses `tkinter` for file dialogs in GUI utilities
- `scoring.py`: Bridge scoring calculations (contract scores, overtricks, undertricks)
- `compare.py`: IMP (International Match Point) calculations for comparing results

**Node.js (src/*.js)**: Table manager interface programs
- `TMGib.js`: Connects GIB bridge engine to Table Managers (Bridge Moniteur, etc.)
- `TMMediator.js`: Mediator for Blue Chip Bridge with Bridge Moniteur
- `TMWbridge5.js`: Seats WBridge5's `Autoconnect` mode at a table manager, and can start the instances
- `ExtractLinks.js`: Extract challenge matches from BBO as PBN
- Uses TCP sockets for Table Manager protocol communication

### Key Python Utilities

| Utility | Purpose |
|---------|---------|
| `PBN2LIN.py` | Convert PBN to LIN format (command-line) |
| `PBN2LinUI.py` | Convert PBN to LIN format (GUI) |
| `LIN2PBN.py` | Convert LIN to PBN format (command-line) |
| `Lin2PBNUI.py` | Convert LIN to PBN format (GUI) |
| `listmatchpbnashtml.py` | HTML comparing multiple PBN files (open/closed pairs, IMPs); match-results + team-totals summary at top |
| `comparerobots.py` | HTML comparing one PBN per robot side-by-side; match-results + team-totals summary at top |
| `comparematchpbnashtml.py` | Compare two robot replays as HTML |
| `printmatchpbnashtml.py` | HTML index of all boards linking to per-board files (Bridge Composer output) |
| `MergePBNFiles.py` | Merge all PBN files in a folder into one (dialogs, or `-d/-o/-r` on the command line); reports duplicate and rotated boards, within and across files, with file and board number |
| `CalculateMatch.py` | Merge open/closed room PBN into match file |
| `CountPBNBoards.py` | Count boards in a PBN file |
| `Split_PBN.py` | Split a PBN by double-dummy results into separate files |
| `ResetAndRenumberPBNBoards.py` | Renumber boards (dealer and vulnerability follow the new board number), drop incomplete, duplicate and rotated deals and play |
| `csvlin2pbn.py` | Convert a Danish Bridge Federation CSV/LIN to PBN |
| `LoadAndSavePBN.py` | Round-trip a PBN through endplay (PBN → LIN) |
| `TMPbn2LinVG.py` | Convert Bridge Moniteur PBN to LIN for NetBridgeVu |
| `TMPbn2DDS.py` | Clean PBN from Bridge Moniteur for Double Dummy Solver |
| `TMPbn2Cleaner.py` | Clean non-standard lines from a PBN file |
| `ExtractDatumScore.py` | Add the double-dummy tables a PBN already carries (`[OptimumResultTable]`) to `DatumScores.pkl` — no solving |
| `ComputeDDTables.py` | Migrate an old `DatumScores.pkl` to tricks only, solving entries that have no table — **source-only, not shipped** (endplay/DDS dev step; run `python src/ComputeDDTables.py DatumScores.pkl`) |
| `ComputeDatumScores.py` | Double-dummy solve a PBN's deals that the pickle has no tricks for, and add them to `DatumScores.pkl` — **source-only, not shipped** (endplay/DDS dev step) |
| `AddDatumScoreToPBN.py` | Annotate a PBN from `DatumScores.pkl` with `OptimumScore`/`ParContract`/`OptimumResultTable` (single output file) |
| `UpdateScore.py` | Score the auctions in a PBN from `DatumScores.pkl`: `Declarer`/`Contract` from the auction, double-dummy `Result`, `Score`, plus the `AddDatumScoreToPBN` tags (reuses its `lookup`/`build_ort`/`strip_existing` and `scoring.score`); for engines that write only the calls, ahead of `Split_PBN` |
| `CheckDatumScores.py` | Scan a PBN for boards with missing/malformed par annotation, duplicate and rotated deals — **source-only, not shipped** |
| `PbnExtractBoards.py` | Extract unique boards, remove duplicates (`extract_boards(boards)` is the core, shared with ProcessRobotReports) |
| `ProcessRobotReports.py` | File a robot's report folder: save each TMClient zip's `match.pbn` (or a plain match PBN) to `Boards\<name>.matches` named after the robot in the player tags, extract it, move the report to `Processed`, rebuild `All.PBN`/`Ordered_All.PBN` overall and per robot (dialogs, or `<folder> [--dry-run] [--rename] [--merge]`). Reuses PbnExtractBoards, MergePBNFiles and `ResetAndRenumberPBNBoards.renumber_boards` |
| `benchmark.py` | Hardware benchmark — **source-only, not shipped** (run `python src/benchmark.py`) |

### Shared Modules

- `src/scoring.py`: Contract score calculation using bridge scoring rules
- `src/compare.py`: IMP difference calculation between match results
- `src/lastdir.py`: Remembers the last folder used in file dialogs (stored in `%APPDATA%/bridge-robot-utilities.json`). `get_last_dir(key=...)`/`set_last_dir(path, key=...)` — most GUI tools share the default key; the extract/split/renumber tools pass `key="extract"`/`"split"`/`"renumber"` for separate folders.
- `src/dealkey.py`: `hands_from_north(deal)` normalizes a PBN deal (any first seat, value or whole `[Deal]` line) to N/E/S/W hands; `deal_problem(hands)` says why four hands are not a complete deal (not 13 cards each, a card twice), or `None`; `rotation_key(hands)` is identical for a deal and its 1/2/3-seat rotations. `same_board(...)` additionally requires dealer and vulnerability to have turned along (accepts PBN tag strings or endplay `Player`/`Vul` ints). Used by `CheckDatumScores` and `MergePBNFiles` (report) and `ResetAndRenumberPBNBoards` (drops true copies and incomplete deals).
- `src/endplayfix.py`: imported (for its side effect) by every tool that calls `pbn.load`; it wraps `PBNDecoder._tags_to_board` so the stock endplay in the build env behaves like the locally patched one. It re-applies the fixes the locally patched endplay has and the stock PyPI build lacks, so source runs and executables behave alike: (1) endplay (0.5.10 and 0.5.12) applies `[Dealer]` only when the board has a contract, so boards with no `[Contract]` or `[Contract "?"]` get the board-number dealer — and wrong vulnerabilities once a tool resets the dealer; (2) a NAG (`$1`) in an auction reaches `Bid()` and raises `ValueError: invalid literal for int() with base 10: '$'`; (3) the LIN encoder omits the leading `mn||`; (4) `trick_winner` raises `IndexError` on a part trick instead of returning the player on lead. `[Contract "?"]` is fixed in 0.5.12 itself (as `None`, where the patched endplay gave `Pass`), so it is not repeated. New PBN- or LIN-using tools must import it too. Drop a part once the endplay build (the team has a fork) has it.
- `src/datumscore.py`: owns the `DatumScores.pkl` format (below) — `load`/`save` (atomic, one-time `.bak`), `tricks(data, deal_line)` (exact line, then endplay's canonical deal), `tricks_of(value)` (reads both the current and the old tuple format), `normalise` (old → current), `tricks_from_ort`, and `par_tags(dd_bytes, vulnerable)`, which computes `[OptimumScore]`/`[ParContract]` for ONE board with DDS `Par()` on the stored table, written the way BBA and Brill's `DdsParFormat` write them.
- `src/connectionhandler.js`: TCP connection handling for Node.js tools
- `src/processFinder.js`: Windows process management for GIB engine

### Datum-score cache (`DatumScores.pkl`)

A pickle (gitignored, `src/DatumScores.pkl`) keyed by the exact `[Deal "..."]` line. **Each value is the deal's double-dummy table and nothing else**: 20 bytes, one trick count per (declarer, denomination) in the order **N/E/S/W × S/H/D/C/NT** (`datumscore.PLAYER_ORDER` × `DENOM_ORDER`). The format lives in `src/datumscore.py`; every tool goes through it.

**Only tricks, because only tricks belong to the deal.** `[OptimumScore]`/`[ParContract]` depend on the board's vulnerability, and the `[Score]` of a contract on the contract too, so the readers compute them from the tricks for each board they handle. The pickle used to store the par tags under the deal key, which gave every copy of a deal the par of whichever copy was stored: in Brill's `TrainingDeals.pbn` 3,310 boards — every one a deal that recurs at another vulnerability, and no others — carried their twin's par (board T16102, NS vulnerable, was tagged with the non-vulnerable `NS 1510 / 7S=` where par is `NS 2000` for EW's 7NTX−8 save). Old pickles still read: a `(OptimumScore, ParContract, vul, dd_bytes)` tuple contributes its `dd_bytes` (its stored par is ignored); a tuple with no `dd_bytes` counts as absent, since a stored par cannot be trusted for a particular board.

**Par is DDS `Par()` on the stored table, written in BBA's notation** (`datumscore.par_tags`), which is also what Brill computes (`DdsNativeSolver.CalculatePar` + `DdsParFormat`): every contract that scores par, cheapest first, `"; "` between; the declaring SEAT when only one partner makes it (`W 1H+2`), else the side; the lowest level DDS names, with its result; a doubled sacrifice `X`; the score from the DECLARING side (`EW -100` with `EW 2SX-1`). Where par depends on who bids first (both sides make 1NT) both sides' figures are written, as BBA does (`NS 90 EW 90`, `NE 1N=`). Passed out: `NS 0` / `NSEW PASS`. Measured against BBA's own tags on the 1,174,522 training boards it tagged correctly: score text identical on all but one (a side-dependent board BBA settled by dealer), contract text on all but 148 (BBA and DDS naming a different, equal-scoring level, `1N+1` / `2N=`). Brill's `ParAnalyzer --verify-par` agrees with a re-annotated file on score and contract 20,000/20,000.

- **`ExtractDatumScore.py`** adds the tables a PBN already carries: every board with a complete 20-row `[OptimumResultTable]` contributes its tricks (no solving). Boards without one are counted for `ComputeDatumScores`; a table that disagrees with the pickle's is reported, never overwritten.
- **`ComputeDatumScores.py`** double-dummy solves each distinct deal of a PBN the pickle has no tricks for (vulnerability and dealer are not read — tricks don't depend on them). Resumable (worker checkpoints `datum_ckpt_*.pkl`), atomic rewrite, `DD_WORKERS` env var (default 2 — DDS already threads internally, so more oversubscribes).
- **`ComputeDDTables.py`** migrates an old pickle: solves the entries without a table (checkpoints `dd_ckpt_*.pkl`), rewrites every value as plain tricks. A no-op on a current pickle.
- **`AddDatumScoreToPBN.py`** annotates a PBN — `[OptimumScore]`, `[ParContract]` (from the board's own `[Vulnerable]`) and the `[OptimumResultTable]` — as a byte-preserving text edit. `strip_existing` also steps over a one-line `{ ... }` comment between the table tag and its rows (BBA writes `{ Shape ... }` there), keeping the comment; before, the old rows survived beside the new table.
- **`UpdateScore.py`** does the same and scores each board's auction: `[Result]` is `dd_bytes[declarer * 5 + S/H/D/C/NT index]`, `[Score]` comes from `scoring.score`.
- **`CheckDatumScores.py`** streams a PBN and reports boards with no `OptimumScore`/`ParContract`/`OptimumResultTable`, tables that aren't the full 20 rows or hold a trick count outside 0..13, and passed-out pars written as a level-0 contract. Given the pickle, each unannotated board is classified *in the pickle* (its tricks are there: re-run `AddDatumScoreToPBN`) or *missing* (run `ComputeDatumScores`). It also reports duplicate board numbers and duplicate deals, and exits non-zero when anything is wrong.
- **`Split_PBN.py`** computes par from the pickle for a board without `[OptimumScore]`, at that board's vulnerability.

**Shipping:** the executables that compute par (`AddDatumScoreToPBN`, `UpdateScore`, `Split_PBN`) need endplay's `dds.dll` at `endplay/_dds/` inside the bundle — endplay loads it beside its wrapper and PyInstaller cannot see that ctypes load — so their specs add `collect_dynamic_libs('endplay')`. Without it the exe dies at import with "Failed to load dynlib/dll ...\endplay\_dds\dds.dll".

Because the value shape can be a 3- or 4-tuple, any new consumer must index (`value[0]`, `value[3] if len(value) > 3`) rather than unpack a fixed arity.

### CSS Files

HTML generators embed CSS for standalone output (read at runtime, no external dependency):
- `src/listmatch.css`: used by `listmatchpbnashtml.py`
- `src/robotcompare.css`: used by `comparerobots.py`
- `src/viz.css`: used by `comparematchpbnashtml.py` and `printmatchpbnashtml.py`

The HTML report tools (listmatch/comparerobots) also inject extra rules in a `<style>` block at generation time (e.g. the `.match-summary` width/centering overrides).

## Table Manager Protocol

TMGib communicates with table managers using a text-based protocol over TCP (default port 2000). Key concepts:
- Seats: North, East, South, West
- Protocol version 18
- Commands include bidding, play, and timing information
- GIB bridge engine is spawned as subprocess and controlled via stdin/stdout

### WBridge5's `Autoconnect` seat (`TMWbridge5.js`)

`Wbridge5.exe Autoconnect <port>` connects by itself but always announces
`Connecting "WBridge5" as ANYPL using protocol version 18`. `ANYPL` is index 0 of a padded
five-entry table in the executable (`ANYPL|NORTH| EAST|SOUTH| WEST`) and means "any player" -- it
asks the table manager to assign the seat. **Nothing selects the seat on WBridge5's side**: a third
command line argument is ignored and the INI keys have no effect (both tested).

- Bridge Moniteur assigns the first vacant seat (`bm17.r`, `Get-Client`: `find Siege "Any"`), which
  is why Autoconnect works there.
- TMJob rejects it: `AsyncTableHost.ProcessConnect` takes exactly five characters after `" as "` and
  matches north/east/south/west, else `Illegal hand 'anypl' specified`.

The **seated reply is the seat assignment** -- answer `North ("WBridge5") seated` and WBridge5
adopts North. So `TMWbridge5.js` only has to rewrite that one token on the first line; everything
afterwards passes through untouched, because WBridge5 accepts the table manager's own wording
(TMJob's parenthesised form included) and tolerates LF as well as the CRLF it sends itself.

Two quirks when reading its traffic: it echoes its seat **uppercase and space-padded**, so
`NORTH ready for  EAST's bid` has a double space. TMJob additionally refuses two pairs with the same
team name, which blocks WBridge5 against WBridge5 until `--name` renames them.
