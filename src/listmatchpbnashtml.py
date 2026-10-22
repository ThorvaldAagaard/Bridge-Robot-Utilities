import os
import json
import sys
import scoring
import compare
import lastdir
import tkinter as tk
from tkinter import filedialog, messagebox
import endplay.parsers.pbn as pbn
import endplayfix  # endplay drops [Dealer] on boards without a contract
import endplay.parsers.lin as lin
import webbrowser
import re
import urllib.parse
from html import escape

# Read the file line by line and process each JSON object

def encode_annotations(lin):
    def encode_match(m):
        text = m.group(1)
        return f"|an|{urllib.parse.quote(text)}|"
    return re.sub(r"\|an\|(.*?)\|", encode_match, lin)

def generate_html_card(suit, cards):
    html = f"<div class='suit'><span>{suit}</span>"
    for card in cards:
        html += f"{card}"
    html += "</div>"
    return html

def generate_frequency_table(results):
    """Every table result on a board, grouped by contract/declarer/tricks, with the NS score,
    how often it occurred and its cross-IMPs (NS view, averaged over every other result)."""
    groups = {}
    for r in results:
        groups[r] = groups.get(r, 0) + 1
    n = len(results)
    rows = []
    for (declarer, contract, tricks, score), count in groups.items():
        # The result against all other tables: the other copies of itself score 0
        total = sum(compare.get_imps(score, other[3]) * c for other, c in groups.items())
        xi = total / (n - 1) if n > 1 else 0.0
        rows.append((score, declarer, contract, tricks, count, xi))
    rows.sort(key=lambda r: (-r[0], r[2] or "", r[1] or ""))
    html = "<table class='freq-table'>\n<tr><th>Contract</th><th>Tricks</th><th>NS</th><th>#</th><th>X-IMPs</th></tr>\n"
    for score, declarer, contract, tricks, count, xi in rows:
        shown = "Pass" if not declarer or not contract or contract.startswith("PASS") else f"{contract} {declarer}"
        html += (f"<tr><td>{shown}</td><td class='align-right'>{tricks if declarer else ''}</td>"
                 f"<td class='align-right'>{score}</td><td class='align-right'>{count}</td>"
                 f"<td class='align-right'>{xi:+.2f}</td></tr>\n")
    html += "</table>\n"
    return html


def generate_html_deal(dealer, vulnerable, cards, board_number, extra_html=""):
    cards = cards.split(':')[1].split()
    html = f"""
        <div class='board-section'>
            <div class='diagram-container'>
                <div id='deal'>
                    <div id='dealer-vuln'>
                        <div id='vul-north' class='{"red" if vulnerable in ('N-S', 'Both') else 'white'}'>
                            {"<span class='dealer'>N</span>" if dealer == 'N' else ''}
                        </div>
                        <div id='vul-east' class='{"red" if vulnerable in ('E-W', 'Both') else 'white'}'>
                            {"<span class='dealer'>E</span>" if dealer == 'E' else ''}
                        </div>
                        <div id='vul-south' class='{"red" if vulnerable in ('N-S', 'Both') else 'white'}'>
                            {"<span class='dealer'>S</span>" if dealer == 'S' else ''}
                        </div>
                        <div id='vul-west' class='{"red" if vulnerable in ('E-W', 'Both') else 'white'}'>
                            {"<span class='dealer'>W</span>" if dealer == 'W' else ''}
                        </div>
                        <div id='boardno'>
                            {board_number}
                        </div>
                    </div>
                    <div id='north'>
                        {generate_html_card('&spades;', cards[0].split('.')[0])}
                        {generate_html_card('<span class="font-red">&hearts;</span>', cards[0].split('.')[1])}
                        {generate_html_card('<span class="font-red">&diams;</span>', cards[0].split('.')[2])}
                        {generate_html_card('&clubs;', cards[0].split('.')[3])}
                    </div>
                    <div id='west'>
                        {generate_html_card('&spades;', cards[3].split('.')[0])}
                        {generate_html_card('<span class="font-red">&hearts;</span>', cards[3].split('.')[1])}
                        {generate_html_card('<span class="font-red">&diams;</span>', cards[3].split('.')[2])}
                        {generate_html_card('&clubs;', cards[3].split('.')[3])}
                    </div>
                    <div id='east'>
                        {generate_html_card('&spades;', cards[1].split('.')[0])}
                        {generate_html_card('<span class="font-red">&hearts;</span>', cards[1].split('.')[1])}
                        {generate_html_card('<span class="font-red">&diams;</span>', cards[1].split('.')[2])}
                        {generate_html_card('&clubs;', cards[1].split('.')[3])}
                    </div>
                    <div id='south'>
                        {generate_html_card('&spades;', cards[2].split('.')[0])}
                        {generate_html_card('<span class="font-red">&hearts;</span>', cards[2].split('.')[1])}
                        {generate_html_card('<span class="font-red">&diams;</span>', cards[2].split('.')[2])}
                        {generate_html_card('&clubs;', cards[2].split('.')[3])}
                    </div>
                </div>
                {extra_html}
         </div>"""
    return html


