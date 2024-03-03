import sys
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
import endplay.config as config
import argparse
import io
import os
import math
import bisect
import tkinter as tk
from tkinter import filedialog


IMP = [10, 40, 80, 120, 160, 210, 260, 310, 360, 420, 490, 590, 740, 890, 1090, 1290, 
       1490, 1740, 1990, 2240, 2490, 3490, 3990]


def get_imps(score1, score2):
    score_diff = score1 - score2
    imp = bisect.bisect_left(IMP, int(math.fabs(score_diff)))
    if score_diff >= 0:
        return imp
    else:
        return -imp


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

def write_playernames_to_file(output_file, sorted_boards):
    output_file.write("pn|")
    output_file.write(f"{sorted_boards[0].info.south},")
    output_file.write(f"{sorted_boards[0].info.west},")
    output_file.write(f"{sorted_boards[0].info.north},")
    output_file.write(f"{sorted_boards[0].info.east},")
    output_file.write(f"{sorted_boards[1].info.south},")
    output_file.write(f"{sorted_boards[1].info.west},")
    output_file.write(f"{sorted_boards[1].info.north},")
    output_file.write(f"{sorted_boards[1].info.east}\n")
    output_file.write("|pg||\n")

def generate_vg(start, end, boards, filename, co_ns, co_ew):  
    # Use a list comprehension to extract the contract information from each board
    contract_info = [board.contract for board in boards]

    # Join the contract information into a single line
    contract_line = ','.join(str(contract) for contract in contract_info).replace('NT','N')

     # Construct the output file path with ".lin" extension
    output_file_path = filename + " " + str(start) + "-" + str(end) + ".lin"
    print("Creating: ",output_file_path)
    with open(output_file_path, 'w') as output_file:
        output_file.write(f"vg|{boards[0].info.event},'{start}-{end}',I,{start},{end},{boards[0].info.north},{co_ns},{boards[0].info.east},{co_ew}|\n")
        output_file.write(f"rs|{contract_line}|\n")
        write_playernames_to_file(output_file, boards)
        for index, board in enumerate(boards):
            linfile = lin.dumps([board])
            if index % 2 == 1:
                if boards[index-1].contract.declarer in (0,2):
                    ns_score_open = boards[index-1].contract.score(boards[index-1].vul)
                else:
                    ns_score_open = -boards[index-1].contract.score(boards[index-1].vul)
                if boards[index].contract.declarer in (0,2):
                    ns_score_closed = boards[index].contract.score(boards[index].vul)
                else:
                    ns_score_closed = -boards[index].contract.score(boards[index].vul)
                imp = get_imps(ns_score_open,ns_score_closed)
                #print(f"{boards[index-1].contract} - {ns_score_open} closed {boards[index].contract} - {ns_score_closed}= {imp}")
                if imp > 0:
                    co_ns += imp
                else: 
                    co_ew -= imp
            linfile = linfile.replace('\n', '')
            if board.info.room == "Closed":
                linfile = linfile.replace(f',|rh||ah|Board {board.board_num}','')
                linfile = linfile.replace('|mb|','\n|sa|0|mb|',1)
                linfile = linfile.replace('st|',f'qx|c{board.board_num},BOARD {board.board_num}|rh||ah|Board {board.board_num}')
            if board.info.room == "Open":
                linfile = linfile.replace(f',|rh||ah|Board {board.board_num}','')
                linfile = linfile.replace('|mb|','\n|sa|0|mb|',1)
                linfile = linfile.replace('st|',f'qx|o{board.board_num},BOARD {board.board_num}|rh||ah|Board {board.board_num}')
            linfile += 'pg||'
            linfile = linfile.replace('||','||\n') 
            linfile = linfile.replace('||\n','||',1) 
            output_file.write(linfile + "\n")
    
        write_playernames_to_file(output_file, boards)

    print(f"{output_file_path} generated")
    return co_ns, co_ew

def main():

    print("Table Manager PBN to Lin, Version 1.0.8")

    # create a root window
    root = tk.Tk()
    root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        # Allow all files (in case the user wants to choose other formats)
        ("All files", "*.*")
    ]
    # open the file dialog box
    file_path = filedialog.askopenfilename(
        initialdir=".", filetypes=file_types)

    # print the selected file path
    if not file_path:
        sys.exit(1)

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("--onefile",default=False, required = False, help="create only one file")

    # Parse the command-line arguments
    args = parser.parse_args()
    onefile = args.onefile

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

    # If two first boards have the same number we assume it is from Bridge Moniteur
    BM = boards[0].board_num == boards[1].board_num
    if (BM):
        # Loop through the array and set the alternating text attribute
        for i, board in enumerate(boards):
            if board.info.room == None:
                board.info.room = room[i % len(room)]
        # Perhaps we should renumber all boards - making it optional
        board.board_num = 1 + (i // 2)

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

    filename = os.path.splitext(file_path)[0]
    co_ns = 0
    co_ew = 0
    chunk_size = 64
    if onefile:
        chunk_size = 10000
    for i in range(0, len(boards), chunk_size):
        start_idx = i // 2 + 1
        chunk = boards[i:i + chunk_size]
        last_idx = min(i + chunk_size - 1, len(boards) - 1) // 2 +1
        co_ns, co_ew = generate_vg(start_idx, last_idx, chunk, filename, co_ns, co_ew)


if __name__ == "__main__":
    main()

