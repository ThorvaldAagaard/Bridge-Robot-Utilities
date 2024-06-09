import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin

with open("test.pbn", 'r') as f:
    boards = pbn.load(f)

with open("test.lin", 'w') as output_file:
    lin.dump(boards, output_file)
    # Close the file after writing
    output_file.close()