def team_totals(matches):
    """Aggregate the per-match IMPs into a per-team (robot) standings list.

    Each match is 'NS vs EW'; the net belongs to NS and the opposite to EW, so a
    team's totals are summed across every match it played, sorted best first.
    """
    teams = {}
    for m in matches:
        ns_name, ew_name = m.get('ns'), m.get('ew')
        if not (ns_name and ew_name):
            continue
        ns = teams.setdefault(ns_name, {'label': ns_name, 'played': 0, 'plus': 0, 'minus': 0})
        ew = teams.setdefault(ew_name, {'label': ew_name, 'played': 0, 'plus': 0, 'minus': 0})
        ns['played'] += 1; ns['plus'] += m['plus']; ns['minus'] += m['minus']
        ew['played'] += 1; ew['plus'] += m['minus']; ew['minus'] += m['plus']
    result = list(teams.values())
    for t in result:
        t['net'] = t['plus'] - t['minus']
    result.sort(key=lambda t: t['net'], reverse=True)
    return result


TAU = (5 ** 0.5 - 1) / 2


def imp_to_vp(imp_diff, boards):
    """WBF continuous VP scale (WBF_VPScales.pdf), 20-point: VP = 10 + 10*(1 - tau^(3M/B))/(1 - tau^3)
    with blitz B = 15*sqrt(boards), rounded to two decimals; the loser gets 20 - VP. Scaled by the
    boards actually played, so a match that lost boards is not scored as if it had all of them."""
    m = abs(imp_diff)
    b = 15 * (max(boards, 1) ** 0.5)
    if m >= b:
        win = 20.0
    elif m == 0:
        win = 10.0
    else:
        win = 10 + 10 * (1 - TAU ** (3 * m / b)) / (1 - TAU ** 3)
    win = round(win, 2)
    return win if imp_diff >= 0 else round(20 - win, 2)


def team_results(matches):
    """Per team: every match it played, from its own side, plus its VP and IMP totals.
    Sorted by VP, then net IMPs, best first."""
    teams = {}
    for m in matches:
        ns_name, ew_name = m.get('ns'), m.get('ew')
        if not (ns_name and ew_name):
            continue
        for me, opp, imps_for, imps_against in ((ns_name, ew_name, m['plus'], m['minus']),
                                                (ew_name, ns_name, m['minus'], m['plus'])):
            t = teams.setdefault(me, {'label': me, 'rows': [], 'vp': 0.0, 'plus': 0, 'minus': 0})
            vp = imp_to_vp(imps_for - imps_against, m['boards'])
            t['rows'].append({'opp': opp, 'for': imps_for, 'against': imps_against, 'vp': vp, 'boards': m['boards']})
            t['vp'] += vp; t['plus'] += imps_for; t['minus'] += imps_against
    result = list(teams.values())
    for t in result:
        t['vp'] = round(t['vp'], 2)
        t['net'] = t['plus'] - t['minus']
        t['played'] = len(t['rows'])
    result.sort(key=lambda t: (t['vp'], t['net']), reverse=True)
    rank = {t['label']: i for i, t in enumerate(result)}
    for t in result:
        t['rows'].sort(key=lambda r: rank.get(r['opp'], 999))
    return result


