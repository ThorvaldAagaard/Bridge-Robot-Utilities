import os
import re
import sys
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox
import lastdir
import dealkey

TAG = re.compile(r'^\s*\[(\w+)\s+"([^"]*)"\]')

# How many boards to list per kind in the message box; the console gets them all
SHOW_IN_DIALOG = 10


def board_blocks(text):
    """The boards of a PBN text, as lists of lines (boards are separated by blank lines)."""
    block = []
    for line in text.splitlines():
        if line.strip() == '':
            if block:
                yield block
            block = []
        else:
            block.append(line)
    if block:
        yield block


class DuplicateFinder:
    """Finds boards that were already seen, in the same file or an earlier one."""

    def __init__(self):
        # rotation key -> (where, hands N/E/S/W, dealer, vulnerability) of the first board seen
        self.seen = {}
        self.duplicates = []
        self.rotated = []
        self.rotated_other = []

    def add_file(self, text, name):
        previous = {}  # a "#" tag value repeats the value from the previous board
        for block in board_blocks(text):
            tags = {}
            for line in block:
                m = TAG.match(line)
                if m:
                    value = previous.get(m.group(1), '') if m.group(2) == '#' else m.group(2)
                    tags[m.group(1)] = previous[m.group(1)] = value
            if 'Deal' not in tags:
                continue
            try:
                hands = dealkey.hands_from_north(tags['Deal'])
            except (ValueError, IndexError):
                continue
            where = f"board {tags.get('Board', '?')} in {name}"
            dealer, vul = tags.get('Dealer'), tags.get('Vulnerable')
            key = dealkey.rotation_key(hands)
            first = self.seen.get(key)
            if first is None:
                self.seen[key] = (where, hands, dealer, vul)
            elif first[1] == hands:
                self.duplicates.append((where, first[0]))
            elif dealkey.same_board(first[1], first[2], first[3], hands, dealer, vul):
                self.rotated.append((where, first[0]))
            else:
                self.rotated_other.append((where, first[0]))

    def kinds(self):
        return [("duplicate deals", self.duplicates),
                ("rotated boards (hands, dealer and vulnerability all turned)", self.rotated),
                ("rotated deals with a different dealer or vulnerability", self.rotated_other)]


def process_file(files, merged_file, directory_path, output_path, finder, base_path):
    for filename in files:
        if filename.lower().endswith('.pbn'):
            file_path = os.path.join(directory_path, filename)
            # Never merge the output file into itself
            if os.path.normcase(os.path.abspath(file_path)) == output_path:
                continue
            print(f"Merging file: {file_path}")
            with open(file_path, 'r') as pbn_file:
                content = pbn_file.read()
            merged_file.write(content)
            merged_file.write('\n')  # Add a newline between merged files
            finder.add_file(content, os.path.relpath(file_path, base_path))

def merge_pbn_files(directory_path, output_file, recursive=False):
    output_path = os.path.normcase(os.path.abspath(output_file))
    finder = DuplicateFinder()
    with open(output_file, 'w') as merged_file:
        if recursive:
            print(f"Scanning directory: {directory_path} recursively")
            for root, dirs, files in os.walk(directory_path):
                process_file(files, merged_file, root, output_path, finder, directory_path)
        else:
            print(f"Scanning directory: {directory_path}")
            # Use os.listdir() to get files in the current directory only
            current_directory_files = os.listdir(directory_path)
            process_file(current_directory_files, merged_file, directory_path, output_path, finder, directory_path)

    print(f"Merging complete! Merged files saved as: {output_file}")
    return finder

def report_duplicates(finder):
    """Print every duplicate found, and return a shorter summary for a dialog."""
    summary = []
    for title, found in finder.kinds():
        print(f"{len(found)} {title}")
        summary.append(f"{len(found)} {title}")
        for i, (where, first) in enumerate(found):
            print(f"  {where} = {first}")
            if i < SHOW_IN_DIALOG:
                summary.append(f"  {where} = {first}")
            elif i == SHOW_IN_DIALOG:
                summary.append(f"  ... and {len(found) - SHOW_IN_DIALOG} more")
    return "\n".join(summary)

def ask_arguments():
    directory = filedialog.askdirectory(initialdir=lastdir.get_last_dir(), title="Select folder with PBN files")
    if not directory:
        sys.exit(1)
    lastdir.set_last_dir(directory)

    recursive = messagebox.askyesno("Merge PBN Files", "Include PBN files in subfolders?")

    file_types = [
        ("PBN files", "*.pbn"),
        ("All files", "*.*")
    ]
    output_file = filedialog.asksaveasfilename(defaultextension=".pbn", initialdir=directory, filetypes=file_types,
                                               initialfile="All.PBN", title="Save merged PBN file as")
    if not output_file:
        print("File not saved")
        sys.exit(1)

    return directory, output_file, recursive

def main():
    print("Merge PBN Files, Version 1.0.23")
    parser = argparse.ArgumentParser(description="Merge .PBN files in a directory into a single file, reporting duplicate "
                                                 "and rotated boards. Without --directory, dialogs ask for the folder and output file.")
    parser.add_argument("-d", "--directory", help="Path to the directory containing .PBN files.")
    parser.add_argument("-o", "--output", default="All.PBN", help="Name of the output file.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively search for .PBN files.")
    args = parser.parse_args()

    if args.directory:
        report_duplicates(merge_pbn_files(args.directory, args.output, args.recursive))
    else:
        # create a root window
        root = tk.Tk()
        root.withdraw()
        directory, output_file, recursive = ask_arguments()
        summary = report_duplicates(merge_pbn_files(directory, output_file, recursive))
        messagebox.showinfo("Merge PBN Files", f"Merged into {output_file}\n\n{summary}")
        root.destroy()

if __name__ == "__main__":
    main()
