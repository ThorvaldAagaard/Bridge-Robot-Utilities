import argparse
import os
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin

# Set up argument parsing
parser = argparse.ArgumentParser(description="Convert PBN file to LIN format. Version 1.0.18")
parser.add_argument('input_file', help="The input PBN file.")
parser.add_argument('output_file', nargs='?', help="The output LIN file (optional).")

# Parse the arguments
args = parser.parse_args()

# If no output file is specified, generate the output file name by changing the extension
if not args.output_file:
    base, _ = os.path.splitext(args.input_file)
    args.output_file = base + '.lin'

# Open the input PBN file and process it
with open(args.input_file, 'r') as f:
    boards = pbn.load(f)

# Open the output LIN file and write the data
with open(args.output_file, 'w') as output_file:
    lin.dump(boards, output_file)

print(f"Converted {args.input_file} to {args.output_file}")