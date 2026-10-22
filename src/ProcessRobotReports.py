"""File a robot's match reports: save each match, extract its boards, and rebuild the merged board files.

A report folder (for example D:\\RobotMatches\\Eamon) receives Brill TMClient report zips
(BrillTM_*.zip, with the match at match.pbn in the zip) and plain match PBNs. For each one:

  1. the match is saved in Boards\\<name>.matches          (Brill_versus_<robot>_<label>_<start>_match.pbn)
  2. its boards are extracted to Boards\\All-<name>.PBN    (Extract_<match file>, as PbnExtractBoards does)
  3. the report is moved to Processed

The robot in the name is the one in the player tags, not the one the match was named after: a match
called WB5_2_sep26_match21 was played against Lia. The [Event] tag is rewritten to agree. --rename
applies the same naming to everything already filed: match files, extracts and the zips in Processed.

and then every Extract_*.pbn is merged into All.PBN (as MergePBNFiles does) and renumbered, without
duplicate or incomplete deals, into Ordered_All.PBN (as ResetAndRenumberPBNBoards does) -- the deck a
seat match plays. The extracts are merged in the order the matches were played, so a new match only
adds boards at the end. The same pair is built per robot in Boards\\All-<name>.PBN\\<robot>.

A match already in <name>.matches is not saved again: a zip is recognised by the start time in its
name (a match is often saved under another name), a PBN by its file name. A match file without an
extract gets one, so running the script again finishes whatever an earlier run, or a manual filing,
left half done.
"""
import argparse
import contextlib
import io
import os
import re
import shutil
import sys
import zipfile
from collections import Counter

import endplay.parsers.pbn as pbn
import endplayfix  # endplay drops [Dealer] on boards without a contract

import MergePBNFiles
import PbnExtractBoards
import ResetAndRenumberPBNBoards

# The start time TMClient puts in a match name: 2026-10-20_00-45-46
START_STAMP = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')
# BrillTM_<match name>_<start>_<saved yyyymmdd_hhmmss>.zip
REPORT_ZIP = re.compile(r'^BrillTM_(?P<match>.+)_(?P<saved>\d{8}_\d{6})\.zip$', re.IGNORECASE)
# Any date and time in a file name, for the order the extracts are merged in
PLAYED = re.compile(r'(\d{4})-(\d{2})-(\d{2})[_-](\d{2})-(\d{2})(?:-(\d{2}))?')
PLAYER = re.compile(r'^\[(West|North|East|South) "([^"]*)"\]', re.MULTILINE)
EMPTY_TAG = re.compile(r'^\[\w+\s+""\]\s*$')
EVENT = re.compile(r'^\[Event "[^"]*?( \((?:Open|Closed)\))?"\]', re.MULTILINE)
# A plain PBN from the RoboBridge table manager: .2026-10-16-16-56.Brill NS-Pidgin.pbn
ROBOBRIDGE_PBN = re.compile(r'^\.?(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})\.Brill NS-.+\.pbn$', re.IGNORECASE)
# The robot a match label opens with (the part of the name the robot replaces), longest spelling first
ROBOT_IN_LABEL = re.compile(r'^(?:WB5_2|WB5_L4|Wb5_L2|WB5|WBridge5|WBridge|GIB620|GIB|Lia48|Lia|Pidgin'
                            r'|Bridge_Baron|BBO_Ben|BEN_2|Ben21)(?:_|$)', re.IGNORECASE)
# The robot of an extract, from the name its match was filed under
EXTRACT_ROBOT = re.compile(r'^Extract_Brill_versus_([^_]+)_')
# Robots that sit at the table under another name
ROBOT_ALIASES = {'jackos': 'Q-Plus'}


def is_audit(name):
    return '_audit' in name.lower()


def load_boards(text):
    """The boards of a PBN text, read the way the extract tool reads them.

    Tags with an empty value are dropped: BridgeComposer writes [Result ""] on an unplayed board,
    which endplay cannot read, and the extract needs only the deal, dealer and vulnerability.
    So is a board with neither a number nor a card, which BridgeComposer leaves after the last one.
    """
    text = ''.join(line for line in text.splitlines(keepends=True)
                   if not line.startswith('{Feasability:') and not EMPTY_TAG.match(line))
    return [board for board in pbn.load(io.StringIO(text))
            if board.board_num is not None or re.search(r'[AKQJT2-9]', board.deal.to_pbn()[2:])]


