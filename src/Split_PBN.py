import sys
import endplay.parsers.pbn as pbn
import endplay.parsers.lin as lin
from endplay.types.board import Board
import endplay.config as config
import os
import io
import re
import tkinter as tk
from tkinter import filedialog, ttk
from collections import Counter
from colorama import Fore, Back, Style, init
import threading
import pickle

# Define a function to convert room values to numeric values for sorting


def room_to_numeric(room):
    if room == "Open":
        return 0
    elif room == "Closed":
        return 1
    else:
        return 2  # Handle other cases as needed


def modify_event_string(original_string):
    if original_string == '[Event ""]':
        return original_string
    match = re.match(r'\[Event\s"([^"]+)"\]', original_string)
    if match:
        return original_string  # Return if the name is already in quotes

    # If not in quotes, find the event name and add quotes around it
    parts = re.split(r'\[Event\s', original_string)
    if len(parts) > 1:
        event_name = parts[1][:-1]  # Remove the trailing "]"
        modified_string = f'[Event "{event_name}"]'
        return modified_string
    else:
        return original_string  # Return original if no match found


def update_event_and_feasability(file_path):
    # Read the contents of the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("[Event "):
            lines[i] = modify_event_string(line.strip())

    # Filter out lines starting with '{Feasability:'
    new_lines = [line for line in lines if not line.startswith('{Feasability:')]

    # Filter out lines starting with '{Feasability:'
    lines = [line for line in new_lines if not line.startswith('{PAR of')]

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file

def update_event_and_feasability(file_path):
    # Read the contents of the file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Create an in-memory file-like object
    fake_file = io.StringIO(''.join(lines))

    return fake_file

def getScore(str):
    if str == None:
        return 0
    print(str)
    if "NS" in str:
        return int(str.split(" ")[1])
    
    elif "EW" in str:
        return -int(str.split(" ")[1])
    return 0

def load_optimumscores(pickle_path):
    with open(pickle_path, 'rb') as pkl_file:
        return pickle.load(pkl_file)

def lookup(data, deal_line):
    value = data.get(deal_line, None)
    if value == None:
        return None, None, None
    score, par_contract, vulnerable = value
    optimum_score = score.split("\"")[1]
    return optimum_score, par_contract, vulnerable


