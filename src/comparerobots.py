import os
import json
import sys
import scoring
import compare
import tkinter as tk
from tkinter import filedialog, messagebox
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
import webbrowser
import re
import urllib.parse

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

def generate_html_deal(dealer, vulnerable, cards, board_number):
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
         </div>"""
    return html


def load(fin):
    data_list = []
    dealer = ""
    ns = ""
    ew = ""
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
    print("List matches as html, Version 1.0.17")
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


    # open the file dialog box
    file_paths = filedialog.askopenfilenames(initialdir=".", filetypes=file_types)

    new_data_list = []
    for file_path in file_paths:
        print(file_path)
        try:
            with open(file_path, "r", encoding='utf-8') as file:  # Open the input file with UTF-8 encoding
                pbn_boards = pbn.load(file)
            with open(file_path, "r", encoding='utf-8') as file:  # Open the input file with UTF-8 encoding
                lines = file.readlines()
            data_list = load(lines)

            for i in range(0, len(data_list), 1):
                lin_board_open = encode_annotations(lin.LINEncoder().serialise_board(pbn_boards[i ]))
                data_list[i] = data_list[i] + (lin_board_open,)
        except Exception as ex:
            print('Error:', ex)
            raise ex
        new_data_list.extend(data_list)



    # Sort the data_list based on board number  
    sorted_data = sorted(new_data_list, key=lambda x: x[0], reverse=False)

    #sorted_data = sorted([x for x in new_data_list if x[0] == 1], key=lambda x: x[1])

    # Generate the HTML tables
    row_html = ""
    old_board = -1
    table1_html = ""
    html = ""
    for i, board_data in enumerate(sorted_data):

        board, ns, ew, dealer, vul, declarer1, contract1, result1, score1, hands_pbn, lin_open = board_data
        if board != old_board:
            if i > 0:
                table1_html += "</table>\n</div>\n</div>\n"
                html += table1_html
            html += generate_html_deal(dealer, vul, hands_pbn, board)
            table1_html = "\n<div class='results-container'>\n"
            table1_html += "\n<table class='border-collapse table-container'>\n"
            table1_html += "<tr>\n"
            table1_html += "<th class='col-name'>NS</th>\n"
            table1_html += "<th class='col-name'>EW</th>\n"
            table1_html += "<th class='col-contract'>Contract</th>\n"
            table1_html += "<th class='col-tricks'>Tricks</th>\n"
            table1_html += "<th class='col-result'>Result</th>\n"
            table1_html += "</tr>\n"
            old_board = board

        # Align right for Result and Tricks columns
        tricks1 = f"<td class='align-right'>{result1}</td>" if result1 is not None else "<td class='align-right'></td>"
        res1 = f"<td class='align-right'>{score1}</td>" if score1 is not None else "<td class='align-right'></td>"

        link_open = "https://www.bridgebase.com/tools/handviewer.html?lin=" + lin_open
        contract_open = f"<a href='{link_open}' target='_blank'>{declarer1} {contract1}</a>"
        # Add class to the row based on imp value
        row_height_class = "row-height"
        row_html += f"<tr class='{row_height_class}'>\n<td>{ns}</td>\n<td>{ew}</td>\n<td>{contract_open}</td>{tricks1}{res1}</tr>\n"
        table1_html += row_html
        row_html = ""

    table1_html += "</table></div</div>\n"
    html += table1_html

    if getattr(sys, 'frozen', False):
        # Running as bundled
        base_path = sys._MEIPASS
    else:
        # Running normally
        base_path = os.path.dirname(__file__)

    css_path = os.path.join(base_path, 'robotcompare.css')

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
            "</style>\n"
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

