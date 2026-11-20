"""Double-dummy solve a PBN's deals and add their tricks to DatumScores.pkl.

For every deal in the PBN that the pickle has no tricks for yet, this solves the full
double-dummy table and stores it:

    key   = '[Deal "..."]'
    value = 20 bytes, one trick count per (declarer, denomination), N/E/S/W x S/H/D/C/NT

Only the tricks are stored -- they belong to the deal alone. [OptimumScore] and
[ParContract] depend on the board's vulnerability and dealer, so AddDatumScoreToPBN,
UpdateScore and Split_PBN compute them from these tricks for each board they handle.
(This tool used to store the par it computed for the FIRST copy of each deal, so every
other copy of the deal, at another vulnerability, inherited the wrong par.)

Deals are solved once each, however many boards share them. Afterwards
AddDatumScoreToPBN.py can write the tags into any PBN whose deals are in the pickle.

This is the expensive, one-time step (hours for a large file). It is resumable:
worker checkpoints (`datum_ckpt_*.pkl`) let an interrupted run continue, and the
pickle is backed up to `DatumScores.pkl.bak` and replaced atomically. Old-format
entries that already carry a table are rewritten as plain tricks on the way.

Usage: ComputeDatumScores.py <input.pbn> [DatumScores.pkl]
Env:   DD_WORKERS (default 2)   -- DDS already threads internally, so 2 is the
       sweet spot on a many-core box; 3+ oversubscribes and slows down.
"""
import sys
import os
import time
import pickle
import multiprocessing as mp
import tkinter as tk
from tkinter import filedialog
import lastdir
import endplay.config as config
import endplayfix  # local endplay fixes (dealer tag, auction NAGs, LIN mn||)
config.use_unicode = False
from endplay.types import Deal, Denom, Player
from endplay.dds import calc_all_tables
import datumscore

# Deals solved per DDS batch call (DDS caps CalcAllTables at 32).
CHUNK = 32
WORKERS = int(os.environ.get("DD_WORKERS", "2"))
# Flush a worker checkpoint every this many freshly solved deals.
CHECKPOINT_EVERY = 6400

# Packing order of the 20 bytes (datumscore.PLAYER_ORDER x DENOM_ORDER).
PLAYERS = [Player.north, Player.east, Player.south, Player.west]
DENOMS = [Denom.spades, Denom.hearts, Denom.diamonds, Denom.clubs, Denom.nt]


def _tricks_bytes(table):
    return bytes(table[d, p] for p in PLAYERS for d in DENOMS)


def _solve_worker(task):
    """Solve one strided slice of deal strings; checkpoint to own pickle."""
    idx, deal_strs, ckpt = task
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

    todo = [s for s in deal_strs if s not in solved]
    buf, since, t0 = [], 0, time.time()

    def drain():
        for (_, dstr), tbl in zip(buf, calc_all_tables([b[0] for b in buf])):
            solved[dstr] = _tricks_bytes(tbl)
        buf.clear()

    for dstr in todo:
        try:
            dobj = Deal(dstr)
        except Exception:
            continue
        buf.append((dobj, dstr))
        if len(buf) >= CHUNK:
            drain()
            since += CHUNK
            if since >= CHECKPOINT_EVERY:
                flush()
                since = 0
                print(f"  [w{idx}] {len(solved)}/{len(deal_strs)} ({time.time()-t0:.0f}s)", flush=True)
    if buf:
        drain()
    flush()
    return ckpt


def compute_entries(deal_strs, ckpt_dir):
    """Solve every deal string across WORKERS processes.

    Returns {deal_str: dd_bytes} and the checkpoint paths used."""
    # Strided split is deterministic, so a resumed run rebuilds the same slices.
    tasks = [(i, deal_strs[i::WORKERS], os.path.join(ckpt_dir, f'datum_ckpt_{i}.pkl'))
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
    """The distinct deal strings of a PBN, in file order. Vulnerability and dealer are
    not read: the tricks do not depend on them."""
    deals, seen = [], set()
    with open(path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            s = line.strip()
            if s.startswith('[Deal '):
                deal = s.split('"')[1]
                if deal not in seen:
                    seen.add(deal)
                    deals.append(deal)
    return deals


def add_pbn(pbn_path, pickle_path):
    deals = parse_pbn(pbn_path)
    print(f"{len(deals)} unique deals in {os.path.basename(pbn_path)}", flush=True)

    data = datumscore.load(pickle_path) if os.path.exists(pickle_path) else {}
    converted = datumscore.normalise(data)
    if converted:
        print(f"rewrote {converted} old-format entries as plain tricks", flush=True)
    # Only solve deals the pickle holds no tricks for.
    todo = [d for d in deals if datumscore.tricks_of(data.get(datumscore.deal_key(d))) is None]
    print(f"{len(todo)} to compute on {WORKERS} worker(s) "
          f"({len(data)} existing entries)", flush=True)
    if not todo:
        if converted:
            datumscore.save(data, pickle_path)
        print("Nothing to add - every deal already has its tricks in the pickle.")
        return

    ckpt_dir = os.path.dirname(os.path.abspath(pickle_path))
    t0 = time.time()
    entries, ckpts = compute_entries(todo, ckpt_dir)
    print(f"solved {len(entries)} deals in {time.time()-t0:.0f}s", flush=True)

    for dstr, dd in entries.items():
        data[datumscore.deal_key(dstr)] = dd
    datumscore.save(data, pickle_path)
    print(f"added {len(entries)} entries; pickle now has {len(data)}", flush=True)

    if len(entries) >= len(todo):
        for c in ckpts:
            try:
                os.remove(c)
            except OSError:
                pass


def main():
    print("Compute Datum Scores, Version 1.0.24")

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
