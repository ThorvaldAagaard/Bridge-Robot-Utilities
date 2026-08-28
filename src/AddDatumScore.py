import sys
import os
import re
import pickle
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import lastdir

# How often (bytes of input consumed) to emit a progress update.
PROGRESS_EVERY = 16 * 1024 * 1024

# A generated OptimumResultTable data row, e.g. "N S 5" or "E H -9752".
ORT_ROW = re.compile(r'^[NESW]\s+(?:NT|S|H|D|C)\s+-?\d+$')


def load_optimumscores(pickle_path):
    with open(pickle_path, 'rb') as pkl_file:
        return pickle.load(pkl_file)


# Row order of the standard PBN OptimumResultTable: 4 declarers x 5 denominations.
# Must match the packing order used when the dd bytes were computed.
ORT_HEADER = '[OptimumResultTable "Declarer Denomination Result"]'
ROW_LABELS = [(p, d) for p in ('N', 'E', 'S', 'W')
              for d in ('S', 'H', 'D', 'C', 'NT')]


def tag_value(line):
    """Return the quoted value of a full PBN tag line, or None."""
    if not line:
        return None
    parts = line.split('"')
    return parts[1] if len(parts) > 1 else None


def lookup(data, deal_line):
    """Find the datum-score entry for a `[Deal "..."]` line.

    The pickle (built by ExtractDatumScore.py) is keyed by the exact deal line.
    Try that verbatim first, then fall back to the endplay-canonical form so a
    differently formatted deal still matches (same lookup Split_PBN.py relies on).

    Returns (optimum_score, par_contract, dd_bytes). dd_bytes is the 20-byte
    double-dummy table when the entry has been enriched with one, else None.
    """
    value = data.get(deal_line)
    if value is None:
        deal_str = tag_value(deal_line)
        if deal_str:
            try:
                from endplay.types import Deal
                value = data.get(f'[Deal "{Deal(deal_str).to_pbn()}"]')
            except Exception:
                value = None
    if value is None:
        return None, None, None
    optimum_score, par_contract = value[0], value[1]
    dd_bytes = value[3] if len(value) > 3 else None
    return tag_value(optimum_score), tag_value(par_contract), dd_bytes


def build_ort(dd_bytes, term):
    """Render the OptimumResultTable tag + 20 rows from packed dd bytes."""
    lines = [f'{ORT_HEADER}{term}']
    for (decl, denom), t in zip(ROW_LABELS, dd_bytes):
        lines.append(f'{decl} {denom} {t}{term}')
    return lines


def strip_existing(block):
    """Drop pre-existing OptimumScore/ParContract tags and any OptimumResultTable
    block (its tag plus data rows), so re-running is idempotent."""
    out = []
    i = 0
    while i < len(block):
        stripped = block[i].lstrip()
        if stripped.startswith('[OptimumResultTable'):
            i += 1
            while i < len(block) and ORT_ROW.match(block[i].strip()):
                i += 1
            continue
        if stripped.startswith('[OptimumScore') or stripped.startswith('[ParContract'):
            i += 1
            continue
        out.append(block[i])
        i += 1
    return out


