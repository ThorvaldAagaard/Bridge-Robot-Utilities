import os
import argparse

def merge_pbn_files(directory_path, output_file, recursive=False):
    with open(output_file, 'w') as merged_file:
        for root, dirs, files in os.walk(directory_path):
            print(f"Scanning directory: {root}")
            for filename in files:
                if filename.lower().endswith('.pbn'):
                    file_path = os.path.join(root, filename)
                    print(f"Merging file: {file_path}")
                    with open(file_path, 'r') as pbn_file:
                        merged_file.write(pbn_file.read())
                    merged_file.write('\n')  # Add a newline between merged files

    print(f"Merging complete! Merged files saved as: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Merge .PBN files in a directory into a single file.")
    parser.add_argument("-d", "--directory", required=True, help="Path to the directory containing .PBN files.")
    parser.add_argument("-o", "--output", default="All.PBN", help="Name of the output file.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively search for .PBN files.")
    args = parser.parse_args()

    merge_pbn_files(args.directory, args.output, args.recursive)

if __name__ == "__main__":
    main()
