import os
import argparse

def process_file(files, merged_file, directory_path):
    for filename in files:
        if filename.lower().endswith('.pbn'):
            print(filename, directory_path)
            file_path = os.path.join(directory_path, filename)
            print(f"Merging file: {filename}")
            with open(file_path, 'r') as pbn_file:
                merged_file.write(pbn_file.read())
            merged_file.write('\n')  # Add a newline between merged files

def merge_pbn_files(directory_path, output_file, recursive=False):
    with open(output_file, 'w') as merged_file:
        if recursive:
            print(f"Scanning directory: {directory_path} recursively")
            for root, dirs, files in os.walk(directory_path):
                process_file(files, merged_file, root)
        else:
            print(f"Scanning directory: {directory_path}")
            # Use os.listdir() to get files in the current directory only
            current_directory_files = os.listdir(directory_path)
            process_file(current_directory_files, merged_file, directory_path)

    print(f"Merging complete! Merged files saved as: {output_file}")

def main():
    print("Merge PBN Files, Version 1.0.14")
    parser = argparse.ArgumentParser(description="Merge .PBN files in a directory into a single file.")
    parser.add_argument("-d", "--directory", required=True, help="Path to the directory containing .PBN files.")
    parser.add_argument("-o", "--output", default="All.PBN", help="Name of the output file.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively search for .PBN files.")
    args = parser.parse_args()

    merge_pbn_files(args.directory, args.output, args.recursive)

if __name__ == "__main__":
    main()