def generate_match_summary(matches):
    """VP standings, then a cross table of every pairing, rows and columns in ranking order."""
    teams = team_results(matches)
    full = max((m['boards'] for m in matches), default=0)
    html = "<div class='match-summary'>\n"
    html += "<h2>Standings</h2>\n"
    html += (f"<p class='align-center'>WBF 20-point VP scale, {full} boards a match "
             "(a match short of boards is scaled to the boards it played)</p>\n")
    html += "<table class='border-collapse table-container'>\n<tr>\n"
    html += "<th class='align-right'>#</th><th class='col-name'>Team</th>"
    html += "<th class='align-right'>VP</th><th class='align-right'>Net IMPs</th>"
    html += "<th class='align-right'>Matches</th><th class='align-right'>VP/match</th>\n</tr>\n"
    for i, t in enumerate(teams, 1):
        html += (f"<tr class='row-height'><td class='align-right'>{i}</td><td>{t['label']}</td>"
                 f"<td class='align-right'><b>{t['vp']:.2f}</b></td><td class='align-right'>{t['net']:+d}</td>"
                 f"<td class='align-right'>{t['played']}</td><td class='align-right'>{t['vp'] / t['played']:.2f}</td></tr>\n")
    html += "</table>\n"

    html += "<h2>Cross table</h2>\n"
    html += "<p class='align-center'>Each cell is the row team's VP and IMPs against the column team</p>\n"
    html += "<table class='cross-table'>\n<tr><th>#</th><th class='col-name'>Team</th>"
    for i, t in enumerate(teams, 1):
        html += f"<th title='{t['label']}'>{i}<br>{t['label']}</th>"
    html += "<th>VP</th></tr>\n"
    for i, t in enumerate(teams, 1):
        by_opp = {}
        for r in t['rows']:
            by_opp.setdefault(r['opp'], []).append(r)
        html += f"<tr><td class='align-right'>{i}</td><td class='team-name'>{t['label']}</td>"
        for o in teams:
            if o['label'] == t['label']:
                html += "<td class='self'></td>"
                continue
            cell = ""
            for r in by_opp.get(o['label'], []):
                cls = 'win' if r['vp'] > 10 else 'loss' if r['vp'] < 10 else 'draw'
                short = f" <span class='short'>({r['boards']} bd)</span>" if r['boards'] < full else ""
                cell += (f"<div class='{cls}'><span class='vp'>{r['vp']:.2f}</span>"
                         f"<span class='imps'>{r['for']}-{r['against']}{short}</span></div>")
            html += f"<td>{cell}</td>"
        html += f"<td class='total'>{t['vp']:.2f}</td></tr>\n"
    html += "</table>\n</div>\n"
    return html


def load(fin):
    data_list = []
    dealer = ""
    dealer, vulnerable, declarer = None, None, None
    result = 0
    for line in fin:
        #print(line)
        if line.startswith("% PBN") or line == "\n":
            if dealer != None:
                v = False
                if (declarer != None):
                    if (vulnerable == "All" or vulnerable == "Both"):
                        v = True
                    if (declarer == "N" or declarer == "S") and (vulnerable == "NS" or vulnerable == "N-S"):
                        v= True
                    if (declarer == "E" or declarer == "W") and (vulnerable == "EW" or vulnerable == "E-W"):
                        v= True
                    if (contract_parts != ""):
                        X = scoring.score(contract_parts, v , int(result))
                        if declarer == "E" or declarer == "W":
                            X = -X
                else:
                    X = 0
                #print(f"Appending board {board}")
                data_list.append((int(board), ns, ew, dealer, vulnerable, declarer, contract_parts, int(result), X, hands_pbn))
                dealer, vulnerable, declarer = None, None, None
                result = 0
        if line.startswith('[North'):
            ns = extract_value(line)
        if line.startswith('[East'):
            ew = extract_value(line)
        if line.startswith('[Dealer'):
            dealer = extract_value(line)
        if line.startswith('[Declarer'):
            declarer = extract_value(line)
        if line.startswith('[Contract'):
            contract_parts = extract_value(line.upper())
            if contract_parts == "":
                print(f"contract is empty {board}")
                print(line)
        if line.startswith('[Board'):
            board = extract_value(line)
            if not board.isdigit():
                last_space_index = board.rfind(' ')
                board = board[last_space_index + 1:]
        if line.startswith('[Result'):
            result = extract_value(line)
            if result == "":
                result =  0
        elif line.startswith('[Vulnerable'):
            vuln_str = extract_value(line)
            vulnerable = {'NS': 'N-S', 'EW': 'E-W', 'All': 'Both'}.get(vuln_str, vuln_str)
        elif line.startswith('[Deal'):
            hands_pbn = extract_value(line)
        else:
            continue
    # pick up any pending deals
    if dealer != None:
        v = False
        if (vulnerable == "All" or vulnerable == "Both"):
            v = True
        if (declarer == "N" or declarer == "S") and (vulnerable == "NS" or vulnerable == "N-S"):
            v= True
        if (declarer == "E" or declarer == "W") and (vulnerable == "EW" or vulnerable == "E-W"):
            v= True
        X = scoring.score(contract_parts, v , int(result))
        if declarer == "E" or declarer == "W":
            X = -X
        #print(f"Appending board {board}")
        data_list.append((int(board), ns, ew, dealer, vulnerable, declarer, contract_parts, int(result), X, hands_pbn))
        dealer= None
    return data_list

