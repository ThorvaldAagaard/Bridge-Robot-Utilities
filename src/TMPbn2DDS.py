import sys
import endplay.parsers.pbn as pbn
from endplay.types.board import Board
import endplay.config as config
import argparse
import io
import os

# Define a function to convert room values to numeric values for sorting
def room_to_numeric(room):
    if room == "Open":
        return 0
    elif room == "Closed":
        return 1
    else:
        return 2  # Handle other cases as needed

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

    print("PBN cleaner for DDS, Version 1.0")
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="")

    # Add a positional argument for the name
    parser.add_argument("input", help="filename for conversion")
    parser.add_argument("output", help="filename for conversion")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the function to remove lines and save the file
    fakefile = remove_feasability_lines(args.input)

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

    # If two first boards have the same number we assume it is from Bridge Moniteur
    BM = boards[0].board_num == boards[1].board_num
    print("File from Bridge Monituer")
    if (BM):
        # Loop through the array and set the alternating text attribute
        for i, board in enumerate(boards):
            board.info.room = room[i % len(room)]

    else:
        # From Blue Chip, or Bridge Monituer without instant replay
        # Loop through the array and set the alternating text attribute
        for i, board in enumerate(boards):
            if board.info.room is None:
                if i < len(boards) / 2:
                    board.info.room = room[0]
                else:
                    board.info.room = room[1]

    if (BM):
        # From Bridge Moniteur
        # Now all the boards in the closed room is rotated 90 degress, so we need to rotate it back.
        for index, board in enumerate(boards[1::2]):
            original_index = 2 * index + 1
            boards[original_index].deal = boards[original_index -  1].deal
            boards[original_index].vul = boards[original_index -  1].vul
            boards[original_index].dealer = boards[original_index -  1].dealer
            board.contract.declarer = ((board.contract.declarer - 1) + 4) % 4
            temp = board.info.north
            board.info.north = board.info.east
            board.info.east = board.info.south
            board.info.south = board.info.west
            board.info.west = temp
    else:
        # Sort the array of Board objects based on board.number and board.info.room
        boards = sorted(
            boards,
            key=lambda board: (board.board_num, room_to_numeric(board.info.room))
        )

    # Loop through the array and set the alternating text attribute
    for i, board in enumerate(boards):
        board.info.scoring = "IMP"
        if board.contract.declarer in (0, 2):
            board.info.score = f'NS {board.contract.score(board.vul)}'
        else:
            board.info.score = f'EW {board.contract.score(board.vul)}'

     # Construct the output file
    output_file_path = args.output

    with open(output_file_path, 'w') as output_file:
        pbn.dump(boards, output_file)

    print(f"{output_file_path} generated")


if __name__ == "__main__":
    main()

