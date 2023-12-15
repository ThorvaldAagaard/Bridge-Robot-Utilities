import json
import sys
import scoring
import compare
import tkinter as tk
from tkinter import filedialog

# Read the file line by line and process each JSON object

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
                X = scoring.score(contract_parts, v , int(result))
                if declarer == "E":
                    X = -X
                if declarer == "W":
                    X= -X
                #print(f"Appending board {board}")
                data_list.append((int(board), vulnerable, declarer, contract_parts, int(result), X))
                dealer= None
        if line.startswith('[Dealer'):
            dealer = extract_value(line)
        if line.startswith('[Declarer'):
            declarer = extract_value(line)
        if line.startswith('[Contract'):
            contract_parts = extract_value(line.upper())
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
    return data_list

def extract_value(s: str) -> str:
    return s[s.index('"') + 1 : s.rindex('"')]

def main():
    print("HTML Generator fpr PBN, Version 1.0")
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
    file_path = filedialog.askopenfilename(initialdir=".", filetypes=file_types)

    # print the selected file path
    if not file_path:
        sys.exit(1)

    try:
        with open(file_path, "r", encoding='utf-8') as file:  # Open the input file with UTF-8 encoding
            lines = file.readlines()
        data_list = load(lines)

    except Exception as ex:
        print('Error:', ex)
        raise ex

    new_data_list = []
    positive_imp_sum = 0
    negative_imp_sum = 0

    #print(data_list)
    for i in range(0, len(data_list), 2):
        if (i+1 >= len(data_list)): 
            continue
        imp = compare.get_imps(data_list[i][-1],data_list[i+1][-1])
        # Sum positive and negative imp values
        if imp > 0:
            positive_imp_sum += imp
        else:
            negative_imp_sum += imp

        merged_tuple = data_list[i] + data_list[i + 1][2:] + (imp,)
        new_data_list.append(merged_tuple)

    #print(new_data_list)

    # Sort the data_list based on the imp value in descending order
    sorted_data = sorted(new_data_list, key=lambda x: x[0], reverse=False)

    # Generate the HTML tables
    table1_html = "<table class='border-collapse table-container'>"
    table1_html += "<style>"
    table1_html += "th { background-color: #4a86e8; color: white; }"
    table1_html += ".align-right { text-align: right; }"
    table1_html += ".positive-imp { background-color: #b8e994; }"
    table1_html += ".negative-imp { background-color: #ff7675; }"
    table1_html += ".zero-imp { background-color: white; }"
    table1_html += ".align-center { text-align: center; }"
    table1_html += ".row-height { height: 22px; }"
    table1_html += "</style>"
    table1_html += "<tr><th>Board</th><th>Contract</th><th>Tricks</th><th>Result</th><th>Contract</th><th>Tricks</th><th>Result</th><th class='align-right'>Imps (+)</th><th class='align-right'>Imps (-)</th></tr>"

    table2_html = "<table class='border-collapse table-container'>"
    table2_html += "<style>"
    table2_html += "th { background-color: #4a86e8; color: white; }"
    table2_html += ".align-right { text-align: right; }"
    table2_html += ".positive-imp { background-color: #b8e994; }"
    table2_html += ".negative-imp { background-color: #ff7675; }"
    table2_html += ".zero-imp { background-color: white; }"
    table2_html += ".align-center { text-align: center; }"
    table2_html += ".row-height { height: 22px; }"
    table2_html += "</style>"
    table2_html += "<tr><th>Board</th><th>Contract</th><th>Tricks</th><th>Result</th><th>Contract</th><th>Tricks</th><th>Result</th><th class='align-right'>Imps (+)</th><th class='align-right'>Imps (-)</th></tr>"

    for i, board_data in enumerate(sorted_data):
        board, vul, declarer1, contract1, result1, score1, declarer2, contract2, result2, score2, imp = board_data

        #print(board_data)
        # Align right for Result and Tricks columns
        res1 = f"<td class='align-right'>{score1}</td>" if score1 is not None else "<td class='align-right'></td>"
        tricks1 = f"<td class='align-right'>{result1}</td>" if result1 is not None else "<td class='align-right'></td>"
        res2 = f"<td class='align-right'>{score2}</td>" if score2 is not None else "<td class='align-right'></td>"
        tricks2 = f"<td class='align-right'>{result2}</td>" if result2 is not None else "<td class='align-right'></td>"

        # Split Imps column into positive and negative columns
        imp_positive = f"<td class='align-right'>{imp if imp > 0 else '--'}</td>"
        imp_negative = f"<td class='align-right'>{abs(imp) if imp < 0 else '--'}</td>"

        # Add class to the row based on imp value
        row_class = "positive-imp" if imp > 0 else "negative-imp" if imp < 0 else "zero-imp"
        row_height_class = "row-height"
        row_html = f"<tr class='{row_class} {row_height_class}'><td class='align-center'><a href='BEN.htm#Board{board}Open'>{board}</a></td><td>{declarer1} {contract1}</td>{tricks1}{res1}<td>{declarer2} {contract2}</td>{tricks2}{res2}{imp_positive}{imp_negative}</tr>\n"

        # Split rows evenly between the two tables
        if i < len(sorted_data) / 2:
            table1_html += row_html
        else:
            table2_html += row_html

    table1_html += "</table>"
    table2_html += "</table>"

    # Print the winner at the top of the tables with <h1> tags
    total_imp_sum = positive_imp_sum + negative_imp_sum
    if total_imp_sum > 0:
        win_html = f"<h1>NS wins by {total_imp_sum}</h1>\n"
    elif total_imp_sum < 0:
        win_html = f"<h1>EW wins by {abs(total_imp_sum)}</h1>\n"
    else:
        win_html = "<h1>It is a draw</h1>\n"

    html_content = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='utf-8'>\n"
        "<title>Match deal</title>\n"
        "<link rel='stylesheet' href='viz.css'>\n"
        "</head>\n"
        "<body>\n"
        f"<div style='display: flex; justify-content: center;'>\n"
        f"<p><h1 style='text-align: center;'>\n"
        f"{win_html}\n"
        f"</h1></p>\n"
        f"</div>\n"
        f"<div style='display: flex; justify-content: center;'>\n"
        f"<div style='margin-right: 20px;'>\n"
        f"{table1_html}\n"
        f"</div>\n"
        f"<div>\n"
        f"{table2_html}\n"
        f"</div>\n"
        f"</div>\n"
        f"<p style='text-align: center;'><b>Final score:</b> NS: {positive_imp_sum}, EW: {abs(negative_imp_sum)}</p>\n"
        "</body>\n"
        "</html>"
    )
    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".html", initialdir=".", filetypes=file_types_html, initialfile="index.html")
    output_file.writelines(html_content)
    output_file.close()
    print(f"{output_file.name} generated")


if __name__ == "__main__":
    main()