def extract_value(s: str) -> str:
    return s[s.index('"') + 1 : s.rindex('"')]

def main():
    print("List matches as html, Version 1.0.23")

    # Batch mode for scripts (robot-roundrobin.ps1 puts the page in its zip): --out <file.html>
    # writes there with no dialog and no browser, and a board one room never finished -- a VOID
    # board, which leaves a single record -- is skipped instead of stopping the whole run.
    args = sys.argv[1:]
    out_path = None
    if '--out' in args:
        i = args.index('--out')
        if i + 1 >= len(args):
            print("Error: --out needs a file name.")
            sys.exit(2)
        out_path = args[i + 1]
        del args[i:i + 2]

    if out_path is None:
        # create a root window
        root = tk.Tk()
        root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]
    file_types_html = [
        ("html files", "*.html"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]


    # Command-line paths (one per robot match, from any mix of directories) bypass the dialog,
    # which only lets you multi-select files within a single folder per open.
    if args:
        file_paths = args
    elif out_path is not None:
        print("Error: --out needs the match PBNs on the command line.")
        sys.exit(2)
    else:
        # open the file dialog box in the folder used last time
        file_paths = filedialog.askopenfilenames(initialdir=lastdir.get_last_dir(), filetypes=file_types)
        if file_paths:
            lastdir.set_last_dir(file_paths[0])

    new_data_list = []
    matches = []
    for file_path in file_paths:
        print(file_path)
        try:
            with open(file_path, "r", encoding='utf-8-sig') as file:  # Open the input file with UTF-8 encoding, tolerating a BOM
                pbn_boards = pbn.loads(file.read().replace('﻿', ''))  # matches concatenated across TM sessions each carry their own BOM
            with open(file_path, "r", encoding='utf-8-sig') as file:  # Open the input file with UTF-8 encoding, tolerating a BOM
                lines = file.readlines()
            data_list = load(lines)

            if len(data_list) % 2 != 0 and out_path is not None:
                # Keep only the boards with both rooms, in file order (records are paired by
                # position below, so a lone record would pair with the next board's).
                counts = {}
                for d in data_list:
                    counts[d[0]] = counts.get(d[0], 0) + 1
                keep = [i for i, d in enumerate(data_list) if counts[d[0]] == 2]
                skipped = sorted(b for b, c in counts.items() if c != 2)
                print(f"  skipped board(s) not played in both rooms: {', '.join(str(b) for b in skipped)}")
                data_list = [data_list[i] for i in keep]
                pbn_boards = [pbn_boards[i] for i in keep]

            if len(data_list) % 2 != 0:
                print("Error: The number of boards must be even.")
                input("\n Press any key to exit...")
                sys.exit(1)

            #print(data_list)
            imp_plus = 0
            imp_minus = 0
            n_pairs = 0
            for i in range(0, len(data_list), 2):
                lin_board_open = encode_annotations(lin.LINEncoder().serialise_board(pbn_boards[i ]))
                lin_board_closed = encode_annotations(lin.LINEncoder().serialise_board(pbn_boards[i + 1]))
                imp = compare.get_imps(data_list[i][-2],data_list[i+1][-2])
                merged_tuple = data_list[i] + data_list[i + 1][5:-1] + (imp,) + (lin_board_open, lin_board_closed)
                new_data_list.append(merged_tuple)
                if imp > 0:
                    imp_plus += imp
                elif imp < 0:
                    imp_minus += -imp
                n_pairs += 1

        except Exception as ex:
            print('Error:', ex)
            raise ex

        if data_list:
            # Each file is a match between two robots (NS vs EW); label by both
            # seat names, fall back to the file name if either is missing.
            ns_name, ew_name = data_list[0][1], data_list[0][2]
            if ns_name and ew_name:
                label = f"{ns_name} vs {ew_name}"
            else:
                label = os.path.splitext(os.path.basename(file_path))[0]
            matches.append({
                'label': label,
                'boards': n_pairs,
                'plus': imp_plus,
                'minus': imp_minus,
                'net': imp_plus - imp_minus,
                'ns': ns_name,
                'ew': ew_name,
            })

    # Rank the matches by net IMPs, best first
    matches.sort(key=lambda m: m['net'], reverse=True)



    teams = team_results(matches)
    rank = {t['label']: i for i, t in enumerate(teams)}

    # Every table result per board (each table once), for the frequency table
    board_results = {}
    for d in new_data_list:
        board_results.setdefault(d[0], []).extend([(d[5], d[6], d[7], d[8]), (d[10], d[11], d[12], d[13])])

    # Show every match from both sides, so each team appears as NS in the open room once per
    # match it played: the mirror swaps the teams and the rooms and negates the IMPs.
    rows = []
    for d in new_data_list:
        (board, ns, ew, dealer, vul, declarer1, contract1, result1, score1, hands_pbn,
         declarer2, contract2, result2, score2, imp, lin_open, lin_closed) = d
        rows.append(d)
        rows.append((board, ew, ns, dealer, vul, declarer2, contract2, result2, score2, hands_pbn,
                     declarer1, contract1, result1, score1, -imp, lin_closed, lin_open))
    sorted_data = sorted(rows, key=lambda x: (x[0], rank.get(x[1], 999), rank.get(x[2], 999)))

    # Generate the HTML tables
    row_html = ""
    old_board = -1
    table1_html = ""
    html = generate_match_summary(matches)
    html += "<div class='team-filter'><label>Show team (NS in open room): <select id='team-filter' onchange='filterTeam(this.value)'>"
    html += "<option value=''>All teams</option>"
    for t in teams:
        name = escape(t['label'], quote=True)
        html += f"<option value='{name}'>{name}</option>"
    html += "</select></label></div>\n"
    for i, board_data in enumerate(sorted_data):

        board, ns, ew, dealer, vul, declarer1, contract1, result1, score1, hands_pbn, declarer2, contract2, result2, score2, imp, lin_open, lin_closed = board_data
        if board != old_board:
            if i > 0:
                table1_html += "</table>\n</div>\n</div>\n"
                html += table1_html
            html += generate_html_deal(dealer, vul, hands_pbn, board, generate_frequency_table(board_results[board]))
            table1_html = "\n<div class='results-container'>\n"
            table1_html += "\n<table class='border-collapse table-container'>\n"
            table1_html += "<tr>\n"
            table1_html += "<th class='col-name'>NS</th>\n"
            table1_html += "<th class='col-name'>EW</th>\n"
            table1_html += "<th class='col-contract'>Contract</th>\n"
            table1_html += "<th class='col-tricks'>Tricks</th>\n"
            table1_html += "<th class='col-result'>Result</th>\n"
            table1_html += "<th class='col-name'>NS</th>\n"
            table1_html += "<th class='col-name'>EW</th>\n"
            table1_html += "<th class='col-contract'>Contract</th>\n"
            table1_html += "<th class='col-tricks'>Tricks</th>\n"
            table1_html += "<th class='col-result'>Result</th>\n"
            table1_html += "<th class='align-right col-imps'>Imps (+)</th>\n"
            table1_html += "<th class='align-right col-imps'>Imps (-)</th>\n"
            table1_html += "</tr>\n"
            old_board = board
        # Align right for Result and Tricks columns
        res1 = f"<td class='align-right'>{score1}</td>" if score1 is not None else "<td class='align-right'></td>"
        tricks1 = f"<td class='align-right'>{result1}</td>" if result1 is not None else "<td class='align-right'></td>"
        res2 = f"<td class='align-right'>{score2}</td>" if score2 is not None else "<td class='align-right'></td>"
        tricks2 = f"<td class='align-right'>{result2}</td>" if result2 is not None else "<td class='align-right'></td>"

        # Split Imps column into positive and negative columns
        imp_positive = f"<td class='align-right'>{imp if imp > 0 else '--'}</td>"
        imp_negative = f"<td class='align-right'>{abs(imp) if imp < 0 else '--'}</td>"

        link_open = "https://www.bridgebase.com/tools/handviewer.html?lin=" + lin_open
        link_closed = "https://www.bridgebase.com/tools/handviewer.html?lin=" + lin_closed
        contract_open = f"<a href='{link_open}' target='_blank'>{declarer1} {contract1}</a>"
        contract_closed = f"<a href='{link_closed}' target='_blank'>{declarer2} {contract2}</a>"
        # Add class to the row based on imp value
        row_height_class = "row-height"
        row_html += f"<tr class='{row_height_class}' data-ns='{escape(ns, quote=True)}'>\n<td>{ns}</td>\n<td>{ew}</td>\n<td>{contract_open}</td>{tricks1}{res1}<td>{ew}</td>\n<td>{ns}</td>\n<td>{contract_closed}</td>{tricks2}{res2}{imp_positive}{imp_negative}</tr>\n"
        table1_html += row_html
        row_html = ""

    table1_html += "</table>\n</div>\n</div>\n"
    html += table1_html

    if getattr(sys, 'frozen', False):
        # Running as bundled
        base_path = sys._MEIPASS
    else:
        # Running normally
        base_path = os.path.dirname(__file__)

    css_path = os.path.join(base_path, 'listmatch.css')

    # Read the CSS file
    with open(css_path, 'r') as f:
        css_content = f.read()

    html_content = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='utf-8'>\n"
        "<title>Match deal</title>\n"
        "<style>\n"
            f"{css_content}\n"
            ".align-right { text-align: right; }\n"
            ".align-center { text-align: center; }\n"
            ".row-height { height: 22px; }\n"
            ".match-summary { margin-bottom: 20px; }\n"
            ".match-summary h2 { text-align: center; }\n"
            ".match-summary table { width: auto; table-layout: auto; margin: 10px auto; }\n"
            ".match-summary th, .match-summary td { white-space: nowrap; }\n"
            ".match-summary table.cross-table { border-collapse: collapse; font-size: 0.85em; margin: 10px auto 30px; }\n"
            ".cross-table th, .cross-table td { border: 1px solid #b8c4d6; padding: 2px 4px; text-align: center; }\n"
            ".cross-table th { background: #eef2f8; font-weight: normal; }\n"
            ".cross-table td.team-name { text-align: left; font-weight: bold; }\n"
            ".cross-table td.self { background: #d0d7e2; }\n"
            ".cross-table td.total { font-weight: bold; }\n"
            ".cross-table .vp, .cross-table .imps { display: block; }\n"
            ".cross-table .imps { color: #666; font-size: 0.85em; }\n"
            ".cross-table .win .vp { color: #1a7f37; font-weight: bold; }\n"
            ".cross-table .loss .vp { color: #b42318; }\n"
            ".cross-table .short { color: #888; }\n"
            ".team-filter { position: sticky; top: 0; z-index: 10; background: #fff; text-align: center; padding: 8px; border-bottom: 1px solid #b8c4d6; }\n"
            ".team-filter select { font-size: 1em; margin-left: 6px; }\n"
            ".freq-table { width: 300px; table-layout: auto; font-size: 12px; margin: 10px auto 0; }\n"
            ".freq-table th { background: #eef2f8; font-weight: normal; text-align: center; padding: 2px 4px; }\n"
            ".freq-table td { padding: 2px 4px; white-space: nowrap; }\n"
            ".board-section { align-items: flex-start; }\n"
            "</style>\n"
            "<script>\n"
            "function filterTeam(team) {\n"
            "  document.querySelectorAll('.results-container table').forEach(function (table) {\n"
            "    var n = 0;\n"
            "    table.querySelectorAll('tr[data-ns]').forEach(function (tr) {\n"
            "      var show = !team || tr.dataset.ns === team;\n"
            "      tr.style.display = show ? '' : 'none';\n"
            "      if (show) tr.style.backgroundColor = (n++ % 2) ? '#f0f0f0' : '#ffffff';\n"
            "    });\n"
            "  });\n"
            "}\n"
            "</script>\n"
        "</head>\n"
        "<body>\n"
        "<div style='display: flex; justify-content: center;'>\n"
        "<div style='margin-right: 20px;'>\n"
        f"{html}\n"
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>"
    )
        # Split the file path into directory and filename
    directory, _ = os.path.split(file_paths[0])

    if out_path is not None:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(html_content)
        print(f"{out_path} generated")
        return

    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".html", initialdir=directory, filetypes=file_types_html, initialfile="matchindex.html")
    if output_file is None:
        return
    output_file.writelines(html_content)
    output_file.close()
    print(f"{output_file.name} generated")

    # After closing the file
    webbrowser.open(f'file://{output_file.name}')

if __name__ == "__main__":
    main()

