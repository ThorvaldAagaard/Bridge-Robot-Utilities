"""Add the double-dummy tables a PBN already carries to DatumScores.pkl.

Every board with a complete 20-row [OptimumResultTable] contributes its deal's tricks:

    key   = '[Deal "..."]'
    value = 20 bytes, one trick count per (declarer, denomination), N/E/S/W x S/H/D/C/NT

No solving, so it is instant. Boards without a table are counted and left out --
run ComputeDatumScores.py on the file to solve those.

It used to copy [OptimumScore]/[ParContract] into the pickle instead. Par depends on
the board's vulnerability and dealer, and the pickle is keyed by the deal, so a
deal that recurs at another vulnerability got the wrong par; the scores are now
computed per board from the tricks (datumscore.py).

Usage: ExtractDatumScore.py [<input.pbn> [DatumScores.pkl]]   (no arguments: file dialog,
       pickle DatumScores.pkl in the current folder)
"""
import sys
import os
import tkinter as tk
from tkinter import filedialog
import lastdir
import datumscore


def extract_data(file_path, output_path):
    data = datumscore.load(output_path) if os.path.exists(output_path) else {}
    converted = datumscore.normalise(data)

    counts = {'boards': 0, 'added': 0, 'known': 0, 'no_table': 0, 'conflict': 0}
    deal = None
    rows = {}

    def flush():
        nonlocal deal, rows
        if deal is not None:
            counts['boards'] += 1
            dd = datumscore.tricks_from_ort(rows)
            if dd is None:
                counts['no_table'] += 1
            else:
                key = datumscore.deal_key(deal)
                have = datumscore.tricks_of(data.get(key))
                if have is None:
                    data[key] = dd
                    counts['added'] += 1
                elif have == dd:
                    counts['known'] += 1
                else:
                    # One deal has one double-dummy table; two that differ means one of
                    # the sources is wrong. Keep what the pickle has and report it.
                    counts['conflict'] += 1
                    if counts['conflict'] <= 10:
                        print(f"  conflicting table for {key}; pickle kept")
        deal, rows = None, {}

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            s = line.strip()
            if s.startswith('[Board ') or s == '':
                if s.startswith('[Board ') or deal is not None:
                    flush()
                continue
            if s.startswith('[Deal '):
                deal = s.split('"')[1]
                continue
            parts = s.split()
            if len(parts) == 3 and parts[0] in datumscore.PLAYER_ORDER \
                    and parts[1] in datumscore.DENOM_ORDER and parts[2].isdigit():
                rows[(parts[0], parts[1])] = int(parts[2])
    flush()

    if counts['added'] or converted:
        datumscore.save(data, output_path)
    print(f"{counts['boards']} boards: {counts['added']} deals added, {counts['known']} already in the "
          f"pickle, {counts['no_table']} without a complete OptimumResultTable "
          f"(run ComputeDatumScores on them), {counts['conflict']} conflicting")
    if converted:
        print(f"rewrote {converted} old-format entries as plain tricks")
    print(f"Updated data saved to {output_path} ({len(data)} entries)")


def main():

    print("Extract Datum Score, Version 1.0.24")

    if len(sys.argv) > 1:
        extract_data(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'DatumScores.pkl')
        return

    # create a root window
    root = tk.Tk()
    root.withdraw()

    file_types = [
        ("PBN files", "*.pbn"),
        ("All files", "*.*")
    ]
    file_path = filedialog.askopenfilename(initialdir=lastdir.get_last_dir(key="extract"), filetypes=file_types)
    if file_path:
        lastdir.set_last_dir(file_path, key="extract")
    if not file_path:
        sys.exit(1)

    extract_data(file_path, 'DatumScores.pkl')


if __name__ == "__main__":
    main()