def annotate(pbn_path, pickle_path, output_path, on_status=None, on_progress=None):
    """Write OptimumScore / ParContract into every board, as a single PBN file.

    Works line-by-line as a text edit so every other tag, comment, auction and
    play line is preserved byte-for-byte (endplay's load/dump would drop the
    non-standard tags and reject the 'T1'-style board labels). Streams one board
    at a time to keep memory flat on very large files.

    on_status(text) reports the current phase; on_progress(percent, boards) is
    called periodically while streaming. Both default to console output.
    """
    def status(msg):
        if on_status:
            on_status(msg)
        else:
            print(msg, flush=True)

    status("Loading datum scores ...")
    data = load_optimumscores(pickle_path)

    total = max(os.path.getsize(pbn_path), 1)
    status("Annotating boards ...")

    updated = 0
    missing = 0

    def flush_block(block, out):
        nonlocal updated, missing
        if not block:
            return
        deal_idx = next(
            (i for i, l in enumerate(block) if l.lstrip().startswith('[Deal ')), None)
        if deal_idx is None:
            out.writelines(block)
            return
        deal_line = block[deal_idx]
        opt, par, dd_bytes = lookup(data, deal_line.strip())
        if opt is None:
            missing += 1
            out.writelines(block)
            return
        # Preserve the original line terminator when building new tag lines.
        term = deal_line[len(deal_line.rstrip('\r\n')):] or '\n'
        block = strip_existing(block)
        di = next(i for i, l in enumerate(block) if l.lstrip().startswith('[Deal '))
        inserts = [f'[OptimumScore "{opt}"]{term}']
        if par is not None:
            inserts.append(f'[ParContract "{par}"]{term}')
        if dd_bytes:
            inserts.extend(build_ort(dd_bytes, term))
        block[di + 1:di + 1] = inserts
        out.writelines(block)
        updated += 1

    done = 0
    next_report = 0
    with open(pbn_path, 'r', encoding='utf-8', newline='') as fin, \
            open(output_path, 'w', encoding='utf-8', newline='') as fout:
        block = []
        for line in fin:
            done += len(line)
            if line.strip() == '':
                flush_block(block, fout)
                block = []
                fout.write(line)
            else:
                block.append(line)
            if done >= next_report:
                pct = min(100, int(done * 100 / total))
                if on_progress:
                    on_progress(pct, updated)
                else:
                    print(f"\r  {pct}%  ({updated} boards)", end="", flush=True)
                next_report = done + PROGRESS_EVERY
        flush_block(block, fout)
    if on_progress is None:
        print(flush=True)

    status(f"{updated} boards updated, {missing} without a datum score.")
    status(f"{output_path} generated")


def main():
    print("Add Datum Score, Version 1.0.19")

    # Command-line usage: AddDatumScore.py <input.pbn> [DatumScores.pkl] [output.pbn]
    if len(sys.argv) > 1:
        pbn_path = sys.argv[1]
        pickle_path = sys.argv[2] if len(sys.argv) > 2 else 'DatumScores.pkl'
        output_path = sys.argv[3] if len(sys.argv) > 3 else f"{os.path.splitext(pbn_path)[0]}-DD.pbn"
        annotate(pbn_path, pickle_path, output_path)
        return

    root = tk.Tk()
    root.withdraw()

    file_types = [
        ("PBN files", "*.pbn"),
        ("All files", "*.*"),
    ]

    pbn_path = filedialog.askopenfilename(
        title="Select the PBN file to annotate",
        initialdir=lastdir.get_last_dir(key="extract"),
        filetypes=file_types,
    )
    if not pbn_path:
        sys.exit(1)
    lastdir.set_last_dir(pbn_path, key="extract")

    pickle_path = filedialog.askopenfilename(
        title="Select the datum-score pickle",
        initialdir=os.path.dirname(pbn_path),
        filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")],
    )
    if not pickle_path:
        sys.exit(1)

    directory = os.path.dirname(pbn_path)
    default_name = f"{os.path.splitext(os.path.basename(pbn_path))[0]}-DD.pbn"
    output_file = filedialog.asksaveasfilename(
        defaultextension=".pbn",
        initialdir=directory,
        initialfile=default_name,
        filetypes=file_types,
    )
    if not output_file:
        return

    # Progress window: a marquee while the pickle loads, then a determinate bar
    # driven by how much of the input file has been streamed.
    progress_window = tk.Toplevel(root)
    progress_window.title("Add Datum Score")
    bar = ttk.Progressbar(progress_window, orient="horizontal", length=340,
                          mode="indeterminate")
    bar.pack(pady=20, padx=20)
    bar.start(12)
    status_label = tk.Label(progress_window, text="Starting ...")
    status_label.pack(pady=(0, 12), padx=20)

    state = {"determinate": False}

    def on_status(msg):
        status_label.config(text=msg)

    def on_progress(pct, boards):
        if not state["determinate"]:
            bar.stop()
            bar.config(mode="determinate", maximum=100)
            state["determinate"] = True
        bar["value"] = pct
        status_label.config(text=f"Annotating boards ... {pct}%  ({boards} boards)")

    thread = threading.Thread(
        target=annotate,
        args=(pbn_path, pickle_path, output_file, on_status, on_progress))
    thread.start()

    root.after(100, check_thread_status, thread, root)
    root.mainloop()
    root.destroy()


def check_thread_status(thread, root):
    if thread.is_alive():
        root.after(100, check_thread_status, thread, root)
    else:
        root.quit()


if __name__ == "__main__":
    main()
