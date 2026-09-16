"""Scan a PBN for boards missing (or malformed) par / optimum-score annotation.

Reads the file the same way AddDatumScoreToPBN.py writes it -- one blank-line
separated board block at a time -- and reports every board that is not fully
annotated:

  - no [OptimumScore] / [ParContract] / [OptimumResultTable]
  - an OptimumResultTable that is not the expected 20 rows
    (4 declarers x 5 denominations) or has a trick count outside 0..13
  - a passed-out par written as a level-0 contract ("NS 0N=") instead of "Pass"

Give it the datum-score pickle as well and each unannotated board is classified:
already in the pickle (re-run AddDatumScoreToPBN.py) or absent from it (run
ComputeDatumScores.py first).

It also counts boards and reports duplicate board numbers and duplicate deals,
which is usually what is behind a board count that comes up short, and lists
rotated deals: the same four hands moved one, two or three seats around. Those
where dealer and vulnerability turned along are the same board; the rest are
listed separately.

Streams the input, so a 500 MB file costs no more memory than a small one
(bar the optional duplicate sets). Source-only developer tool; not shipped.

Usage: CheckDatumScores.py <input.pbn> [DatumScores.pkl] [--limit N] [--all]
                           [--no-dupes]
"""
import sys
import os
import re
import pickle
import argparse
import dealkey

# A data row of an OptimumResultTable, e.g. "N S 5".
ORT_ROW = re.compile(r'^([NESW])\s+(NT|S|H|D|C)\s+(-?\d+)$')

# The 20 (declarer, denomination) cells a complete table must contain.
EXPECTED_CELLS = {(p, d) for p in ('N', 'E', 'S', 'W')
                  for d in ('S', 'H', 'D', 'C', 'NT')}

# "NS 4H=", "EW 7Nx-5", "Pass". Level 0 means the par is a pass-out.
PAR_LEVEL = re.compile(r'^(?:NS|EW)\s+(\d)')


def tag_value(line):
    parts = line.split('"')
    return parts[1] if len(parts) > 1 else None


def tag_in(block, name):
    """Value of the [name "..."] tag in a board block, or None."""
    prefix = '[%s ' % name
    for line in block:
        if line.lstrip().startswith(prefix):
            return tag_value(line.strip())
    return None


def check_block(block):
    """Return (board, deal_line, [problems]) for one board block."""
    board = deal_line = opt = par = None
    ort_seen = False
    cells = []
    problems = []

    i = 0
    while i < len(block):
        s = block[i].strip()
        if s.startswith('[Board '):
            board = tag_value(s)
        elif s.startswith('[Deal '):
            deal_line = s
        elif s.startswith('[OptimumScore'):
            opt = tag_value(s)
        elif s.startswith('[ParContract'):
            par = tag_value(s)
        elif s.startswith('[OptimumResultTable'):
            ort_seen = True
            i += 1
            while i < len(block):
                m = ORT_ROW.match(block[i].strip())
                if not m:
                    break
                cells.append((m.group(1), m.group(2), int(m.group(3))))
                i += 1
            continue
        i += 1

    if deal_line is None:
        return board, None, problems

    if opt is None:
        problems.append('no OptimumScore')
    if par is None:
        problems.append('no ParContract')
    else:
        m = PAR_LEVEL.match(par)
        if m and m.group(1) == '0':
            problems.append('level-0 par contract "%s" (should be Pass)' % par)

    if not ort_seen:
        problems.append('no OptimumResultTable')
    else:
        got = {(p, d) for p, d, _ in cells}
        if len(cells) != 20 or got != EXPECTED_CELLS:
            missing = sorted('%s %s' % (p, d) for p, d in EXPECTED_CELLS - got)
            problems.append('OptimumResultTable has %d rows%s' % (
                len(cells), ', missing ' + ', '.join(missing) if missing else ''))
        bad = ['%s %s %d' % c for c in cells if not 0 <= c[2] <= 13]
        if bad:
            problems.append('trick count out of range: ' + ', '.join(bad))

    return board, deal_line, problems


