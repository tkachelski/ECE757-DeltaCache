#!/usr/bin/env python3
"""
Analyze DeltaCache compression statistics from a gem5 output file.

Extracts ECE757 INC/DEC Counts events, reconstructs the pair/l3_valid time
series, computes compression metrics, and saves a four-panel plot.

Usage:
    python3 analyze_delta_compression.py [output.txt] [plot.png]

Defaults:
    input  -> output.txt
    output -> delta_cache_compression.png
"""

import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_COUNT_RE = re.compile(r"ECE757 (INC|DEC) Counts: pairs=(\d+) l3_valid=(\d+)")
_TICK_RE  = re.compile(r"^(\d+): ")


def parse_events(filepath):
    """Return list of dicts: {tick, type, pairs, l3_valid}."""
    events = []
    current_tick = 0

    with open(filepath, "r") as fh:
        for line in fh:
            tick_m = _TICK_RE.match(line)
            if tick_m:
                current_tick = int(tick_m.group(1))

            count_m = _COUNT_RE.search(line)
            if count_m:
                events.append({
                    "tick":    current_tick,
                    "type":    count_m.group(1),
                    "pairs":   int(count_m.group(2)),
                    "l3_valid": int(count_m.group(3)),
                })

    return events


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

BLOCK_BYTES = 64   # full cache line
DELTA_BYTES = 32   # calculateCompressedSize placeholder = block_size / 2


def compute_metrics(events):
    ticks    = np.array([e["tick"]    for e in events], dtype=np.int64)
    pairs    = np.array([e["pairs"]   for e in events], dtype=np.float64)
    l3valid  = np.array([e["l3_valid"] for e in events], dtype=np.float64)

    # Fraction of L3 lines participating in a delta pair (both halves counted)
    with np.errstate(invalid="ignore", divide="ignore"):
        pair_frac = np.where(l3valid > 0, 2.0 * pairs / l3valid, 0.0)

    # Compression ratio: logical data bytes / physical storage bytes
    #   - paired lines:   1 raw line (BLOCK_BYTES) + 1 delta line (DELTA_BYTES)
    #   - unpaired lines: BLOCK_BYTES each
    physical = (l3valid - pairs) * BLOCK_BYTES + pairs * DELTA_BYTES
    logical  = l3valid * BLOCK_BYTES
    with np.errstate(invalid="ignore", divide="ignore"):
        comp_ratio = np.where(physical > 0, logical / physical, 1.0)

    # Absolute bytes saved by delta encoding
    bytes_saved = pairs * (BLOCK_BYTES - DELTA_BYTES)

    return ticks, pairs, l3valid, pair_frac, comp_ratio, bytes_saved


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _x_axis(ticks):
    """Return (x values, x-axis label, scale factor label for ticks)."""
    if ticks.max() > 0:
        scale = 1e6
        return ticks / scale, "Simulation Time (M ticks)"
    return np.arange(len(ticks)), "Event Index"


