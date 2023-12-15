import numpy as np
import datetime

import os
import os.path

#n = 500000
displaystep = 10000
n = 10485760  # Number of records

y = np.zeros((n * 20, 14), dtype=np.float16)  # Initializing the array for tricks
X = np.zeros((n * 20, 5 + 4*32), dtype=np.float16)

card_index_lookup_x = dict(
    zip(
        ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'],
        [0, 1, 2, 3, 4, 5, 6, 7, 7, 7, 7, 7, 7],
    )
)

player_ranges = [
    (5 + i * 32, 5 + (i + 1) * 32) for i in range(4)
]

def binary_hand(hand):
    suits = hand.split('.')
    x = np.zeros(32, np.float16)
    assert(len(suits) == 4)
    for suit_index in [0, 1, 2, 3]:
        for card in suits[suit_index]:
            card_index = card_index_lookup_x[card]
            x[suit_index * 8 + card_index] += 1
    assert(np.sum(x) == 13)
    return x

# Function to convert the deck array to the specified string format
def deck_to_string(deck_array):
    card_values = 'AKQJT98765432'
    players = ['West', 'North', 'East', 'South']
    translated_deck = {player: '' for player in players}

    for i in range(52):
        player_index = deck_array[i]
        player = players[player_index]
        card_value = card_values[i % 13]
        
        if i % 13 == 0 and i != 0:
           for p in players:
                translated_deck[p] += '.'

        translated_deck[player] += card_value

    return [translated_deck[player] for player in players]

# Define the size of each block in bits
block_size = 184

# Define the sizes of each part in the block
deck_size = 2 * 52  # 104 bits for deck (2 * 52)
tricks_size = 20 * 4  # 80 bits for the tricks (20 * 4)

# Function to read binary file in blocks of 184 bits
def read_blocks(file_name):
    with open(file_name, "rb") as file:
        record = 0
        print('{} records: {}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),n))
        while record < n:
            # Read 184 bits (23 bytes) at a time
            block = file.read(block_size // 8)
            if not block:
                break

            # Unpack the block according to the specified sizes
            deck_data = block[:deck_size // 8]
            tricks_data = block[deck_size // 8:][:tricks_size // 8]

            deck_array = []
            for byte in deck_data:
                for shift in range(0, 8, 2):  # 2-bit values (4 values in each byte)
                    value = (byte >> shift) & 0b11  # Extract 2 bits
                    deck_array.append(value)

            tricks_array = []
            for byte in tricks_data:
                for shift in range(0, 8, 4):  # 4-bit values (2 values in each byte)
                    value = (byte >> shift) & 0xF  # Extract 4 bits
                    tricks_array.append(value)

            # Check if elements are within the range of 0-3 and 0-13 respectively
            if all(0 <= elem <= 3 for elem in deck_array) and all(0 <= elem <= 13 for elem in tricks_array):
                #print("Deck Array:", deck_array)
                # Process the unpacked data
                translated_deck = deck_to_string(deck_array)
                #print(translated_deck)
                #print("Tricks Array:", tricks_array)
                for j, value in enumerate(tricks_array):
                    index = record * 20 + j
                    y[index, value] = 1.0  # One-hot encoding for each trick
                    # We do not have any lead
                    #X[i, lead_card_ix] = 1
                    # Strain is N S H D C
                    strain_ix = j // 4
                    # Declarer is West, North, East, South
                    declarer_ix = j % 4
                    #print(declarer_ix, strain_ix, translated_deck[declarer_ix], value)
                    X[index, strain_ix] = 10 if strain_ix == 0 else 1
                    
                    # lefty
                    X[index, (5 + 0*32):(5 + 1*32)] = binary_hand(translated_deck[(declarer_ix + 1) % 4])
                    # dummy
                    X[index, (5 + 1*32):(5 + 2*32)] = binary_hand(translated_deck[(declarer_ix + 2) % 4])
                    # righty
                    X[index, (5 + 2*32):(5 + 3*32)] = binary_hand(translated_deck[(declarer_ix + 3) % 4])
                    # declarer
                    X[index, (5 + 3*32):] = binary_hand(translated_deck[declarer_ix])
                    #print(translated_deck, value, strain_ix, declarer_ix)
                #print(y[0])
                #print(X[0])
                # print(y[1])
                # print(X[1])
            else:
                print("Invalid Deck or Tricks Array")
            record += 1
            if record % displaystep == 0:
                print('{} record={}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),record))

# Usage example
file_name = "rpdd.zrd"
read_blocks(file_name)

out_dir = "E:/"
np.save(os.path.join(out_dir, 'X.npy'), X)
np.save(os.path.join(out_dir, 'y.npy'), y)

