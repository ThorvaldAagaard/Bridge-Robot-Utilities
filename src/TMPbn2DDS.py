import sys
import endplay.parsers.pbn as pbn
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
    new_lines = [line for line in new_lines if not line.startswith('"')]

    # Filter out lines starting with '{Feasability:'
    lines = [line for line in new_lines if not line.startswith('{PAR of')]

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file


def main():

    print("PBN cleaner for DDS, Version 1.0.15")
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
    config.use_unicode = False
    room = ["Open", "Closed"]

    # If two first boards have the same number we assume it is from Bridge Moniteur
    BM = boards[0].board_num == boards[1].board_num
    if (BM):
        print("File from Bridge Monituer")
        # Loop through the array and set the alternating text attribute
        for i, board in enumerate(boards):
            board.info.room = room[i % len(room)]
            if boards[i].board_num != i // 2 + 1:
                print(f"Missing a board. Found {boards[i].board_num} expected {i // 2 + 1}")

    else:
        # Sort the array of Board objects based on board.number 
        boards = sorted(
            boards,
            key=lambda board: (board.board_num)
        )
        # From Blue Chip, or Bridge Monituer without instant replay
        # Loop through the array and set the alternating text attribute
        for i, board in enumerate(boards):

            if board.info.room is None:
                if i % 2 == 0:
                    board.info.room = room[0]
                else:
                    board.info.room = room[1]
            print(board.board_num, board.info.room)


    if (BM):
        # From Bridge Moniteur
        # Now all the boards in the closed room is rotated 90 degress, so we need to rotate it back.
        for index, board in enumerate(boards[1::2]):
            original_index = 2 * index + 1
            boards[original_index].deal = boards[original_index - 1].deal
            boards[original_index].vul = boards[original_index - 1].vul
            boards[original_index].dealer = boards[original_index - 1].dealer
            board.contract.declarer = ((board.contract.declarer - 1) + 4) % 4
            temp = board.info.north
            board.info.north = board.info.east
            board.info.east = board.info.south
            board.info.south = board.info.west
            board.info.west = temp

    # Loop through the array and set the alternating text attribute
    for i, board in enumerate(boards):
        board.board_num = (i // 2) + 1
        board.info.scoring = "IMP"
        if board.contract.declarer in (0, 2):
            board.info.score = f'NS {board.contract.score(board.vul)}'
        else:
            board.info.score = f'EW {board.contract.score(board.vul)}'

    # Split the file path into directory and filename
    directory, filename = os.path.split(file_path)

    # Insert "DDS" at the beginning of the filename
    new_filename = "DDS_" + filename

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
