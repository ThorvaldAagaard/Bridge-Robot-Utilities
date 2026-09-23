# Drop incomplete deals, set dealer/vulnerability from the new board number, remove duplicate deals and renumber the boards in a PBN-file
import sys
import endplay.parsers.pbn as pbn
import endplayfix  # endplay drops [Dealer] on boards without a contract
from endplay.types.board import Board
import endplay.config as config
import io
import os
import tkinter as tk
from tkinter import filedialog
import lastdir
import dealkey

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

    print("Reset and Renumber PBN Boards, Version 1.0.21")

    # create a root window
    root = tk.Tk()
    root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]
    # open the file dialog box
    file_path = filedialog.askopenfilename(initialdir=lastdir.get_last_dir(key="renumber"), filetypes=file_types)
    if file_path:
        lastdir.set_last_dir(file_path, key="renumber")

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

    # Deals kept so far: rotation key -> (hands, dealer, vulnerability), so rotated copies are dropped too
    seen_deals = {}

     # Construct the output file
    # Split the file path into directory and filename
    directory, filename = os.path.split(file_path)

    # Insert "DDS" at the beginning of the filename
    new_filename = "Ordered_" + filename
    # Get the file path to save the data
    output_file = filedialog.asksaveasfile(defaultextension=".pbn", initialdir=directory, filetypes=file_types, initialfile=new_filename)

    if output_file is not None:
        # Dealer and vulnerability are left unset, so endplay derives them from the new board number
        selected_attributes = ['deal']

        new_boards = []
        incomplete = 0
        number = 1
        for index, board in enumerate(boards):
            # Leave out partial deals: every hand must hold 13 different cards
            hands = dealkey.hands_from_north(board.deal.to_pbn())
            problem = dealkey.deal_problem(hands)
            if problem:
                print(f"Incomplete deal, board {board.board_num} left out: {problem}")
                incomplete += 1
                continue

            # Check for copies against the original dealer and vulnerability, as a rotated copy has them turned too
            key = dealkey.rotation_key(hands)
            first = seen_deals.get(key)
            if first is not None:
                if first[0] == hands:
                    print(f"Duplicate deal: {board.deal.to_pbn()}")
                    continue
                if dealkey.same_board(*first, hands, board.dealer, board.vul):
                    print(f"Rotated duplicate deal: {board.deal.to_pbn()}")
                    continue
                print(f"Rotated deal kept, dealer or vulnerability differs: {board.deal.to_pbn()}")
            else:
                seen_deals[key] = (hands, board.dealer, board.vul)

            attributes = {attr: getattr(board, attr) for attr in selected_attributes}
            attributes['info'] = Board.Info()  # Add an empty 'info' dictionary
            new_board = Board(**attributes)  # Create a new Board object with selected attributes
            new_board.board_num = number  # Set the 'board_num' attribute explicitly
            number += 1
            new_boards.append(new_board)

        if incomplete:
            print(f"{incomplete} incomplete deals left out")
        pbn.dump(new_boards, output_file)
        # Close the file after writing
        output_file.close()
        print(f"{output_file.name} generated")
    else:
        print("File not saved")

if __name__ == "__main__":
    main()
