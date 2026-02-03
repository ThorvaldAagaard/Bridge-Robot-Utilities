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

### Build individual Python utilities
```cmd
cd Install
python -m PyInstaller <utility_name>.spec
```
Spec files are in `Install/` directory. Each spec file corresponds to a Python source file in `src/`.

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
| `listmatchpbnashtml.py` | Generate HTML comparing multiple PBN files |
| `comparematchpbnashtml.py` | Compare two robot replays as HTML |
| `MergePBNFiles.py` | Merge multiple PBN files into one |
| `CalculateMatch.py` | Merge open/closed room PBN into match file |
| `TMPbn2LinVG.py` | Convert Bridge Moniteur PBN to LIN for NetBridgeVu |
| `TMPbn2DDS.py` | Clean PBN from Bridge Moniteur for Double Dummy Solver |
| `ExtractDatumScore.py` | Extract optimum scores/par contracts to pickle file |
| `PbnExtractBoards.py` | Extract unique boards, remove duplicates |
| `benchmark.py` | System performance benchmark utility |

### Shared Modules

- `src/scoring.py`: Contract score calculation using bridge scoring rules
- `src/compare.py`: IMP difference calculation between match results
- `src/connectionhandler.js`: TCP connection handling for Node.js tools
- `src/processFinder.js`: Windows process management for GIB engine

### CSS Files

HTML generators embed CSS for standalone output:
- `src/listmatch.css`: Styles for match listing HTML
- `src/viz.css`: Visualization styles

## Table Manager Protocol

TMGib communicates with table managers using a text-based protocol over TCP (default port 2000). Key concepts:
- Seats: North, East, South, West
- Protocol version 18
- Commands include bidding, play, and timing information
- GIB bridge engine is spawned as subprocess and controlled via stdin/stdout
