import sys
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
from endplay.types.board import Board
from endplay.types.deal import Deal
import endplay.config as config
import os
import io
import re
import tkinter as tk
from tkinter import filedialog

# Define the rank and suit mappings
rank_map = {
    1: 'A', 2: 'K', 3: 'Q', 4: 'J', 5: 'T', 6: '9', 7: '8', 8: '7', 9: '6', 10: '5', 11: '4', 12: '3', 13: '2'
}

def convert_to_pbn(card_string):
    cards = []
    # Process each card (2 characters)
    for i in range(0, len(card_string), 2):
        card = card_string[i:i+2]
        cards.append(int(card))

    north = ""
    east = ""
    south = ""
    west = ""
    for j in range(4):
        for i in range(13):
            thiscard = j * 13 + i + 1
            if thiscard in cards:
                hand = cards.index(thiscard)
                if hand // 13 == 0:
                    north += rank_map[i+1]
                elif hand // 13 == 1:
                    east += rank_map[i+1]
                elif hand // 13 == 2:
                    south += rank_map[i+1]
            else:
                west += rank_map[i+1]
        
        if j < 3:
            north += '.'
            east += '.'
            south += '.'
            west += '.'

    deal = f"N:{north} {east} {south} {west}"    
    
    return deal

def main():

    print("csvLin -> PBN, Version 1.0.16")
    # create a root window
    root = tk.Tk()
    root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.csv"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]
    # open the file dialog box
    file_path = filedialog.askopenfilename(initialdir=".", filetypes=file_types)

    # print the selected file path
    if not file_path:
        sys.exit(1)

    with open(file_path, 'r') as file:
        lines = file.readlines()[1:]

    print(f"No of boards {len(lines)}")

    boards = []
    for i in range(len(lines)):
        line = lines[i].strip().split(';')
        board = Board()
        board.board_num = int(line[1])

        board.deal = Deal.from_pbn(convert_to_pbn(line[4]))
        boards.append(board)


    # Split the file path into directory and filename
    directory, filename = os.path.split(file_path)

    # Insert "DDS" at the beginning of the filename
    new_filename = filename.replace(".csv", ".pbn")

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]

    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".pbn", initialdir=directory, filetypes=file_types, initialfile=new_filename)

    if output_file is not None:
        # Save the data to the selected file
        pbn.dump(boards, output_file)

        # Close the file after writing
        output_file.close()
        print(f"{output_file.name} generated")
    else:
        print("File not saved")


if __name__ == "__main__":
    main()
