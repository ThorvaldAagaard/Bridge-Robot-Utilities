import sys
import endplay.parsers.pbn as pbn
from endplay.types.board import Board
import endplay.config as config
import argparse
import io
import os
import math
import bisect
import tkinter as tk
from tkinter import filedialog



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

    print("Table Manager PBN Extract, Version 1.0.14")
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
    room = ["Open", "Closed"]

    print("Number of boards:", len(boards))
    print("Last board:", boards[len(boards)-1].board_num)
    # Sort the array of Board objects based on board.number and board.info.room
    boards = sorted(
        boards,
        key=lambda board: (board.board_num)
    )

     # Construct the output file
    # Split the file path into directory and filename
    directory, filename = os.path.split(file_path)

    # Insert "DDS" at the beginning of the filename
    new_filename = "Extract_" + filename

    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".pbn", initialdir=directory, filetypes=file_types, initialfile=new_filename)

    if output_file is not None:
        selected_attributes = ['board_num', 'dealer', 'vul', 'deal']

        new_boards = []

        board_num = 1
        for board in boards:
            
            attributes = {attr: getattr(board, attr) for attr in selected_attributes}
            attributes['info'] = Board.Info()  # Add an empty 'info' dictionary
            new_board = Board(**attributes)  # Create a new Board object with selected attributes
            if new_board.board_num == board_num:
                new_boards.append(new_board)
                board_num += 1

        pbn.dump(new_boards, output_file)
        # Close the file after writing
        output_file.close()
        print(f"{output_file.name} generated")
    else:
        print("File not saved")


if __name__ == "__main__":
    main()

