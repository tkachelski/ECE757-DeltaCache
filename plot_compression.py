"""
Compression comparison: Plain BDI vs XOR+BDI vs Delta+BDI
Schemes: Random Bank, Ideal Set, Ideal Bank
"""

import os, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

STATS_DIR = os.path.expanduser("~/ECE757-DeltaCache/stats")
OUT_PNG   = os.path.expanduser("~/ECE757-DeltaCache/compression_comparison.png")
OUT_PDF   = os.path.expanduser("~/ECE757-DeltaCache/compression_comparison.pdf")

# ── workload display names ────────────────────────────────────────────────────
NAMES = {
    "bt.S.x.txt":                       "BT",
    "gabps_bc.txt":                     "BC",
    "gabps_bfs.txt":                    "BFS",
    "gabps_cc.txt":                     "CC",
    "gabps_cc_sv.txt":                  "CC-SV",
    "gabps_converter.txt":              "Conv",
    "gabps_pr.txt":                     "PR",
    "gabps_pr_spmv.txt":                "PR-SpMV",
    "gabps_pr_sssp.txt":                "SSSP",
    "gabps_pr_tc.txt":                  "TC",
    "is.S.x.txt":                       "IS",
    "lu.S.x.txt":                       "LU",
    "wrf-s.1_globalr1.sim.elfie.txt":   "WRF-R1",
    "wrf-s.1_globalr7.sim.elfie.txt":   "WRF-R7",
    "wrf-s.1_globalr17.sim.elfie.txt":  "WRF-R17",
    "x86-matrix-multiply-20220826.txt": "MatMul",
}

KEYS = ['plain_bdi',
        'is_xor',  'is_delta',
        'ib_xor',  'ib_delta',
        'rand_xor','rand_delta']

def parse(path):
    vals = []
    with open(path) as f:
        for line in f:
            m = re.search(r'Final size ratio.*?:\s*([\d.]+)', line)
            if m:
                vals.append(float(m.group(1)))
    if len(vals) != 7:
        return None
    return dict(zip(KEYS, vals))

# ── load ──────────────────────────────────────────────────────────────────────
raw = {}
for fname, short in NAMES.items():
    p = os.path.join(STATS_DIR, fname)
    if os.path.exists(p):
        d = parse(p)
        if d:
            raw[short] = d

# Fixed ordering: MatMul | NPB (BT, IS, LU) | GAP (BC,BFS,CC,CC-SV,Conv,PR,PR-SpMV,SSSP,TC) | WRF
WORKLOAD_ORDER = [
    "MatMul",
    "BT", "IS", "LU",
    "BC", "BFS", "CC", "CC-SV", "Conv", "PR", "PR-SpMV", "SSSP", "TC",
    "WRF-R1", "WRF-R7", "WRF-R17",
]
workloads = [w for w in WORKLOAD_ORDER if w in raw]

# Group boundaries and labels for annotation
GROUPS = [
    ("MatMul", [0],          "MatMul"),
    ("NPB",    [1, 2, 3],    "NPB"),
    ("GAP",    list(range(4, 13)), "GAP"),
    ("WRF",    [13, 14, 15], "WRF"),
]

n  = len(workloads)
xi = np.arange(n)

# ── colour palette ────────────────────────────────────────────────────────────
C_BDI       = '#888888'   # plain BDI  – neutral grey
C_XOR       = '#4C72B0'   # XOR+BDI   – steel blue
C_DELTA     = '#DD4444'   # Delta+BDI – vivid red (easy to distinguish)

BAR_W   = 0.22
GAP     = 0.04          # gap between the three bars in a group
OFFSETS = np.array([-BAR_W - GAP/2, 0, BAR_W + GAP/2])

SCHEME_KEYS = {
    'Random Bank' : ('rand_xor', 'rand_delta'),
    'Ideal Set'   : ('is_xor',   'is_delta'),
    'Ideal Bank'  : ('ib_xor',   'ib_delta'),
}

# ── figure setup ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor('white')

gs = GridSpec(4, 1, figure=fig,
              hspace=0.55,
              top=0.93, bottom=0.07,
              left=0.06, right=0.98)

ax_rand = fig.add_subplot(gs[0])
ax_iset = fig.add_subplot(gs[1])
ax_ibnk = fig.add_subplot(gs[2])
ax_gain = fig.add_subplot(gs[3])

scheme_axes = [
    ('Random Bank',  ax_rand),
    ('Ideal Set',    ax_iset),
    ('Ideal Bank',   ax_ibnk),
]

# ── helper: draw group separators + top labels on an axes ────────────────────
GROUP_COLORS = {
    "MatMul": "#F5F5F5",
    "NPB":    "#EEF4FB",
    "GAP":    "#F0FBF0",
    "WRF":    "#FFF5EE",
}

def draw_groups(ax, ylim_top, label_y_frac=0.97):
    for gname, idxs, glabel in GROUPS:
        if not idxs or max(idxs) >= n:
            continue
        lo = min(idxs) - 0.5
        hi = max(idxs) + 0.5
        ax.axvspan(lo, hi, color=GROUP_COLORS[gname], alpha=0.55, zorder=0)
        mid = (lo + hi) / 2
        ax.text(mid, ylim_top * label_y_frac, glabel,
                ha='center', va='top', fontsize=8,
                color='#444444', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.2', fc='white',
                          ec='#cccccc', alpha=0.7))
        # vertical separator line
        if min(idxs) > 0:
            ax.axvline(lo, color='#bbbbbb', linewidth=0.8,
                       linestyle='--', zorder=1)

