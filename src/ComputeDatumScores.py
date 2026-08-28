"""Compute datum scores for a PBN's bare deals and add them to DatumScores.pkl.

For deals that carry no scores at all (only a `[Deal ...]`), this double-dummy
solves each deal and stores a full entry in the datum-score pickle:

    key   = '[Deal "..."]'
    value = (OptimumScore, ParContract, vul, dd_bytes)

- OptimumScore / ParContract come from the par calculation (endplay/DDS), given
  the board's vulnerability and dealer.
- dd_bytes is the 20-cell double-dummy table, packed one byte per
  (declarer, denomination) in the order N/E/S/W x S/H/D/C/NT.

It is the compute-from-scratch companion to ExtractDatumScore.py (which only
pulls existing score tags out of a PBN) and ComputeDDTables.py (which adds DD
tables to entries that already have a par score). Afterwards AddDatumScore.py can
write the tags into any PBN whose deals are now in the pickle.

This is the expensive, one-time step (hours for a large file). It is resumable:
worker checkpoints (`datum_ckpt_*.pkl`) let an interrupted run continue, and the
pickle is backed up to `DatumScores.pkl.bak` and replaced atomically.

Usage: ComputeDatumScores.py <input.pbn> [DatumScores.pkl]
Env:   DD_WORKERS (default 2)   -- DDS already threads internally, so 2 is the
       sweet spot on a many-core box; 3+ oversubscribes and slows down.
"""
import sys
import os
import time
import shutil
import pickle
import multiprocessing as mp
import tkinter as tk
from tkinter import filedialog
import lastdir
import endplay.config as config
config.use_unicode = False
from endplay.types import Deal, Denom, Player, Vul, Penalty
from endplay.dds import calc_all_tables, par

# Deals solved per DDS batch call (DDS caps CalcAllTables at 32).
CHUNK = 32
WORKERS = int(os.environ.get("DD_WORKERS", "2"))
# Flush a worker checkpoint every this many freshly solved deals.
CHECKPOINT_EVERY = 6400

# Packing order of the 20 bytes: 4 declarers x 5 denominations. AddDatumScore.py
# unpacks in this same order, so keep the two in sync.
PLAYERS = [Player.north, Player.east, Player.south, Player.west]
DENOMS = [Denom.spades, Denom.hearts, Denom.diamonds, Denom.clubs, Denom.nt]

VUL_MAP = {'None': Vul.none, 'Love': Vul.none, '-': Vul.none, '': Vul.none,
           'NS': Vul.ns, 'N-S': Vul.ns, 'EW': Vul.ew, 'E-W': Vul.ew,
           'All': Vul.both, 'Both': Vul.both}
DEALER_MAP = {'N': Player.north, 'E': Player.east, 'S': Player.south, 'W': Player.west}
VUL_BOOLS = {Vul.none: [False, False], Vul.ns: [True, False],
             Vul.ew: [False, True], Vul.both: [True, True]}


def _tricks_bytes(table):
    return bytes(table[d, p] for p in PLAYERS for d in DENOMS)


def _par_lines(table, vul, dealer):
    """Return ('[OptimumScore "..."]', '[ParContract "..."]') from a DD table."""
    p = par(table, vul, dealer)
    s = p.score  # from the N/S perspective
    opt = f'NS {s}' if s > 0 else (f'EW {-s}' if s < 0 else 'NS 0')
    contracts = list(p)
    if contracts:
        c = contracts[0]
        side = 'NS' if c.declarer in (Player.north, Player.south) else 'EW'
        denom = 'N' if c.denom == Denom.nt else c.denom.abbr
        dbl = 'x' if c.penalty == Penalty.doubled else ('xx' if c.penalty == Penalty.redoubled else '')
        r = c.result
        res = '=' if r == 0 else (f'+{r}' if r > 0 else f'{r}')
        parc = f'{side} {c.level}{denom}{dbl}{res}'
    else:
        parc = 'Pass'
    return f'[OptimumScore "{opt}"]', f'[ParContract "{parc}"]'


def _solve_worker(task):
    """Solve one strided slice of (deal, vul, dealer); checkpoint to own pickle."""
    idx, items, ckpt = task
    solved = {}
    if os.path.exists(ckpt):
        try:
            with open(ckpt, 'rb') as f:
                solved = pickle.load(f)
        except Exception:
            solved = {}

    def flush():
        tmp = ckpt + '.tmp'
        with open(tmp, 'wb') as f:
            pickle.dump(solved, f, pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, ckpt)

    todo = [it for it in items if it[0] not in solved]
    buf, since, t0 = [], 0, time.time()

    def drain():
        for (dobj, dstr, vul, dealer), tbl in zip(buf, calc_all_tables([b[0] for b in buf])):
            opt_line, par_line = _par_lines(tbl, vul, dealer)
            solved[dstr] = (opt_line, par_line, VUL_BOOLS[vul], _tricks_bytes(tbl))
        buf.clear()

    for dstr, vname, dname in todo:
        vul = VUL_MAP.get(vname, Vul.none)
        dealer = DEALER_MAP.get(dname, Player.north)
        try:
            dobj = Deal(dstr)
        except Exception:
            continue
        buf.append((dobj, dstr, vul, dealer))
        if len(buf) >= CHUNK:
            drain()
            since += CHUNK
            if since >= CHECKPOINT_EVERY:
                flush()
                since = 0
                print(f"  [w{idx}] {len(solved)}/{len(items)} ({time.time()-t0:.0f}s)", flush=True)
    if buf:
        drain()
    flush()
    return ckpt