def scan(pbn_path, pickle_path=None, limit=20, show_all=False, dupes=True):
    data = None
    if pickle_path:
        print("Loading %s ..." % os.path.basename(pickle_path), flush=True)
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
        print("  %d entries" % len(data), flush=True)

    total = max(os.path.getsize(pbn_path), 1)
    counts = {'boards': 0, 'no_deal': 0, 'bad': 0, 'shown': 0,
              'in_pickle': 0, 'not_in_pickle': 0}
    seen_nums, dup_nums = set(), []
    # rotation key -> (first board, its hands N/E/S/W, dealer, vulnerability)
    seen_deals, dup_deals, rotated = {}, [], []
    progress = {'done': 0, 'next': 0}

    def report(block):
        if not block:
            return
        board, deal_line, problems = check_block(block)
        if deal_line is None:
            if any(l.lstrip().startswith('[') for l in block):
                counts['no_deal'] += 1
            return
        counts['boards'] += 1

        if dupes:
            if board is not None:
                if board in seen_nums:
                    dup_nums.append(board)
                else:
                    seen_nums.add(board)
            try:
                hands = dealkey.hands_from_north(deal_line)
                key = dealkey.rotation_key(hands)
            except (ValueError, IndexError):
                hands = key = deal_line  # malformed deal: exact match only
            dealer, vul = tag_in(block, 'Dealer'), tag_in(block, 'Vulnerable')
            first = seen_deals.get(key)
            if first is None:
                seen_deals[key] = (board, hands, dealer, vul)
            elif first[1] == hands:
                dup_deals.append(board)
            else:
                rotated.append((board, first[0], dealkey.same_board(
                    first[1], first[2], first[3], hands, dealer, vul)))

        if not problems:
            return
        counts['bad'] += 1
        note = ''
        if data is not None and ('no OptimumScore' in problems
                                 or 'no ParContract' in problems):
            if deal_line in data:
                counts['in_pickle'] += 1
                note = '  [in pickle - re-run AddDatumScoreToPBN]'
            else:
                counts['not_in_pickle'] += 1
                note = '  [NOT in pickle - run ComputeDatumScores]'
        if show_all or counts['shown'] < limit:
            counts['shown'] += 1
            print("  Board %s: %s%s" % (board, '; '.join(problems), note))
            print("    %s" % deal_line)
        elif counts['shown'] == limit:
            counts['shown'] += 1
            print("  ... (further boards suppressed; use --all to list them)")

    print("Scanning %s ..." % os.path.basename(pbn_path), flush=True)
    with open(pbn_path, 'r', encoding='utf-8', errors='replace') as f:
        block = []
        for line in f:
            progress['done'] += len(line)
            if line.strip() == '':
                report(block)
                block = []
            else:
                block.append(line)
            if progress['done'] >= progress['next']:
                progress['next'] = progress['done'] + 32 * 1024 * 1024
                print("\r  %d%%  (%d boards)" % (
                    min(100, int(progress['done'] * 100 / total)),
                    counts['boards']), end='', file=sys.stderr, flush=True)
        report(block)
    print("\r%s\r" % (' ' * 40), end='', file=sys.stderr, flush=True)

    print()
    print("%d boards with a deal" % counts['boards'])
    if counts['no_deal']:
        print("%d blocks without a [Deal] tag (skipped)" % counts['no_deal'])
    if dupes:
        print("%d duplicate board numbers%s" % (
            len(dup_nums),
            ' (e.g. %s)' % ', '.join(dup_nums[:5]) if dup_nums else ''))
        print("%d duplicate deals%s" % (
            len(dup_deals),
            ' (e.g. board %s)' % ', '.join(str(b) for b in dup_deals[:5])
            if dup_deals else ''))
        same = [(b, o) for b, o, s in rotated if s]
        other = [(b, o) for b, o, s in rotated if not s]
        for title, found in (
                ("rotated boards (hands, dealer and vulnerability all turned)", same),
                ("rotated deals with a different dealer or vulnerability", other)):
            print("%d %s" % (len(found), title))
            for i, (board, original) in enumerate(found):
                if not show_all and i == limit:
                    print("  ... (further suppressed; use --all to list them)")
                    break
                print("  Board %s is board %s rotated" % (board, original))
    print("%d boards with a problem" % counts['bad'])
    if data is not None and (counts['in_pickle'] or counts['not_in_pickle']):
        print("  %d unannotated but present in the pickle" % counts['in_pickle'])
        print("  %d unannotated and missing from the pickle"
              % counts['not_in_pickle'])
    return 1 if counts['bad'] else 0


def main():
    print("Check Datum Scores, Version 1.0.21")
    parser = argparse.ArgumentParser(
        description="Scan a PBN for boards missing par / optimum scores")
    parser.add_argument("filename", help="PBN file to scan")
    parser.add_argument("pickle", nargs="?",
                        help="DatumScores.pkl, to classify unannotated boards")
    parser.add_argument("--limit", type=int, default=20,
                        help="how many offending boards to list (default 20)")
    parser.add_argument("--all", action="store_true",
                        help="list every offending board")
    parser.add_argument("--no-dupes", action="store_true",
                        help="skip duplicate board/deal detection (less memory)")
    args = parser.parse_args()

    sys.exit(scan(args.filename, args.pickle, args.limit, args.all,
                  not args.no_dupes))


if __name__ == "__main__":
    main()
