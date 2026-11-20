"""Bring DatumScores.pkl to its current format: one double-dummy table per deal.

The pickle maps each `[Deal "..."]` line to 20 bytes of tricks (see datumscore.py).
Older pickles hold (OptimumScore, ParContract, vul[, dd_bytes]) tuples instead, and
their stored par is wrong for any copy of a deal at another vulnerability or with
another dealer. This tool double-dummy solves every entry that has no table and
rewrites EVERY value as plain tricks, dropping the stored par: AddDatumScoreToPBN,
UpdateScore and Split_PBN compute par per board from the tricks.

Run it once on an old pickle (`python src/ComputeDDTables.py DatumScores.pkl`); on a
current one it is a no-op. The solve is resumable - worker checkpoints let an
interrupted run continue where it left off.
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
# Worker processes. DDS already threads internally (~13x), so 2 is the sweet
# spot on a many-core box; 3+ oversubscribes and slows down. Override with
# DD_WORKERS.
WORKERS = int(os.environ.get("DD_WORKERS", "2"))
# Flush a worker checkpoint every this many freshly solved deals (resume support).
CHECKPOINT_EVERY = 6400

# Packing order of the 20 bytes: 4 declarers x 5 denominations. AddDatumScoreToPBN.py
# unpacks in this same order, so keep the two in sync.
PLAYERS = [Player.north, Player.east, Player.south, Player.west]
DENOMS = [Denom.spades, Denom.hearts, Denom.diamonds, Denom.clubs, Denom.nt]


def tag_value(line):
    if not line:
        return None
    parts = line.split('"')
    return parts[1] if len(parts) > 1 else None


def _tricks_bytes(table):
    return bytes(table[d, p] for p in PLAYERS for d in DENOMS)


def _solve_worker(task):
    """Solve one strided slice of deal strings, checkpointing to its own pickle."""
    idx, deal_strs, ckpt_path = task
    solved = {}
    if os.path.exists(ckpt_path):
        try:
            with open(ckpt_path, 'rb') as f:
                solved = pickle.load(f)
        except Exception:
            solved = {}

    def flush():
        tmp = ckpt_path + '.tmp'
        with open(tmp, 'wb') as f:
            pickle.dump(solved, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, ckpt_path)

    todo = [s for s in deal_strs if s not in solved]
    buf_deals, buf_keys, since = [], [], 0
    t0 = time.time()

    def drain():
        for k, tbl in zip(buf_keys, calc_all_tables(buf_deals)):
            solved[k] = _tricks_bytes(tbl)
        buf_deals.clear()
        buf_keys.clear()

    for s in todo:
        try:
            d = Deal(s)
        except Exception:
            continue
        buf_deals.append(d)
        buf_keys.append(s)
        if len(buf_deals) >= CHUNK:
            drain()
            since += CHUNK
            if since >= CHECKPOINT_EVERY:
                flush()
                since = 0
                print(f"  [w{idx}] {len(solved)}/{len(deal_strs)} "
                      f"({time.time()-t0:.0f}s)", flush=True)
    if buf_deals:
        drain()
    flush()
    return ckpt_path


def compute_tables(unique, ckpt_dir):
    """Solve every unique deal string across WORKERS processes; returns
    {deal_str: dd_bytes} and the checkpoint paths used."""
    tasks = []
    for i in range(WORKERS):
        # Strided split is deterministic, so a resumed run rebuilds the same
        # slices and reuses each worker's checkpoint.
        tasks.append((i, unique[i::WORKERS],
                      os.path.join(ckpt_dir, f'dd_ckpt_{i}.pkl')))

    if WORKERS <= 1:
        results = [_solve_worker(tasks[0])]
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(WORKERS) as pool:
            results = pool.map(_solve_worker, tasks)

    tables = {}
    for ckpt_path in results:
        with open(ckpt_path, 'rb') as f:
            tables.update(pickle.load(f))
    return tables, [t[2] for t in tasks]


def enrich(pickle_path):
    data = datumscore.load(pickle_path)

    todo_keys = [k for k, v in data.items() if datumscore.tricks_of(v) is None]
    print(f"{len(data)} pickle entries, {len(todo_keys)} need a DD table "
          f"on {WORKERS} worker(s)")

    filled = 0
    ckpts = []
    if todo_keys:
        unique = [tag_value(k) for k in todo_keys]
        ckpt_dir = os.path.dirname(os.path.abspath(pickle_path))
        t0 = time.time()
        tables, ckpts = compute_tables(unique, ckpt_dir)
        print(f"solved {len(tables)} deals in {time.time()-t0:.0f}s")
        for k in todo_keys:
            dd = tables.get(tag_value(k))
            if dd is not None:
                data[k] = dd
                filled += 1

    converted = datumscore.normalise(data)
    if not filled and not converted:
        print("Nothing to do - every entry is already plain tricks.")
        return
    datumscore.save(data, pickle_path)
    print(f"solved {filled} entries, rewrote {converted} old-format entries as plain tricks; "
          f"{len(todo_keys) - filled} unsolved")

    if filled == len(todo_keys):
        for c in ckpts:
            try:
                os.remove(c)
            except OSError:
                pass


def main():
    print("Compute DD Tables, Version 1.0.24")

    # Command-line usage: ComputeDDTables.py [DatumScores.pkl]
    if len(sys.argv) > 1:
        enrich(sys.argv[1])
        return

    root = tk.Tk()
    root.withdraw()
    pickle_path = filedialog.askopenfilename(
        title="Select the datum-score pickle to enrich",
        initialdir=lastdir.get_last_dir(key="extract"),
        filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")],
    )
    if not pickle_path:
        sys.exit(1)
    enrich(pickle_path)


if __name__ == "__main__":
    main()
