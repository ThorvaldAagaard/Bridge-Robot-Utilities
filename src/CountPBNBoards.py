# Count number of borad in a PBN-file
import sys
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
import endplay.config as config
import argparse
import io
import os
import math
import bisect

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

    print("PBN Board Counter, Version 1.0.12")
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="Example program with command-line arguments")

    # Add a positional argument for the name
    parser.add_argument("filename", help="filename for conversion")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the function to remove lines and save the file
    fakefile = remove_feasability_lines(args.filename)

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
    #for i, board in enumerate(boards):
    #    print(i+1,board.board_num)

main()