def read_text(path):
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        return f.read()


def canonical_robot(player):
    """One name per robot: 'WBridge5 W' and 'WBridge5' are the same robot, as are BEN-21GF builds."""
    name = re.sub(r'\s+[NESW]$', '', player.strip())
    if name.upper().startswith('BEN-21GF'):
        return 'BEN-21GF'
    return ROBOT_ALIASES.get(name.lower(), name)


def opponent(text):
    """The robot Brill played, from the player tags (never trust the match name)."""
    names = Counter(canonical_robot(m.group(2)) for m in PLAYER.finditer(text)
                    if m.group(2) and not m.group(2).startswith('Brill'))
    return names.most_common(1)[0][0] if names else '?'


def canonical_name(file_name, text):
    """(stem, tail) of the name a match file should have: Brill_versus_<robot>_<label>_<start> + _match.pbn.

    The label is the match's own name with its robot removed; the tail keeps an audit file's suffix.
    None when the name carries no start time to anchor it.
    """
    start = START_STAMP.search(file_name)
    if start:
        label, stamp, tail = file_name[:start.start()], start.group(0), file_name[start.end():]
        label = re.sub(r'^Brill_versus_', '', label).strip('_')
        if label.lower() == 'match':  # BrillTM_Match_<start>: a match given no name
            label = ''
    else:
        m = ROBOBRIDGE_PBN.match(file_name)
        if not m:
            return None
        label, stamp, tail = 'robobridge', f'{m.group(1)}_{m.group(2)}-{m.group(3)}', '_match.pbn'
    robot = opponent(text)
    # Strip the robot in any spelling, the canonical one included, so renaming twice changes nothing
    while True:
        stripped = re.sub(rf'^{re.escape(robot)}(?:_|$)', '', ROBOT_IN_LABEL.sub('', label), flags=re.IGNORECASE)
        if stripped == label:
            break
        label = stripped
    label = re.sub(r'(?<=[a-z\d])match(?=\d)', '_match', label, flags=re.IGNORECASE)
    return '_'.join(part for part in ('Brill_versus', robot, label, stamp) if part), tail


def with_event(text, stem):
    """The text with every [Event] naming the robot and label of stem, keeping each room."""
    event = 'Brill versus ' + START_STAMP.sub('', stem.replace('Brill_versus_', '', 1)).strip('_')
    event = re.sub(r'_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}$', '', event)  # a RoboBridge start has no seconds
    return EVENT.sub(lambda m: f'[Event "{event}{m.group(1) or ""}"]', text)


def played_key(path):
    """Sort key: when the match was played, from its name, else the file's time."""
    m = PLAYED.search(os.path.basename(path))
    if m:
        return tuple(int(g or 0) for g in m.groups())
    return (9999,) + tuple(int(x) for x in [os.path.getmtime(path)])


