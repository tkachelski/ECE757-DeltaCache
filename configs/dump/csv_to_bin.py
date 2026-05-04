import argparse
import csv
import struct
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("output")
args = parser.parse_args()


def parse_time(s):
    s = s.strip()

    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return int(datetime.strptime(s, fmt).timestamp())
        except ValueError:
            pass

    raise ValueError(f"Bad datetime format: {s}")


with open(args.input) as f, open(args.output, "wb") as g:
    r = csv.DictReader(f)

    rows = list(r)
    rows.sort(key=lambda x: x["datetime"])

    skipped = 0

    for row in rows:
        try:
            timestamp = parse_time(row["datetime"])
            load = int(float(row["nat_demand"]) * 100)

            g.write(struct.pack("<qi", timestamp, load))

        except Exception:
            skipped += 1

print(f"Wrote {args.output}, skipped {skipped} rows")
