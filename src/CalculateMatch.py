import os
import io
import sys
import argparse
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
import endplay.config as config

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
    print("Calculate match from PBN, Version 1.0.16")

    parser = argparse.ArgumentParser(description="Calculate a match from 2 PBN files and create a single PBN file.")
    parser.add_argument("-o", "--open", default="open.PBN", help="Name of the open room file.")
    parser.add_argument("-c", "--closed", default="closed.PBN", help="Name of the closed room file.")
    parser.add_argument("-f", "--file", default="match.PBN", help="File name for the result")
    args = parser.parse_args()
    open_file_path = args.open
    closed_file_path = args.closed
    result_file_path = args.file

    fakefile_open = remove_feasability_lines(open_file_path)
    fakefile_closed = remove_feasability_lines(closed_file_path)

    try:
        boards_open = pbn.load(fakefile_open)
    except pbn.PBNDecodeError as e:
        print("OK: There was an issue decoding the PBN file.")
        print("Error message:", e)
        print("Current line:", e.line)
        print("Line number:", e.lineno)
        sys.exit(1)

    try:
        boards_closed = pbn.load(fakefile_closed)
    except pbn.PBNDecodeError as e:
        print("OK: There was an issue decoding the PBN file.")
        print("Error message:", e)
        print("Current line:", e.line)
        print("Line number:", e.lineno)
        sys.exit(1)

    for i, board in enumerate(boards_open):
        board.info.room = "Open"
        board.info.scoring = "IMP"
        if board.contract.declarer in (0, 2):
            board.info.score = f'NS {board.contract.score(board.vul)}'
        else:
            board.info.score = f'EW {board.contract.score(board.vul)}'
    for i, board in enumerate(boards_closed):
        board.info.room = "Closed"
        board.info.scoring = "IMP"
        if board.contract.declarer in (0, 2):
            board.info.score = f'NS {board.contract.score(board.vul)}'
        else:
            board.info.score = f'EW {board.contract.score(board.vul)}'

    boards = boards_open + boards_closed

    # Sort the array of Board objects based on board.number and board.info.room
    boards = sorted(
        boards,
        key=lambda board: (board.board_num, room_to_numeric(board.info.room))
    )

    #Don't use unicode
    config.use_unicode = False 

    with open(result_file_path, 'w') as output_file:
        pbn.dump(boards, output_file)

    print(f"{result_file_path} generated")

if __name__ == "__main__":
    main()
