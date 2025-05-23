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
    lines = [line for line in new_lines if not line.startswith('{PAR of')]

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file


def main():

    print("PBN add room, Version 1.0.15")
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

    # Loop through the array and set the alternating text attribute
    for i, board in enumerate(boards):
        board.info.room = room[i % len(room)]
        if boards[i].board_num != i // 2 + 1:
            print("Missing a board:",i // 2 + 1)
            sys.exit()

    # Sort the array of Board objects based on board.number and board.info.room
    boards = sorted(
        boards,
        key=lambda board: (board.board_num, room_to_numeric(board.info.room))
    )

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
    new_filename = "Room_" + filename

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
