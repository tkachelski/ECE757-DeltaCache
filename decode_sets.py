#!/usr/bin/env python3

# L3 parameters
BLOCK_SIZE = 64
NUM_SETS = 2048

input_file = "llc_dump.txt"
output_file = "llc_dump_sets.txt"

def parse_block_address(s):
    """
    Your dump prints addresses like:
        0
        40000
        c0000
    These are hex-like without '0x'.
    """
    return int(s, 16)

with open(input_file, "r") as fin, open(output_file, "w") as fout:
    fout.write("set_index data_hex\n")

    for line in fin:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 2:
            continue

        block_addr_str, data_hex = parts

        # Convert block address to integer
        block_addr = parse_block_address(block_addr_str)

        # Compute set index
        set_index = block_addr % NUM_SETS

        # Write minimal output
        fout.write(f"{set_index} {data_hex}\n")

print("Decoded LLC dump written to llc_dump_sets.txt")