# ── draw comparison panels ────────────────────────────────────────────────────
for title, ax in scheme_axes:
    xor_k, dlt_k = SCHEME_KEYS[title]

    bdi_v  = np.array([raw[w]['plain_bdi'] for w in workloads])
    xor_v  = np.array([raw[w][xor_k]      for w in workloads])
    dlt_v  = np.array([raw[w][dlt_k]      for w in workloads])

    b1 = ax.bar(xi + OFFSETS[0], bdi_v, BAR_W,
                color=C_BDI,   label='Plain BDI',   zorder=3, edgecolor='white', linewidth=0.4)
    b2 = ax.bar(xi + OFFSETS[1], xor_v, BAR_W,
                color=C_XOR,   label='XOR+BDI',     zorder=3, edgecolor='white', linewidth=0.4)
    b3 = ax.bar(xi + OFFSETS[2], dlt_v, BAR_W,
                color=C_DELTA, label='Delta+BDI',   zorder=3, edgecolor='white', linewidth=0.4)

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, 1.09)
    draw_groups(ax, ylim_top=1.09)

    ax.set_xticks(xi)
    ax.set_xticklabels(workloads, fontsize=8.5, rotation=30, ha='right')
    ax.set_ylabel('Size ratio\n(↓ better)', fontsize=9)
    ax.set_title(f'{title}: Plain BDI  vs  XOR+BDI  vs  Delta+BDI',
                 fontsize=10, fontweight='bold', pad=4)
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(fontsize=8, loc='upper left', ncol=3,
              framealpha=0.85, edgecolor='#cccccc')

    # Annotate delta-gain % above the Delta bar when gain > 1 %
    for i, w in enumerate(workloads):
        gain = (xor_v[i] - dlt_v[i]) / xor_v[i] * 100
        if gain > 1.0:
            ax.text(i + OFFSETS[2], dlt_v[i] + 0.015,
                    f'{gain:.1f}%', ha='center', va='bottom',
                    fontsize=6.5, color='#AA0000', fontweight='bold')

# ── delta-gain panel ──────────────────────────────────────────────────────────
C_RAND = '#2CA02C'   # green
C_ISET = '#FF7F0E'   # orange
C_IBNK = '#9467BD'   # purple

GAIN_W   = 0.22
GAIN_OFF = np.array([-GAIN_W - GAP/2, 0, GAIN_W + GAP/2])

for i, w in enumerate(workloads):
    d = raw[w]
    g_rand = (d['rand_xor'] - d['rand_delta']) / d['rand_xor'] * 100
    g_iset = (d['is_xor']   - d['is_delta']  ) / d['is_xor']   * 100
    g_ibnk = (d['ib_xor']   - d['ib_delta']  ) / d['ib_xor']   * 100

    ax_gain.bar(i + GAIN_OFF[0], g_rand, GAIN_W, color=C_RAND, zorder=3,
                edgecolor='white', linewidth=0.4)
    ax_gain.bar(i + GAIN_OFF[1], g_iset, GAIN_W, color=C_ISET, zorder=3,
                edgecolor='white', linewidth=0.4)
    ax_gain.bar(i + GAIN_OFF[2], g_ibnk, GAIN_W, color=C_IBNK, zorder=3,
                edgecolor='white', linewidth=0.4)

ax_gain.axhline(0, color='black', linewidth=0.8, zorder=4)
ax_gain.set_xlim(-0.5, n - 0.5)

# auto-scale y then draw groups
ax_gain.set_xticks(xi)
ax_gain.set_xticklabels(workloads, fontsize=8.5, rotation=30, ha='right')
ax_gain.set_ylabel('Delta gain over XOR\n(%, ↑ better)', fontsize=9)
ax_gain.set_title('Delta+BDI improvement over XOR+BDI  (positive = Delta wins)',
                  fontsize=10, fontweight='bold', pad=4)
ax_gain.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.6, zorder=0)
ax_gain.set_axisbelow(True)
ax_gain.spines['top'].set_visible(False)
ax_gain.spines['right'].set_visible(False)

# compute y range then draw groups
all_gains = []
for w in workloads:
    d = raw[w]
    all_gains += [(d['rand_xor']-d['rand_delta'])/d['rand_xor']*100,
                  (d['is_xor']  -d['is_delta']  )/d['is_xor']  *100,
                  (d['ib_xor']  -d['ib_delta']  )/d['ib_xor']  *100]
ylo = min(all_gains) - 2
yhi = max(all_gains) + 4
ax_gain.set_ylim(ylo, yhi)
draw_groups(ax_gain, ylim_top=yhi, label_y_frac=0.97)

legend_patches = [
    mpatches.Patch(color=C_RAND, label='Random Bank'),
    mpatches.Patch(color=C_ISET, label='Ideal Set'),
    mpatches.Patch(color=C_IBNK, label='Ideal Bank'),
]
ax_gain.legend(handles=legend_patches, fontsize=8, loc='upper left',
               ncol=3, framealpha=0.85, edgecolor='#cccccc')

# ── super-title ───────────────────────────────────────────────────────────────
fig.suptitle(
    'LLC Compression: Plain BDI  |  XOR+BDI  |  Delta+BDI\n'
    'Workloads sorted by Ideal-Bank delta gain (left → right)',
    fontsize=12, fontweight='bold', y=0.975
)

plt.savefig(OUT_PNG, dpi=150, bbox_inches='tight')
plt.savefig(OUT_PDF, bbox_inches='tight')
print(f"Saved → {OUT_PNG}")
print(f"Saved → {OUT_PDF}")
