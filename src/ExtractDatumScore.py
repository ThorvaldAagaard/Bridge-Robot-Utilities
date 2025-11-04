import sys
import os
import pickle
import tkinter as tk
from tkinter import filedialog

def extract_data(file_path, output_path):
    # Load existing data if the output file exists
    if os.path.exists(output_path):
        with open(output_path, 'rb') as pkl_file:
            existing_data = pickle.load(pkl_file)
    else:
        existing_data = {}

    # Extract new data
    new_data = {}
    current_object = []

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or line.startswith('%'):
                continue
            if line == '':
                # Process the current object
                deal_line = next((l for l in current_object if l.startswith("[Deal ")), None)
                optimum_score = next((l for l in current_object if l.startswith("[OptimumScore")), None)
                par_contract = next((l for l in current_object if l.startswith("[ParContract")), None)
                vulnerable = next((l for l in current_object if l.startswith("[Vulnerable ")), None)
                v = [False, False]
                if vulnerable == "All":
                    v = [True,True]
                if vulnerable == "NS":
                    if "N" in par_contract or "S" in par_contract:
                        v = [True,False]
                    else:
                        v = [False, True]
                if vulnerable == "EW":
                    if "E" in par_contract or "W" in par_contract:
                        v = [True, False]
                    else:
                        v = [False, True]

                if deal_line and optimum_score and par_contract:
                    key = deal_line
                    value = (optimum_score, par_contract, v)
                    new_data[key] = value
                
                # Reset for the next object
                current_object = []
            else:
                current_object.append(line)
        
        # Handle the last object if not followed by a blank line
        if current_object:
            deal_line = next((l for l in current_object if l.startswith("[Deal ")), None)
            optimum_score = next((l for l in current_object if l.startswith("[OptimumScore ")), None)
            par_contract = next((l for l in current_object if l.startswith("[ParContract ")), None)
            vulnerable = next((l for l in current_object if l.startswith("[Vulnerable ")), None)
            v = [False, False]
            if vulnerable == "All":
                v = [True,True]
            if vulnerable == "NS":
                if "N" in par_contract or "S" in par_contract:
                    v = [True,False]
                else:
                    v = [False, True]
            if vulnerable == "EW":
                if "E" in par_contract or "W" in par_contract:
                    v = [True, False]
                else:
                    v = [False, True]
            if deal_line and optimum_score and par_contract:
                key = deal_line
                value = (optimum_score, par_contract, v)
                new_data[key] = value

    # Update existing data with new data
    existing_data.update(new_data)

    # Save the updated data back to the file
    with open(output_path, 'wb') as pkl_file:
        pickle.dump(existing_data, pkl_file)
    
    print(f"Updated data saved to {output_path}")


def main():

    print("Extract Datum Score, Version 1.0.16")
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

    # Example usage
    extract_data(file_path, 'DatumScores.pkl')



if __name__ == "__main__":
    main()

