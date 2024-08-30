import sys
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
from endplay.types.board import Board
import endplay.config as config
import os
import io
import re
import tkinter as tk
from tkinter import filedialog

# Define a function to convert room values to numeric values for sorting


def room_to_numeric(room):
    if room == "Open":
        return 0
    elif room == "Closed":
        return 1
    else:
        return 2  # Handle other cases as needed


def modify_event_string(original_string):
    if original_string == '[Event ""]':
        return original_string
    match = re.match(r'\[Event\s"([^"]+)"\]', original_string)
    if match:
        return original_string  # Return if the name is already in quotes

    # If not in quotes, find the event name and add quotes around it
    parts = re.split(r'\[Event\s', original_string)
    if len(parts) > 1:
        event_name = parts[1][:-1]  # Remove the trailing "]"
        modified_string = f'[Event "{event_name}"]'
        return modified_string
    else:
        return original_string  # Return original if no match found


def update_event_and_feasability(file_path):
    # Read the contents of the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("[Event "):
            lines[i] = modify_event_string(line.strip())

    # Filter out lines starting with '{Feasability:'
    new_lines = [line for line in lines if not line.startswith('{Feasability:')]

    # Filter out lines starting with '{Feasability:'
    lines = [line for line in new_lines if not line.startswith('{PAR of')]

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file

def update_event_and_feasability(file_path):
    # Read the contents of the file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file

def getScore(str):
    if "NS" in str:
        return int(str.split(" ")[1])
    
    elif "EW" in str:
        return -int(str.split(" ")[1])
    return 0

def main():

    print("Split PBN in 3 files. Doubled and making, more than 2000 from par, and the rest, Version 1.0.11")
    # create a root window
    root = tk.Tk()
    root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]
    # open the file dialog box
    file_path = filedialog.askopenfilename(initialdir=".", filetypes=file_types)

    # print the selected file path
    if not file_path:
        sys.exit(1)

    # Call the function to remove lines and save the file
    fakefile = update_event_and_feasability(file_path)

    try:
        boards = pbn.load(fakefile)
    except pbn.PBNDecodeError as e:
        print("OK: There was an issue decoding the PBN file.")
        print("Error message:", e)
        print("Current line:", e.line)
        print("Line number:", e.lineno)
        sys.exit(1)

    # Don't use unicode
    db_making = []
    disaster = []
    ok_boards = []
    config.use_unicode = False
    for i in range(len(boards)):
        skip = False
        if boards[i].contract.penalty > 1:
            if boards[i].contract.result > 0:
                print(boards[i].board_num, boards[i].contract,  boards[i].info.Score, boards[i].info.OptimumScore)
                db_making.append(boards[i])
                skip = True

        NS_Score = getScore(boards[i].info.Score)
        PAR_Score = getScore(boards[i].info.OptimumScore)
        if abs(NS_Score - PAR_Score) > 2000:
            print(boards[i].board_num, boards[i].contract,  boards[i].info.Score, boards[i].info.OptimumScore)
            disaster.append(boards[i])
            skip = True

        if not skip:
            ok_boards.append(boards[i])

    print(f"No of OK boards {len(ok_boards)}")
    with open("OK_boards.pbn", 'w') as output_file:
        pbn.dump(ok_boards, output_file)
        print(f"OK_boards.pbn generated")

    print(f"No of disaster boards {len(disaster)}")
    with open("disaster.pbn", 'w') as output_file:
        pbn.dump(disaster, output_file)
        print(f"disaster.pbn generated")

    print(f"No of db making boards {len(db_making)}")
    with open("db_making.pbn", 'w') as output_file:
        pbn.dump(db_making, output_file)
        print(f"db_making.pbn generated")

if __name__ == "__main__":
    main()
