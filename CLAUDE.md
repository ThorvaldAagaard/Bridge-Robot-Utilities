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
Spec files are in `Install/`. Each corresponds to a Python source file in `src/`. All specs
share the exclude list in `Install/build_excludes.py` (via `from build_excludes import EXCLUDES`),
which strips libraries no shipped tool uses. matplotlib is a hard dependency of `endplay`
(eager import in `endplay/__init__.py`) and cannot be excluded, so ~37 MB is the size floor.

### Build Node.js utilities
```cmd
call pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
call pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
call pkg -t node16 ..\src\ExtractLinks.js -o dist/ExtractLinks.exe
```

### Run Python utilities directly
```cmd
python src/<utility_name>.py [arguments]
```

### Packaging notes
- `RenumberPBNBoards.spec` builds an exe named **`ResetAndRenumberPBNBoards.exe`** (not RenumberPBNBoards).
- `benchmark.py` is **not** shipped as an executable (TensorFlow makes it ~530 MB); run it from source.
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
| `MergePBNFiles.py` | Merge multiple PBN files into one |
| `CalculateMatch.py` | Merge open/closed room PBN into match file |
| `CountPBNBoards.py` | Count boards in a PBN file |
| `Split_PBN.py` | Split a PBN by double-dummy results into separate files |
| `RenumberPBNBoards.py` | Renumber boards (builds `ResetAndRenumberPBNBoards.exe`) |
| `csvlin2pbn.py` | Convert a Danish Bridge Federation CSV/LIN to PBN |
| `LoadAndSavePBN.py` | Round-trip a PBN through endplay (PBN → LIN) |
| `TMPbn2LinVG.py` | Convert Bridge Moniteur PBN to LIN for NetBridgeVu |
| `TMPbn2DDS.py` | Clean PBN from Bridge Moniteur for Double Dummy Solver |
| `TMPbn2Cleaner.py` | Clean non-standard lines from a PBN file |
| `ExtractDatumScore.py` | Extract optimum scores/par contracts to pickle file |
| `PbnExtractBoards.py` | Extract unique boards, remove duplicates |
| `benchmark.py` | Hardware benchmark — **source-only, not shipped** (run `python src/benchmark.py`) |

### Shared Modules

- `src/scoring.py`: Contract score calculation using bridge scoring rules
- `src/compare.py`: IMP difference calculation between match results
- `src/lastdir.py`: Remembers the last folder used in file dialogs (stored in `%APPDATA%/bridge-robot-utilities.json`). `get_last_dir(key=...)`/`set_last_dir(path, key=...)` — most GUI tools share the default key; the extract/split/renumber tools pass `key="extract"`/`"split"`/`"renumber"` for separate folders.
- `src/connectionhandler.js`: TCP connection handling for Node.js tools
- `src/processFinder.js`: Windows process management for GIB engine

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