def plot_all(ticks, pairs, l3valid, pair_frac, comp_ratio, bytes_saved, outfile):
    x, xlabel = _x_axis(ticks)

    fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)
    fig.suptitle(
        "DeltaCache Compression Analysis",
        fontsize=16, fontweight="bold", y=0.995,
    )

    # Detect warmup boundary: first event where l3_valid reaches its maximum
    max_valid = l3valid.max()
    warmup_end_idx = int(np.argmax(l3valid >= max_valid))

    def _shade_warmup(ax):
        if warmup_end_idx > 0 and warmup_end_idx < len(x) - 1:
            ax.axvspan(x[0], x[warmup_end_idx],
                       alpha=0.07, color="gray", label="warmup")

    # --- Panel 1: Active pair count ---
    ax = axes[0]
    ax.plot(x, pairs, color="tab:blue", linewidth=0.9, label="pairs")
    ax.fill_between(x, pairs, alpha=0.15, color="tab:blue")
    _shade_warmup(ax)
    ax.set_ylabel("Active Delta Pairs")
    ax.set_title("Active Delta Pair Count")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    # --- Panel 2: L3 valid line count ---
    ax = axes[1]
    ax.plot(x, l3valid, color="tab:green", linewidth=0.9, label="l3_valid")
    ax.fill_between(x, l3valid, alpha=0.15, color="tab:green")
    _shade_warmup(ax)
    ax.axhline(max_valid, color="gray", linestyle="--",
               linewidth=0.8, label=f"capacity ({int(max_valid)})")
    ax.set_ylabel("Valid Lines")
    ax.set_title("L3 Valid Line Count")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    # --- Panel 3: Compressed fraction of cache ---
    ax = axes[2]
    pct = pair_frac * 100.0
    ax.plot(x, pct, color="tab:orange", linewidth=0.9, label="compressed %")
    ax.fill_between(x, pct, alpha=0.15, color="tab:orange")
    _shade_warmup(ax)
    ax.set_ylabel("Lines in Pairs (%)")
    ax.set_title(
        "Fraction of L3 Lines Delta-Compressed  "
        r"$\left(\frac{2 \times \mathrm{pairs}}{l3\_valid}\right)$"
    )
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f%%"))
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)

    # --- Panel 4: Compression ratio ---
    ax = axes[3]
    ax.plot(x, comp_ratio, color="tab:red", linewidth=0.9, label="compression ratio")
    ax.fill_between(x, 1.0, comp_ratio, alpha=0.15, color="tab:red")
    _shade_warmup(ax)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, label="1.0x (no gain)")
    ax.set_ylabel("Ratio")
    ax.set_title(
        f"Compression Ratio  "
        r"$\left(\frac{N \times 64B}{(N-P)\times 64B + P\times 32B}\right)$"
        f"  [delta = {DELTA_BYTES}B placeholder]"
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel(xlabel)

    plt.tight_layout(rect=[0, 0, 1, 0.995])
    plt.savefig(outfile, dpi=150, bbox_inches="tight")
    print(f"Saved plot → {outfile}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(events, pairs, l3valid, pair_frac, comp_ratio, bytes_saved):
    n_inc = sum(1 for e in events if e["type"] == "INC")
    n_dec = sum(1 for e in events if e["type"] == "DEC")

    print("\n=== DeltaCache Compression Summary ===")
    print(f"  Total events         : {len(events)}  ({n_inc} INC, {n_dec} DEC)")
    print(f"  Net pairs balance    : {n_inc - n_dec}  (final count = {int(pairs[-1])})")
    print(f"  Peak pair count      : {int(pairs.max())}")
    print(f"  Peak L3 valid lines  : {int(l3valid.max())}")
    print(f"  Peak compressed frac : {pair_frac.max()*100:.3f}% of L3 in pairs")
    print(f"  Peak comp ratio      : {comp_ratio.max():.5f}x")
    print(f"  Peak bytes saved     : {bytes_saved.max()/1024:.2f} KB  "
          f"(@ {DELTA_BYTES}B delta placeholder)")

    # Steady-state window: after l3_valid first hits max
    max_valid = l3valid.max()
    ss_start = int(np.argmax(l3valid >= max_valid))
    if ss_start < len(pairs) - 1:
        ss_pairs = pairs[ss_start:]
        ss_frac  = pair_frac[ss_start:]
        print(f"\n  --- Steady-state (after warmup, {len(ss_pairs)} events) ---")
        print(f"  Avg pairs            : {ss_pairs.mean():.2f}  "
              f"(max {int(ss_pairs.max())}, min {int(ss_pairs.min())})")
        print(f"  Avg compressed frac  : {ss_frac.mean()*100:.3f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    infile  = sys.argv[1] if len(sys.argv) > 1 else "output.txt"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "delta_cache_compression.png"

    print(f"Parsing {infile} ...")
    events = parse_events(infile)

    if not events:
        print("ERROR: no 'ECE757 INC/DEC Counts' lines found. "
              "Check that the simulation was run with the current DeltaMapTable.")
        sys.exit(1)

    print(f"Found {len(events)} count events.")
    ticks, pairs, l3valid, pair_frac, comp_ratio, bytes_saved = compute_metrics(events)
    print_summary(events, pairs, l3valid, pair_frac, comp_ratio, bytes_saved)
    plot_all(ticks, pairs, l3valid, pair_frac, comp_ratio, bytes_saved, outfile)


if __name__ == "__main__":
    main()
