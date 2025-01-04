# Count number of borad in a PBN-file
import sys
from endplay import Player
import endplay.parsers.pbn as pbn
from endplay.types.board import Board
import endplay.config as config
import io
import os
import tkinter as tk
from tkinter import filedialog
from collections import Counter

def remove_feasability_lines(file_path):
    # Read the contents of the file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Filter out lines starting with '{Feasability:'
    new_lines = [line for line in lines if not line.startswith('{Feasability:')]

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(new_lines))
    
    return fake_file

def main():

    print("PBN Renumber boards, Version 1.0.13")

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
    fakefile = remove_feasability_lines(file_path)

    try:
        boards = pbn.load(fakefile)
    except pbn.PBNDecodeError as e:
        print("OK: There was an issue decoding the PBN file.")
        print("Error message:", e)
        print("Current line:", e.line)
        print("Line number:", e.lineno)
        sys.exit(1)

    #Don't use unicode
    config.use_unicode = False 

    print(f"No of boards {len(boards)}")

    # Count the occurrences of each line
    deal_count = Counter()

     # Construct the output file
    # Split the file path into directory and filename
    directory, filename = os.path.split(file_path)

    # Insert "DDS" at the beginning of the filename
    new_filename = "Ordered_" + filename
    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".pbn", initialdir=directory, filetypes=file_types, initialfile=new_filename)

    if output_file is not None:
        selected_attributes = ['board_num', 'dealer', 'vul', 'deal']

        new_boards = []
        number = 1
        for index, board in enumerate(boards):
            #print(board.dealer, board.vul)
            if board.dealer > 0:
                # Switch vulnerabolity
                if board.dealer != 2:
                    if board.vul == 2:
                        board.vul = 3
                    else:
                        if board.vul == 3:
                            board.vul = 2
                board.dealer = Player(0)

            if deal_count[board.deal.to_pbn()] > 0:
                print(f"Duplicate deal: {board.deal.to_pbn()}")
                continue

            attributes = {attr: getattr(board, attr) for attr in selected_attributes}
            attributes['info'] = Board.Info()  # Add an empty 'info' dictionary
            new_board = Board(**attributes)  # Create a new Board object with selected attributes
            new_board.board_num = number  # Set the 'board_num' attribute explicitly
            number += 1
            new_boards.append(new_board)
            deal_count[board.deal.to_pbn()] += 1

        pbn.dump(new_boards, output_file)
        # Close the file after writing
        output_file.close()
        print(f"{output_file.name} generated")
    else:
        print("File not saved")

main()