def compute_entries(items, ckpt_dir):
    """Solve every (deal, vul, dealer) across WORKERS processes.

    Returns {deal_str: (OptimumScore, ParContract, vul, dd_bytes)} and the
    checkpoint paths used.
    """
    tasks = [(i, items[i::WORKERS], os.path.join(ckpt_dir, f'datum_ckpt_{i}.pkl'))
             for i in range(WORKERS)]
    if WORKERS <= 1:
        results = [_solve_worker(tasks[0])]
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(WORKERS) as pool:
            results = pool.map(_solve_worker, tasks)

    entries = {}
    for ckpt in results:
        with open(ckpt, 'rb') as f:
            entries.update(pickle.load(f))
    return entries, [t[2] for t in tasks]


def parse_pbn(path):
    """Yield unique (deal_str, vulnerable, dealer) tuples, one per distinct deal."""
    items, seen = [], set()
    deal = vul = dealer = None
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s.startswith('[Deal '):
                deal = s.split('"')[1]
            elif s.startswith('[Vulnerable '):
                vul = s.split('"')[1]
            elif s.startswith('[Dealer '):
                dealer = s.split('"')[1]
            elif s == '':
                if deal and deal not in seen:
                    seen.add(deal)
                    items.append((deal, vul or 'None', dealer or 'N'))
                deal = vul = dealer = None
    if deal and deal not in seen:
        items.append((deal, vul or 'None', dealer or 'N'))
    return items


def add_pbn(pbn_path, pickle_path):
    items = parse_pbn(pbn_path)
    print(f"{len(items)} unique deals in {os.path.basename(pbn_path)}", flush=True)

    if os.path.exists(pickle_path):
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
    else:
        data = {}
    # Only compute deals not already in the pickle.
    todo = [it for it in items if f'[Deal "{it[0]}"]' not in data]
    print(f"{len(todo)} to compute on {WORKERS} worker(s) "
          f"({len(data)} existing entries)", flush=True)
    if not todo:
        print("Nothing to add - every deal is already in the pickle.")
        return

    ckpt_dir = os.path.dirname(os.path.abspath(pickle_path))
    t0 = time.time()
    entries, ckpts = compute_entries(todo, ckpt_dir)
    print(f"solved {len(entries)} deals in {time.time()-t0:.0f}s", flush=True)

    added = 0
    for dstr, val in entries.items():
        key = f'[Deal "{dstr}"]'
        if key not in data:
            data[key] = val
            added += 1

    # Keep a one-time backup, then write atomically.
    backup = pickle_path + '.bak'
    if os.path.exists(pickle_path) and not os.path.exists(backup):
        shutil.copy2(pickle_path, backup)
        print(f"backed up original to {backup}", flush=True)
    tmp = pickle_path + '.tmp'
    with open(tmp, 'wb') as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, pickle_path)
    print(f"added {added} entries; pickle now has {len(data)}", flush=True)

    if len(entries) >= len(todo):
        for c in ckpts:
            try:
                os.remove(c)
            except OSError:
                pass


def main():
    print("Compute Datum Scores, Version 1.0.19")

    # Command-line usage: ComputeDatumScores.py <input.pbn> [DatumScores.pkl]
    if len(sys.argv) > 1:
        pbn_path = sys.argv[1]
        pickle_path = sys.argv[2] if len(sys.argv) > 2 else 'DatumScores.pkl'
        add_pbn(pbn_path, pickle_path)
        return

    root = tk.Tk()
    root.withdraw()

    pbn_path = filedialog.askopenfilename(
        title="Select the PBN file whose deals to compute",
        initialdir=lastdir.get_last_dir(key="extract"),
        filetypes=[("PBN files", "*.pbn"), ("All files", "*.*")],
    )
    if not pbn_path:
        sys.exit(1)
    lastdir.set_last_dir(pbn_path, key="extract")

    pickle_path = filedialog.askopenfilename(
        title="Select the datum-score pickle to add to",
        initialdir=os.path.dirname(pbn_path),
        filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")],
    )
    if not pickle_path:
        sys.exit(1)

    add_pbn(pbn_path, pickle_path)


if __name__ == "__main__":
    main()