class Filer:
    def __init__(self, root, name, dry_run):
        self.root = root
        self.dry_run = dry_run
        self.matches_dir = os.path.join(root, 'Boards', f'{name}.matches')
        self.boards_dir = os.path.join(root, 'Boards', f'All-{name}.PBN')
        self.processed_dir = os.path.join(root, 'Processed')
        self.saved = []      # (match file, opponent, boards)
        self.extracted = []
        self.skipped = []    # (report, reason)
        self.failed = []     # (file, error)
        self.moved = 0

    def act(self, what, func, *args):
        print(('(dry run) ' if self.dry_run else '') + what)
        if not self.dry_run:
            func(*args)

    def known_starts(self):
        return {m.group(0) for f in os.listdir(self.matches_dir) for m in [START_STAMP.search(f)] if m}

    def move_to_processed(self, path, name=None):
        target = os.path.join(self.processed_dir, name or os.path.basename(path))
        if os.path.exists(target):
            self.failed.append((path, f'not moved, {target} already exists'))
            return
        self.act(f'Move {os.path.basename(path)} -> Processed\\{os.path.basename(target)}', shutil.move, path, target)
        self.moved += 1

    def save_match(self, target, text):
        def write():
            with open(target, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
        self.act(f'Save {os.path.basename(target)}', write)

    def named(self, file_name, text):
        """The file name a match should be saved under, and its text with the [Event] to match."""
        canonical = canonical_name(file_name, text)
        if canonical is None:
            return file_name, text
        stem, tail = canonical
        return stem + tail, with_event(text, stem)

    # --- reports ---------------------------------------------------------

    def file_zips(self):
        reports = {}
        for f in sorted(os.listdir(self.root)):
            path = os.path.join(self.root, f)
            if not f.lower().endswith('.zip') or not os.path.isfile(path):
                continue
            m = REPORT_ZIP.match(f)
            if not m:
                self.skipped.append((f, 'not a BrillTM report'))
                continue
            start = START_STAMP.search(m.group('match'))
            # Several reports of one match: keep the last one saved, file the others with it
            key = start.group(0) if start else m.group('match')
            reports.setdefault(key, []).append((m.group('saved'), path, m.group('match')))

        known = self.known_starts()
        for start, versions in sorted(reports.items()):
            versions.sort()
            saved, path, match_name = versions[-1]
            try:
                with zipfile.ZipFile(path) as z:
                    if 'match.pbn' not in z.namelist():
                        for _, p, _ in versions:
                            self.skipped.append((os.path.basename(p), 'no match.pbn in the zip (older report format)'))
                        continue
                    data = z.read('match.pbn')
            except (zipfile.BadZipFile, OSError) as e:
                self.failed.append((path, str(e)))
                continue

            if data.startswith(b'\xef\xbb\xbf'):
                data = data[3:]
            name, text = self.named(f'{match_name}_match.pbn', data.decode('utf-8', errors='replace'))
            target = os.path.join(self.matches_dir, name)
            if start in known:
                print(f'Already saved: {os.path.basename(path)}')
            elif os.path.exists(target):
                self.failed.append((path, f'{target} exists with a different start time'))
                continue
            else:
                self.save_match(target, text)
                self.saved.append((name, opponent(text), len(re.findall(r'(?m)^\[Board ', text))))
                known.add(start)
            # The zip goes by the same name, so the report and its match file can be paired by eye
            stem = name[:-len('_match.pbn')] if name.endswith('_match.pbn') else match_name
            for saved_at, p, _ in versions:
                self.move_to_processed(p, f'BrillTM_{stem}_{saved_at}.zip')

    def file_pbns(self):
        known = self.known_starts()
        for f in sorted(os.listdir(self.root)):
            path = os.path.join(self.root, f)
            if not f.lower().endswith('.pbn') or not os.path.isfile(path):
                continue
            with open(path, 'rb') as fh:
                data = fh.read()
            if b'[Deal ' not in data:
                self.skipped.append((f, 'no [Deal] tags'))
                continue
            if data.startswith(b'\xef\xbb\xbf'):
                data = data[3:]
            name, text = self.named(f, data.decode('utf-8', errors='replace'))
            target = os.path.join(self.matches_dir, name)
            start = START_STAMP.search(f)
            if start and start.group(0) in known:
                # A TMClient match saved before, possibly re-saved since with corrections
                print(f'Already saved: {f}')
            elif os.path.exists(target):
                with open(target, 'r', encoding='utf-8-sig', errors='replace', newline='') as fh:
                    same = fh.read() == text
                if not same:
                    self.failed.append((path, f'{target} exists with different content'))
                    continue
                print(f'Already saved: {f}')
            else:
                self.save_match(target, text)
                self.saved.append((name, opponent(text), len(re.findall(r'(?m)^\[Board ', text))))
            self.move_to_processed(path)

    def rename_existing(self):
        """Bring everything already filed under the robot it was played against.

        Each match file in <name>.matches gets its canonical name and [Event] tags; its extract and
        its report zip in Processed (paired by the start time) follow it.
        """
        zips = {}
        for z in os.listdir(self.processed_dir):
            m = REPORT_ZIP.match(z)
            start = START_STAMP.search(z)
            if m and start:
                zips.setdefault(start.group(0), []).append((z, m.group('saved')))

        renamed = 0
        for f in sorted(os.listdir(self.matches_dir)):
            if not f.lower().endswith('.pbn'):
                continue
            path = os.path.join(self.matches_dir, f)
            with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as fh:
                text = fh.read()
            name, new_text = self.named(f, text)
            if name == f and new_text == text:
                continue
            target = os.path.join(self.matches_dir, name)
            # Windows names are case-insensitive: Wbridge5 -> WBridge5 is the same file, not a clash
            if os.path.exists(target) and os.path.normcase(target) != os.path.normcase(path):
                self.failed.append((f, f'not renamed, {name} already exists'))
                continue

            def rewrite(path=path, target=target, new_text=new_text):
                with open(path, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(new_text)
                if target != path:
                    os.rename(path, target)
            self.act(f'{f}\n    -> {name}' if name != f else f'{f}: [Event] corrected', rewrite)
            renamed += 1

            if name == f:
                continue
            extract = os.path.join(self.boards_dir, 'Extract_' + f)
            if os.path.exists(extract):
                self.act(f'    Extract_ follows', os.rename, extract, os.path.join(self.boards_dir, 'Extract_' + name))
            start = START_STAMP.search(f)
            if start and name.endswith('_match.pbn'):
                for z, saved_at in zips.get(start.group(0), []):
                    new_zip = f'BrillTM_{name[:-len("_match.pbn")]}_{saved_at}.zip'
                    if new_zip != z:
                        self.act(f'    zip -> {new_zip}', os.rename, os.path.join(self.processed_dir, z),
                                 os.path.join(self.processed_dir, new_zip))
        print(f'{renamed} match files renamed or corrected')
        return renamed

    # --- boards ----------------------------------------------------------

    def extract_missing(self):
        """An Extract_ file for every match file that has none -- new ones and any left over."""
        have = {f.lower() for f in os.listdir(self.boards_dir)}
        names = [f for f in os.listdir(self.matches_dir) if f.lower().endswith('.pbn') and not is_audit(f)]
        if self.dry_run:
            names += [s[0] for s in self.saved if s[0] not in names]
        for f in sorted(names):
            out_name = 'Extract_' + f
            if out_name.lower() in have:
                continue
            if self.dry_run:
                print(f'(dry run) Extract {f}')
                self.extracted.append(out_name)
                continue
            try:
                text = PbnExtractBoards.extract_boards(load_boards(read_text(os.path.join(self.matches_dir, f))))
            except Exception as e:  # endplay raises a variety of errors on a malformed board
                self.failed.append((f, f'extract failed: {e}'))
                continue
            with open(os.path.join(self.boards_dir, out_name), 'w') as out:
                out.write(text)
            print(f'Extract {f}')
            self.extracted.append(out_name)

    def merge_and_renumber(self):
        """All.PBN / Ordered_All.PBN over every robot, and the same pair per robot in a folder named after it."""
        extracts = [f for f in os.listdir(self.boards_dir) if f.lower().startswith('extract_') and f.lower().endswith('.pbn')]
        extracts.sort(key=lambda f: played_key(os.path.join(self.boards_dir, f)))
        self.merge_into(extracts, self.boards_dir, 'All robots')

        by_robot = {}
        for f in extracts:
            m = EXTRACT_ROBOT.match(f)
            by_robot.setdefault(m.group(1) if m else 'Unknown', []).append(f)
        for robot, files in sorted(by_robot.items()):
            out_dir = os.path.join(self.boards_dir, robot)
            if not self.dry_run:
                os.makedirs(out_dir, exist_ok=True)
            self.merge_into(files, out_dir, robot)

    def merge_into(self, extracts, out_dir, title):
        """Merge extracts (from the boards folder) into out_dir\\All.PBN and renumber that into Ordered_All.PBN."""
        all_pbn = os.path.join(out_dir, 'All.PBN')
        ordered = os.path.join(out_dir, 'Ordered_All.PBN')
        if self.dry_run:
            print(f'(dry run) {title}: merge {len(extracts)} extracts -> {ordered}')
            return

        # Keep the previous files one generation back (not .pbn, so never merged)
        for path in (all_pbn, ordered):
            if os.path.exists(path):
                shutil.copy2(path, path + '.bak')

        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            finder = MergePBNFiles.DuplicateFinder()
            with open(all_pbn, 'w') as merged:
                MergePBNFiles.process_file(extracts, merged, self.boards_dir, os.path.normcase(os.path.abspath(all_pbn)),
                                           finder, self.boards_dir)
            MergePBNFiles.report_duplicates(finder)
            boards = load_boards(read_text(all_pbn))
            new_boards, incomplete = ResetAndRenumberPBNBoards.renumber_boards(boards)
            with open(ordered, 'w') as out:
                pbn.dump(new_boards, out)
        log_path = os.path.join(out_dir, 'merge.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log.getvalue())

        lines = log.getvalue().splitlines()
        dup = sum(1 for l in lines if l.startswith('Duplicate deal'))
        rot = sum(1 for l in lines if l.startswith('Rotated duplicate deal'))
        print(f'{title:<12} {len(extracts):>3} matches  {len(boards):>6} boards -> Ordered_All.PBN {len(new_boards):>6} '
              f'({dup} duplicate, {rot} rotated, {incomplete} incomplete left out)  {ordered}')

    def run(self, rename=False, merge=False):
        if not os.path.isdir(self.root):
            sys.exit(f'Folder not found: {self.root}')
        # A robot's first reports: lay out the folders the way the others are
        for d in (self.matches_dir, self.boards_dir, self.processed_dir):
            if not os.path.isdir(d):
                if self.dry_run:
                    sys.exit(f'(dry run) {d} does not exist yet; run without --dry-run to create it')
                print(f'Create {d}')
                os.makedirs(d)
        renamed = self.rename_existing() if rename else 0
        self.file_zips()
        self.file_pbns()
        self.extract_missing()
        if self.extracted or self.saved or renamed or merge:
            self.merge_and_renumber()
        else:
            print('Nothing new: All.PBN and Ordered_All.PBN left as they are')
        self.summary()
        return 1 if self.failed else 0

    def summary(self):
        print()
        print(f'Saved {len(self.saved)} matches, extracted {len(self.extracted)}, moved {self.moved} reports to Processed')
        for f, opp, n in self.saved:
            print(f'  {opp:<12} {n:>4} boards  {f}')
        by_opp = Counter(opp for _, opp, _ in self.saved)
        if by_opp:
            print('  by opponent: ' + ', '.join(f'{o} {c}' for o, c in by_opp.most_common()))
        if self.skipped:
            print(f'Left alone ({len(self.skipped)}):')
            for f, why in self.skipped:
                print(f'  {f}: {why}')
        if self.failed:
            print(f'PROBLEMS ({len(self.failed)}):')
            for f, why in self.failed:
                print(f'  {f}: {why}')


def ask_arguments():
    """The report folder and whether to rename what is filed already, from dialogs."""
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import lastdir

    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(initialdir=lastdir.get_last_dir(key="reports"),
                                     title="Select the report folder (e.g. D:\\RobotMatches\\Eamon)")
    if not folder:
        sys.exit(1)
    lastdir.set_last_dir(folder, key="reports")
    rename = messagebox.askyesno("Process Robot Reports",
                                 "Also rename the matches already filed after the robot they were played against?")
    return root, folder, rename


def main():
    print("Process Robot Reports, Version 1.0.22")
    parser = argparse.ArgumentParser(description="Save, extract and merge the match reports in a robot's report folder. "
                                                 "Without a folder, dialogs ask for it.")
    parser.add_argument("folder", nargs="?", help=r"The report folder, e.g. D:\RobotMatches\Eamon")
    parser.add_argument("--name", help="Name used for Boards\\<name>.matches and Boards\\All-<name>.PBN (default: the folder's name)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Only list what would be done")
    parser.add_argument("--rename", action="store_true",
                        help="Also rename the matches already filed (and their extracts and zips) after the robot they were played against")
    parser.add_argument("--merge", action="store_true",
                        help="Rebuild All.PBN and Ordered_All.PBN even when nothing new was filed (after deleting matches by hand)")
    args = parser.parse_args()

    if args.folder:
        root = os.path.abspath(args.folder)
        sys.exit(Filer(root, args.name or os.path.basename(root), args.dry_run).run(args.rename, args.merge))

    from tkinter import messagebox
    window, folder, rename = ask_arguments()
    root = os.path.abspath(folder)
    filer = Filer(root, args.name or os.path.basename(root), args.dry_run)
    code = filer.run(rename or args.rename, args.merge)
    summary = (f"Saved {len(filer.saved)} matches, extracted {len(filer.extracted)}, "
               f"moved {filer.moved} reports to Processed.")
    if filer.failed:
        summary += f"\n\n{len(filer.failed)} problem(s) -- see the console."
    messagebox.showinfo("Process Robot Reports", summary)
    window.destroy()
    sys.exit(code)


if __name__ == "__main__":
    main()