def process_file(file_path, info_label,progress_window, progress_bar):

    pickle_path = 'DatumScores.pkl'
    data = load_optimumscores(pickle_path)

    # Once done, update the label to show completion message
    info_label.config(text="Removing bad text in files")
    fakefile = update_event_and_feasability(file_path)

    info_label.config(text="Loading PBN file")
    try:
        boards = pbn.load(fakefile)
    except pbn.PBNDecodeError as e:
        print("OK: There was an issue decoding the PBN file.")
        print("Error message:", e)
        print("Current line:", e.line)
        print("Line number:", e.lineno)
        sys.exit(1)

    # Once done, update the label to show completion message
    info_label.config(text="Validating boards")

    # Simulate file processing with a loop
    file_size = len(boards)  # Example file size, you can set this dynamically based on the actual file
    progress_bar["maximum"] = file_size  # Set the maximum value for the progress bar

    # Don't use unicode
    db_making = []
    db_not_making = []
    disaster = []
    ok_boards = []
    duplicates = []
    missing = []
    # Count the occurrences of each line
    deal_count = Counter()

    print(f"{Fore.GREEN}Loaded {len(boards)} boards{Fore.RESET}")

    config.use_unicode = False
    for i in range(len(boards)):
        if (i+1) % 10000 == 0:
            print("Processed",i+1)
        if deal_count[boards[i].deal.to_pbn()] > 1:
            #print(Fore.GREEN,end="")
            print(f"Duplicate deal {boards[i].board_num}: {boards[i].deal.to_pbn()} {deal_count[boards[i].deal.to_pbn()]}")
            duplicates.append(boards[i])
            continue
        print("Adding:",boards[i].deal.to_pbn())
        deal_count[boards[i].deal.to_pbn()] += 1

        skip = False
        if boards[i].info.OptimumScore is None:
            deal_line = f'[Deal "{boards[i].deal.to_pbn()}"]'  # Replace with an actual deal line
            optimumScore,_,_ = lookup(data, deal_line)
            if optimumScore is None:
                print(f"{Fore.RED}{i+1} No optimum score for board {boards[i].board_num}{Fore.RESET}", deal_line)
                missing.append(boards[i])
                continue
            else:
                boards[i].info.OptimumScore = optimumScore
                #print(f"{Fore.RED}{i+1} Optimum score for board {boards[i].board_num} found in archive:  {optimumScore} {Fore.RESET}")
        else:   
            #print(f"{Fore.RED}{i} Optimum score for board  {boards[i].board_num}: {boards[i].info.OptimumScore}{Fore.RESET}")
            optimumScore = boards[i].info.OptimumScore
            

        if boards[i].contract.penalty > 1:
            if boards[i].contract.result >= 0:
                #print(Fore.YELLOW,end="")
                #print(boards[i].board_num, boards[i].contract,  boards[i].info.Score, boards[i].info.OptimumScore)
                db_making.append(boards[i])
                continue
            else:
                #print(Fore.BLUE,end="")
                #print("Contract with penalty", boards[i].contract, "in file", boards[i].board_num)
                db_not_making.append(boards[i])

        NS_Score = getScore(boards[i].info.Score)
        PAR_Score = getScore(optimumScore)
        if abs(NS_Score - PAR_Score) > 2000:
            print(boards[i].board_num, boards[i].contract,  boards[i].info.Score, boards[i].info.OptimumScore, NS_Score, PAR_Score, optimumScore)
            disaster.append(boards[i])
            continue

        ok_boards.append(boards[i])
        # Update the progress bar
        progress_bar["value"] = i
    

    # Once done, update the label to show completion message
    info_label.config(text="Writing results")

    if len(ok_boards) > 0:
        with open(f"{file_path}-OK_boards.pbn", 'w') as output_file:
            pbn.dump(ok_boards, output_file)
            print(f"OK_boards.pbn with {len(ok_boards)} deals generated")

    if len(disaster) > 0:
        with open(f"{file_path}-disaster.pbn", 'w') as output_file:
            pbn.dump(disaster, output_file)
            print(f"{file_path}-disaster.pbn with {len(disaster)} deals generated")

    if len(db_making) > 0:
        with open(f"{file_path}-db_making.pbn", 'w') as output_file:
            pbn.dump(db_making, output_file)
            print(f"{file_path}-db_making.pbn with {len(db_making)} deals generated")

    if len(db_not_making) > 0:
        with open(f"{file_path}-db_not_making.pbn", 'w') as output_file:
            pbn.dump(db_not_making, output_file)
            print(f"{file_path}-db_not_making.pbn with {len(db_not_making)} deals generated")

    if len(duplicates) > 0:
        with open(f"{file_path}-duplicates.pbn", 'w') as output_file:
            pbn.dump(duplicates, output_file)
            print(f"{file_path}-duplicates.pbn with {len(duplicates)} deals generated")

    if len(missing) > 0:
        with open(f"{file_path}-missing-DD.pbn", 'w') as output_file:
            pbn.dump(missing, output_file)
            print(f"{file_path}-missing-DD.pbn with {len(missing)} deals generated")

    # Once done, update the label to show completion message
    info_label.config(text="Files generated")

def check_thread_status(thread, root):
    if thread.is_alive():
        # Check again after 100 ms if the thread is still running
        root.after(100, check_thread_status, thread, root)
    else:
        # When the thread is done, exit the application
        root.quit()

def main():

    print("Split PBN in 6 files. Doubled and making, doubled not making more than 2000 from par, duplicates, missing DD and the rest, Version 1.0.16")
    # create a root window
    root = tk.Tk()
    root.withdraw()

    # specify the allowed file types
    file_types = [
        ("PBN files", "*.pbn"),  # Example: Only allow .txt files
        ("All files", "*.*")     # Allow all files (in case the user wants to choose other formats)
    ]
    # open the file dialog box
    file_path = filedialog.askopenfilename(initialdir=".", filetypes=file_types)

    # print the selected file path
    if not file_path:
        sys.exit(1)

    # Show the progress bar window
    progress_window = tk.Toplevel(root)
    progress_window.title("Processing File")

    # Add a progress bar
    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=20)
    
    # Add a label to display information
    info_label = tk.Label(progress_window, text="Reading file ...")
    info_label.pack(pady=10)
    # Start processing boards in a new thread to prevent blocking the UI
    thread = threading.Thread(target=process_file, args=(file_path, info_label, root, progress_bar))
    thread.start()

    # Periodically check if the thread is done
    root.after(100, check_thread_status, thread, root)

    # Start the Tkinter main loop
    root.mainloop()

    # After root.mainloop() exits, close the application
    root.destroy()

if __name__ == "__main__":
    main()
