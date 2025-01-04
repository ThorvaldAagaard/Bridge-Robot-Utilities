import os
import json
import sys
import scoring
import compare
import tkinter as tk
from tkinter import filedialog, messagebox

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
                if (contract_parts != ""):
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
        if declarer == "E":
            X = -X
        if declarer == "W":
            X= -X
        #print(f"Appending board {board}")
        data_list.append((int(board), vulnerable, declarer, contract_parts, int(result), X))
        dealer= None
    return data_list

def extract_value(s: str) -> str:
    return s[s.index('"') + 1 : s.rindex('"')]

def main():
    print("Compare match as html, Version 1.0.13")
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

    # Show an info message to inform the user that they need to select 2 files
    messagebox.showinfo("File Selection", "Please select exactly 2 files.")

    # open the file dialog box
    file_paths = filedialog.askopenfilenames(initialdir=".", filetypes=file_types)

    # Print the selected file paths
    if len(file_paths) != 2:  # Check if the user selected exactly 2 files
        messagebox.showerror("Error", "You must select exactly 2 files. Please try again.")
        sys.exit(1)

    # If valid, proceed with the selected file paths
    file1 = file_paths[0]
    file2 = file_paths[1]

    print(f"File 1: {file1}")
    print(f"File 2: {file2}")

    try:
        with open(file1, "r", encoding='utf-8') as file:  # Open the input file with UTF-8 encoding
            lines = file.readlines()
        data_list1 = load(lines)
        with open(file2, "r", encoding='utf-8') as file:  # Open the input file with UTF-8 encoding
            lines = file.readlines()
        data_list2 = load(lines)

    except Exception as ex:
        print('Error:', ex)
        raise ex

    if len(data_list1) % 2 != 0:
        print("Error: The number of boards must be even.")
        input("\n Press any key to exit...")
        sys.exit(1)

    if len(data_list2) % 2 != 0:
        print("Error: The number of boards must be even.")
        input("\n Press any key to exit...")
        sys.exit(1)

    if len(data_list2) != len(data_list2):
        print("Error: The number of boards must match.")
        input("\n Press any key to exit...")
        sys.exit(1)

    new_data_list1 = []
    positive_imp_sum1 = 0
    negative_imp_sum1 = 0
    new_data_list2 = []
    positive_imp_sum2 = 0
    negative_imp_sum2 = 0

    #print(data_list)
    for i in range(0, len(data_list1), 2):
        #if (i > len(data_list)): 
        #    continue
        imp = compare.get_imps(data_list1[i][-1],data_list1[i+1][-1])
        # Sum positive and negative imp values
        if imp > 0:
            positive_imp_sum1 += imp
        else:
            negative_imp_sum1 += imp

        merged_tuple = data_list1[i] + data_list1[i + 1][2:] + (imp,)
        new_data_list1.append(merged_tuple)

    #print(data_list)
    for i in range(0, len(data_list2), 2):
        #if (i > len(data_list)): 
        #    continue
        imp = compare.get_imps(data_list2[i][-1],data_list2[i+1][-1])
        # Sum positive and negative imp values
        if imp > 0:
            positive_imp_sum2 += imp
        else:
            negative_imp_sum2 += imp

        merged_tuple = data_list2[i] + data_list2[i + 1][2:] + (imp,)
        new_data_list2.append(merged_tuple)

    # Sort the data_list based on the imp value in descending order
    sorted_data = sorted(new_data_list1 + new_data_list2, key=lambda x: x[0], reverse=False)

    # Generate the HTML tables
    table1_html = "<table class='border-collapse table-container'>\n"
    table1_html += "<tr><th>Board</th><th>Contract</th><th>Tricks</th><th>Result</th><th>Contract</th><th>Tricks</th><th>Result</th><th class='align-right'>Imps (+)</th><th class='align-right'>Imps (-)</th></tr>\n"
    row_html = ""
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
        row_class = "zero-imp"
        row_height_class = "row-height"
        row_html += f"<tr class='{row_class} {row_height_class}'><td class='align-center'><a href='Match{i % 2 + 1}.htm#Board{board}Open'>{board}</a></td><td>{declarer1} {contract1}</td>{tricks1}{res1}<td>{declarer2} {contract2}</td>{tricks2}{res2}{imp_positive}{imp_negative}</tr>\n"
        if i % 2 == 1:
            imp_change = imp - sorted_data[i - 1][-1]
            if imp_change == 0:
                row_html = ""
                continue
            if imp_change > 0:
                row_class = "positive-imp"
            if imp_change < 0:
                row_class = "negative-imp"
            if imp_change > 6:
                row_class = "good-imp"
            if imp_change < -6:
                row_class = "bad-imp"
            row_html += f"<tr class='{row_class} {row_height_class}'><td class='align-center'>{board}</td><td colspan=\"6\"></td><td colspan=\"2\" class='align-center'>{imp_change if imp_change != 0 else '--'}</td></tr>\n"
            table1_html += row_html
            row_html = ""

    table1_html += "</table>"

    # Print the winner at the top of the tables with <h1> tags
    total_imp_sum1 = positive_imp_sum1 + negative_imp_sum1
    if total_imp_sum1 > 0:
        win_html1 = f"<h1>Match 1: NS wins by {total_imp_sum1}</h1>\n"
    elif total_imp_sum1 < 0:
        win_html1 = f"<h1>Match 1: EW wins by {abs(total_imp_sum1)}</h1>\n"
    else:
        win_html1 = "<h1>Match 1: It is a draw</h1>\n"
    # Print the winner at the top of the tables with <h1> tags
    total_imp_sum2 = positive_imp_sum2 + negative_imp_sum2
    if total_imp_sum2 > 0:
        win_html2 = f"<h1>Match 2: NS wins by {total_imp_sum2}</h1>\n"
    elif total_imp_sum2 < 0:
        win_html2 = f"<h1>Match 2: EW wins by {abs(total_imp_sum2)}</h1>\n"
    else:
        win_html2 = "<h1>Match 2: It is a draw</h1>\n"

    html_content = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='utf-8'>\n"
        "<title>Match deal</title>\n"
        "<link rel='stylesheet' href='viz.css'>\n"
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
        f"{win_html1}\n"
        "</div>\n"
        "<div style='display: flex; justify-content: center;'>\n"
        f"{win_html2}\n"
        "</div>\n"
        "<div style='display: flex; justify-content: center;'>\n"
        "<div style='margin-right: 20px;'>\n"
        f"{table1_html}\n"
        "</div>\n"
        "</div>\n"
        f"<p style='text-align: center;'><b>Final score Match 1:</b> NS: {positive_imp_sum1}, EW: {abs(negative_imp_sum1)}</p>\n"
        f"<p style='text-align: center;'><b>Final score Match 2:</b> NS: {positive_imp_sum2}, EW: {abs(negative_imp_sum2)}</p>\n"
        "</body>\n"
        "</html>"
    )
        # Split the file path into directory and filename
    directory, _ = os.path.split(file1)

    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".html", initialdir=directory, filetypes=file_types_html, initialfile="index.html")
    output_file.writelines(html_content)
    output_file.close()
    print(f"{output_file.name} generated")


if __name__ == "__main__":
    main()

