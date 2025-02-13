import os
import json
import sys
import scoring
import compare
import tkinter as tk
from tkinter import filedialog, messagebox

# Read the file line by line and process each JSON object
import sys
import os

def generate_html_card(suit, cards):
    html = f"<div class='suit'><span>{suit}</span>"
    for card in cards:
        html += f"{card}"
    html += "</div>"
    return html

def generate_html_deal(dealer, vulnerable, cards, board_number):
    cards = cards.split(':')[1].split()
    html = f"""
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
        </div>"""
    return html


def load(fin):
    data_list = []
    dealer = ""
    dealer, vulnerable = None, None
    for line in fin:
        #print(line)
        if line.startswith("% PBN") or line == "\n":
            if dealer != None:
                v = False
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
                #print(f"Appending board {board}")
                data_list.append((int(board), ns, ew, dealer, vulnerable, declarer, contract_parts, int(result), X, hands_pbn))
                dealer= None
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
    print("List matches as html, Version 1.0.14")
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
                lines = file.readlines()
            data_list = load(lines)

            if len(data_list) % 2 != 0:
                print("Error: The number of boards must be even.")
                input("\n Press any key to exit...")
                sys.exit(1)

            if len(data_list) % 2 != 0:
                print("Error: The number of boards must be even.")
                input("\n Press any key to exit...")
                sys.exit(1)


            #print(data_list)
            for i in range(0, len(data_list), 2):
                #if (i > len(data_list)): 
                #    continue
                imp = compare.get_imps(data_list[i][-2],data_list[i+1][-2])
                merged_tuple = data_list[i] + data_list[i + 1][5:-1] + (imp,)
                new_data_list.append(merged_tuple)

        except Exception as ex:
            print('Error:', ex)
            raise ex



    # Sort the data_list based on the imp value in descending order
    sorted_data = sorted(new_data_list, key=lambda x: x[0], reverse=False)

    # Generate the HTML tables
    row_html = ""
    old_board = -1
    table1_html = ""
    html = ""
    for i, board_data in enumerate(sorted_data):

        board, ns, ew, dealer, vul, declarer1, contract1, result1, score1, hands_pbn, declarer2, contract2, result2, score2, imp = board_data
        if board != old_board:
            if i > 0:
                table1_html += "</table>\n"
                html += table1_html
            html += generate_html_deal(dealer, vul, hands_pbn, board)
            table1_html = "\n<table class='border-collapse table-container'>\n"
            table1_html += "<tr><th>Board</th><th>NS</th><th>EW</th><th>Contract</th><th>Tricks</th><th>Result</th><th>NS</th><th>EW</th><th>Contract</th><th>Tricks</th><th>Result</th><th class='align-right'>Imps (+)</th><th class='align-right'>Imps (-)</th></tr>\n"
            old_board = board
        # Align right for Result and Tricks columns
        res1 = f"<td class='align-right'>{score1}</td>" if score1 is not None else "<td class='align-right'></td>"
        tricks1 = f"<td class='align-right'>{result1}</td>" if result1 is not None else "<td class='align-right'></td>"
        res2 = f"<td class='align-right'>{score2}</td>" if score2 is not None else "<td class='align-right'></td>"
        tricks2 = f"<td class='align-right'>{result2}</td>" if result2 is not None else "<td class='align-right'></td>"

        # Split Imps column into positive and negative columns
        imp_positive = f"<td class='align-right'>{imp if imp > 0 else '--'}</td>"
        imp_negative = f"<td class='align-right'>{abs(imp) if imp < 0 else '--'}</td>"

        # Add class to the row based on imp value
        row_class = "zero-imp"
        row_height_class = "row-height"
        row_html += f"<tr class='{row_class} {row_height_class}'><td class='align-center'>{board}</td><td>{ns}</td><td>{ew}</td><td>{declarer1} {contract1}</td>{tricks1}{res1}<td>{ew}</td><td>{ns}</td><td>{declarer2} {contract2}</td>{tricks2}{res2}{imp_positive}{imp_negative}</tr>\n"
        table1_html += row_html
        row_html = ""

    table1_html += "</table>"
    html += table1_html

    html_content = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='utf-8'>\n"
        "<title>Match deal</title>\n"
        "<link rel='stylesheet' href='viz.css'>\n"
        "<script src='viz.js'></script>\n"
        "<style>\n"
            ".th { background-color: #4a86e8; color: white; }\n"
            ".align-right { text-align: right; }\n"
            ".good-imp { background-color: #a0c15a; }\n"
            ".bad-imp { background-color: #ff8c5a; }\n"
            ".positive-imp { background-color: #add633; }\n"
            ".negative-imp { background-color: #ffb234; }\n"
            ".zero-imp { background-color: white; }\n"
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
    output_file.writelines(html_content)
    output_file.close()
    print(f"{output_file.name} generated")


if __name__ == "__main__":
    main()

