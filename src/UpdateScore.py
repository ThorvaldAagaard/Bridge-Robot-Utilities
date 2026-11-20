"""Score the auctions in a PBN from DatumScores.pkl.

For every board with an [Auction] it works out the final contract and declarer, looks the deal up in
the pickle, and writes:

  [Declarer] [Contract]   from the auction (the last bid, any double after it, and the first player
                          of the declaring side to name the strain)
  [Result]                declarer's DOUBLE-DUMMY tricks, from the pickle's 20-cell table
  [Score]                 that result scored for the contract and the declarer's vulnerability, North-South's view
  [OptimumScore] [ParContract] [OptimumResultTable]   as AddDatumScoreToPBN writes them

This is what Split_PBN needs to judge a board, for auctions from an engine that writes only the
calls (e.g. Pidgin's scripts/bid_pbn.py). [Result] is double dummy: nothing was played.

Like AddDatumScoreToPBN it edits the file as text, so every other tag, note and comment is kept
byte-for-byte, it streams one board at a time, and re-running replaces the tags it manages. A board
without an [Auction] is copied unchanged. A board whose deal is not in the pickle, or whose entry
has no double-dummy table, gets its contract and declarer but an empty [Result] and [Score]
(Split_PBN files it under -missing-DD).

    UpdateScore.py <input.pbn> [DatumScores.pkl] [output.pbn]

Output defaults to <input>-scored.pbn.
"""
import os
import re
import sys

import AddDatumScoreToPBN as datum
from scoring import score

SEATS = 'NESW'
STRAINS = 'CDHSN'                                   # bid order; N = notrump
DD_STRAIN = {'S': 0, 'H': 1, 'D': 2, 'C': 3, 'N': 4}  # the pickle's table order, per declarer
VULNERABLE = {'none': (False, False), 'love': (False, False), '-': (False, False),
              'ns': (True, False), 'ew': (False, True), 'all': (True, True), 'both': (True, True)}
MANAGED = ('[Declarer ', '[Contract ', '[Result ', '[Score ')
TAG = re.compile(r'^\s*\[(\w+)\s+"([^"]*)"\]')


def parse_call(token):
    """A PBN call token -> 'P', 'X', 'XX', '1C'..'7N', or None for notes, NAGs and annotations."""
    t = token.strip().upper()
    if not t or t[0] in '=${(' or t in ('*', '-', '+'):
        return None
    t = t.rstrip('!?')
    if t in ('PASS', 'P'):
        return 'P'
    if t in ('X', 'DBL'):
        return 'X'
    if t in ('XX', 'RDBL'):
        return 'XX'
    if t == 'AP':
        return 'AP'
    if len(t) >= 2 and t[0] in '1234567':
        strain = 'N' if t[1:] in ('N', 'NT') else t[1:]
        if strain in STRAINS:
            return t[0] + strain
    return None


def final_contract(dealer, calls):
    """(contract like '4SX' or 'Pass', declarer seat index or None)."""
    last = max((i for i, c in enumerate(calls) if c[0].isdigit()), default=None)
    if last is None:
        return 'Pass', None
    bid = calls[last]
    doubled = ''
    for c in calls[last + 1:]:
        if c in ('X', 'XX'):
            doubled = c
    side = (dealer + last) % 2
    for i, c in enumerate(calls):
        if c[0].isdigit() and c[1] == bid[1] and (dealer + i) % 2 == side:
            return bid + doubled, (dealer + i) % 4


def score_board(block, data):
    """The tag lines this tool writes for one board, or None when the board has no auction."""
    tags = {}
    calls, in_auction, dealer_of_auction = None, False, None
    for line in block:
        m = TAG.match(line)
        if m:
            tags.setdefault(m.group(1), m.group(2))
            in_auction = m.group(1) == 'Auction'
            if in_auction:
                calls, dealer_of_auction = [], m.group(2).strip().upper()
            continue
        if in_auction and not line.lstrip().startswith(('{', ';', '%')):
            for token in line.split():
                c = parse_call(token)
                if c == 'AP':
                    calls += ['P'] * 3
                elif c:
                    calls.append(c)
    if calls is None or 'Deal' not in tags:
        return None
    dealer = SEATS.index((dealer_of_auction or tags.get('Dealer', 'N'))[0])
    contract, declarer = final_contract(dealer, calls)

    # Par is scored at this board's own vulnerability and dealer (the pickle holds only tricks).
    opt, par, dd_bytes = datum.lookup(data, f'[Deal "{tags["Deal"]}"]', tags.get('Vulnerable', 'None'),
                                      tags.get('Dealer') or dealer_of_auction or 'N')
    result = points = None
    if declarer is not None and dd_bytes:
        result = dd_bytes[declarer * 5 + DD_STRAIN[contract[1]]]
        vul_ns, vul_ew = VULNERABLE.get(tags.get('Vulnerable', 'None').strip().lower(), (False, False))
        points = score(contract, vul_ns if declarer % 2 == 0 else vul_ew, result)
        if declarer % 2 == 1:
            points = -points
    elif declarer is None and opt is not None:
        points = 0                                   # passed out

    pbn_contract = 'Pass' if declarer is None else contract[0] + ('NT' if contract[1] == 'N' else contract[1]) + contract[2:]
    return {
        'lines': [f'[Declarer "{"" if declarer is None else SEATS[declarer]}"]',
                  f'[Contract "{pbn_contract}"]',
                  f'[Result "{"" if result is None else result}"]',
                  f'[Score "{"" if points is None else f"NS {points}"}"]'],
        'datum': (opt, par, dd_bytes),
        'scored': points is not None,
    }


def update(pbn_path, pickle_path, output_path):
    print("Loading datum scores ...", flush=True)
    data = datum.load_optimumscores(pickle_path)
    print("Scoring boards ...", flush=True)
    counts = {'scored': 0, 'no result': 0, 'no auction': 0}

    def flush_block(block, out):
        if not block:
            return
        scored = score_board(block, data)
        if scored is None:
            counts['no auction'] += 1 if any(l.lstrip().startswith('[Deal ') for l in block) else 0
            out.writelines(block)
            return
        counts['scored' if scored['scored'] else 'no result'] += 1
        deal_line = next(l for l in block if l.lstrip().startswith('[Deal '))
        term = deal_line[len(deal_line.rstrip('\r\n')):] or '\n'
        # Drop what this tool manages (an existing result belonged to an earlier auction), then
        # put the contract tags in front of the auction and the datum tags after the deal.
        block = [l for l in datum.strip_existing(block) if not l.lstrip().startswith(MANAGED)]
        ai = next(i for i, l in enumerate(block) if l.lstrip().startswith('[Auction'))
        block[ai:ai] = [l + term for l in scored['lines']]
        opt, par, dd_bytes = scored['datum']
        if opt is not None:
            di = next(i for i, l in enumerate(block) if l.lstrip().startswith('[Deal '))
            inserts = [f'[OptimumScore "{opt}"]{term}']
            if par is not None:
                inserts.append(f'[ParContract "{par}"]{term}')
            if dd_bytes:
                inserts.extend(datum.build_ort(dd_bytes, term))
            block[di + 1:di + 1] = inserts
        out.writelines(block)

    n = 0
    with open(pbn_path, 'r', encoding='utf-8-sig', newline='') as fin, \
            open(output_path, 'w', encoding='utf-8', newline='') as fout:
        block = []
        for line in fin:
            if line.strip() == '':
                flush_block(block, fout)
                block = []
                fout.write(line)
                n += 1
                if n % 100000 == 0:
                    print(f"  {counts['scored']:,} boards scored", flush=True)
            else:
                block.append(line)
        flush_block(block, fout)

    print(f"{counts['scored']:,} boards scored, {counts['no result']:,} without a double-dummy result, "
          f"{counts['no auction']:,} without an auction (copied unchanged).")
    print(f"{output_path} generated")
    return 0


def main():
    print("Update Score, Version 1.0.24")
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 1
    pbn_path = sys.argv[1]
    pickle_path = sys.argv[2] if len(sys.argv) > 2 else 'DatumScores.pkl'
    output_path = sys.argv[3] if len(sys.argv) > 3 else f"{os.path.splitext(pbn_path)[0]}-scored.pbn"
    return update(pbn_path, pickle_path, output_path)


if __name__ == "__main__":
    sys.exit(main())
