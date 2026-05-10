#include <bits/stdc++.h>
using namespace std;

static const int LINE_BYTES = 64;
static const int COMPRESS_THRESHOLD = 32;

using Line = array<uint8_t, LINE_BYTES>;

// ===================== BDI HELPERS =====================

static unsigned long long my_llabs(long long x) {
    unsigned long long t = (unsigned long long)x >> 63;
    return (x ^ t) - t;
}

long long unsigned* convertBuffer2Array(char* buffer, unsigned size, unsigned step) {
    unsigned n = size / step;
    auto* values = (long long unsigned*)malloc(sizeof(long long unsigned) * n);
    for (unsigned i = 0; i < n; i++) values[i] = 0ULL;

    for (unsigned i = 0; i < size; i += step) {
        for (unsigned j = 0; j < step; j++) {
            values[i / step] += (long long unsigned)((unsigned char)buffer[i + j]) << (8 * j);
        }
    }
    return values;
}

int isZeroPackable(long long unsigned* values, unsigned size) {
    for (unsigned i = 0; i < size; i++)
        if (values[i] != 0ULL) return 0;
    return 1;
}

int isSameValuePackable(long long unsigned* values, unsigned size) {
    for (unsigned i = 0; i < size; i++)
        if (values[i] != values[0]) return 0;
    return 1;
}

unsigned multBaseCompression(long long unsigned* values, unsigned size,
                             unsigned blimit, unsigned bsize) {
    unsigned long long limit = 0;
    switch (blimit) {
        case 1: limit = 0xFFULL; break;
        case 2: limit = 0xFFFFULL; break;
        case 4: limit = 0xFFFFFFFFULL; break;
        default: exit(1);
    }

    const unsigned BASES = 2;
    unsigned long long mbases[64];
    unsigned baseCount = 1;
    mbases[0] = values[0];

    for (unsigned i = 0; i < size; i++) {
        bool covered = false;
        for (unsigned j = 0; j < baseCount; j++) {
            if (my_llabs((long long)(mbases[j] - values[i])) <= (long long)limit) {
                covered = true;
                break;
            }
        }
        if (!covered) {
            mbases[baseCount++] = values[i];
            if (baseCount >= BASES) break;
        }
    }

    unsigned compCount = 0;
    for (unsigned i = 0; i < size; i++) {
        for (unsigned j = 0; j < baseCount; j++) {
            if (my_llabs((long long)(mbases[j] - values[i])) <= (long long)limit) {
                compCount++;
                break;
            }
        }
    }

    if (compCount < size) return size * bsize;
    unsigned mCompSize = blimit * compCount + bsize * BASES + (size - compCount) * bsize;
    return mCompSize;
}

unsigned BDICompress(char* buffer, unsigned _blockSize) {
    unsigned bestCSize = _blockSize;
    unsigned currCSize = _blockSize;

    long long unsigned* values = convertBuffer2Array(buffer, _blockSize, 8);
    if (isZeroPackable(values, _blockSize / 8)) bestCSize = 1;
    if (isSameValuePackable(values, _blockSize / 8)) currCSize = 8;
    bestCSize = min(bestCSize, currCSize);
    currCSize = multBaseCompression(values, _blockSize / 8, 1, 8);
    bestCSize = min(bestCSize, currCSize);
    currCSize = multBaseCompression(values, _blockSize / 8, 2, 8);
    bestCSize = min(bestCSize, currCSize);
    currCSize = multBaseCompression(values, _blockSize / 8, 4, 8);
    bestCSize = min(bestCSize, currCSize);
    free(values);

    values = convertBuffer2Array(buffer, _blockSize, 4);
    if (isSameValuePackable(values, _blockSize / 4)) currCSize = 4;
    bestCSize = min(bestCSize, currCSize);
    currCSize = multBaseCompression(values, _blockSize / 4, 1, 4);
    bestCSize = min(bestCSize, currCSize);
    currCSize = multBaseCompression(values, _blockSize / 4, 2, 4);
    bestCSize = min(bestCSize, currCSize);
    free(values);

    values = convertBuffer2Array(buffer, _blockSize, 2);
    currCSize = multBaseCompression(values, _blockSize / 2, 1, 2);
    bestCSize = min(bestCSize, currCSize);
    free(values);

    return bestCSize;
}

// ===================== XOR / DELTA HELPERS =====================

int xorDecisionEntropy(const uint8_t* A, const uint8_t* B) {
    int nonZero = 0;
    for (int k = 0; k < LINE_BYTES; ++k)
        if ((A[k] ^ B[k]) != 0) nonZero++;
    return nonZero;
}

struct DeltaInfo {
    int decisionEntropy;
    long long usum = 0;
    array<uint8_t, LINE_BYTES> deltas;
};

DeltaInfo deltaBestInfoBothDirs(const uint8_t* A, const uint8_t* B) {
    auto computeDir = [&](const uint8_t* base, const uint8_t* other) {
        DeltaInfo info;
        int nonZero = 0;
        long long usum = 0;
        for (int k = 0; k < LINE_BYTES; ++k) {
            uint8_t d = (uint8_t)(other[k] - base[k]);
            info.deltas[k] = d;
            if (d != 0) nonZero++;
            usum += d;
        }
        info.decisionEntropy = nonZero;
        info.usum = usum;
        return info;
    };

    DeltaInfo d1 = computeDir(A, B);  // B - A
    DeltaInfo d2 = computeDir(B, A);  // A - B
    // Pick the direction whose deltas are smaller as unsigned values.
    // sum(d1) + sum(d2) = 256 * nonZero, so minimizing one maximizes the other.
    return (d1.usum <= d2.usum) ? d1 : d2;
}

// ===================== COMMON STRUCTS =====================

struct LineRecord {
    bool compressed;
    Line data;
};

struct SetStats {
    int numLines = 0;
    int numCompressedPairs = 0;
    int numUncompressedLines = 0;
    long long compressedBytes = 0;
    long long uncompressedBytes = 0;
};

// ===================== BDI AFTER PAIRING =====================

long long computeBDIBytes(const vector<LineRecord>& outLines) {
    long long total = 0;
    char buf[LINE_BYTES];
    for (auto& rec : outLines) {
        for (int k = 0; k < LINE_BYTES; ++k)
            buf[k] = (char)rec.data[k];
        total += BDICompress(buf, LINE_BYTES);
    }
    return total;
}

// ===================== IDEAL SET (PER-SET, BEST PARTNER PER LINE) =====================

SetStats idealSetXORForSet(const vector<Line>& lines,
                           vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        int best_j = -1;
        int best_entropy = INT_MAX;

        for (int j = 0; j < n; ++j) {
            if (j == i || !available[j]) continue;
            int e = xorDecisionEntropy(lines[i].data(), lines[j].data());
            if (e < best_entropy) {
                best_entropy = e;
                best_j = j;
            }
        }

        if (best_j != -1 && best_entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[best_j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            for (int k = 0; k < LINE_BYTES; ++k)
                rec.data[k] = lines[i][k] ^ lines[best_j][k];
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

SetStats idealSetDeltaForSet(const vector<Line>& lines,
                             vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        int best_j = -1;
        int best_entropy = INT_MAX;
        Line bestDeltas{};

        for (int j = 0; j < n; ++j) {
            if (j == i || !available[j]) continue;

            DeltaInfo info = deltaBestInfoBothDirs(lines[i].data(), lines[j].data());
            int e = info.decisionEntropy;
            if (e < best_entropy) {
                best_entropy = e;
                best_j = j;
                bestDeltas = info.deltas;
            }
        }

        if (best_j != -1 && best_entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[best_j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            rec.data = bestDeltas;
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

SetStats idealSetXOR(const unordered_map<int, vector<Line>>& sets,
                     vector<LineRecord>& outLines) {
    SetStats total;
    for (auto& kv : sets) {
        const auto& lines = kv.second;
        SetStats s = idealSetXORForSet(lines, outLines);
        total.numLines           += s.numLines;
        total.numCompressedPairs += s.numCompressedPairs;
        total.numUncompressedLines += s.numUncompressedLines;
        total.compressedBytes    += s.compressedBytes;
        total.uncompressedBytes  += s.uncompressedBytes;
    }
    return total;
}

SetStats idealSetDelta(const unordered_map<int, vector<Line>>& sets,
                       vector<LineRecord>& outLines) {
    SetStats total;
    for (auto& kv : sets) {
        const auto& lines = kv.second;
        SetStats s = idealSetDeltaForSet(lines, outLines);
        total.numLines           += s.numLines;
        total.numCompressedPairs += s.numCompressedPairs;
        total.numUncompressedLines += s.numUncompressedLines;
        total.compressedBytes    += s.compressedBytes;
        total.uncompressedBytes  += s.uncompressedBytes;
    }
    return total;
}

// ===================== IDEAL BANK (GLOBAL BEST PARTNER PER LINE) =====================

SetStats idealBankXOR(const vector<Line>& lines,
                      vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        int best_j = -1;
        int best_entropy = INT_MAX;

        for (int j = 0; j < n; ++j) {
            if (j == i || !available[j]) continue;
            int e = xorDecisionEntropy(lines[i].data(), lines[j].data());
            if (e < best_entropy) {
                best_entropy = e;
                best_j = j;
            }
        }

        if (best_j != -1 && best_entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[best_j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            for (int k = 0; k < LINE_BYTES; ++k)
                rec.data[k] = lines[i][k] ^ lines[best_j][k];
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

SetStats idealBankDelta(const vector<Line>& lines,
                        vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        int best_j = -1;
        int best_entropy = INT_MAX;
        Line bestDeltas{};

        for (int j = 0; j < n; ++j) {
            if (j == i || !available[j]) continue;

            DeltaInfo info = deltaBestInfoBothDirs(lines[i].data(), lines[j].data());
            int e = info.decisionEntropy;
            if (e < best_entropy) {
                best_entropy = e;
                best_j = j;
                bestDeltas = info.deltas;
            }
        }

        if (best_j != -1 && best_entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[best_j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            rec.data = bestDeltas;
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

// ===================== RANDOM BANK (GLOBAL RANDOM PARTNER) =====================

SetStats randomBankXOR(const vector<Line>& lines,
                       vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);
    mt19937 rng(12345);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        vector<int> cand;
        for (int j = 0; j < n; ++j)
            if (j != i && available[j])
                cand.push_back(j);

        if (cand.empty()) {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
            continue;
        }

        int j = cand[rng() % cand.size()];
        int entropy = xorDecisionEntropy(lines[i].data(), lines[j].data());

        if (entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            for (int k = 0; k < LINE_BYTES; ++k)
                rec.data[k] = lines[i][k] ^ lines[j][k];
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

SetStats randomBankDelta(const vector<Line>& lines,
                         vector<LineRecord>& outLines) {
    int n = lines.size();
    SetStats stats;
    stats.numLines = n;
    if (n == 0) return stats;

    vector<bool> available(n, true);
    mt19937 rng(54321);

    for (int i = 0; i < n; ++i) {
        if (!available[i]) continue;

        vector<int> cand;
        for (int j = 0; j < n; ++j)
            if (j != i && available[j])
                cand.push_back(j);

        if (cand.empty()) {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
            continue;
        }

        int j = cand[rng() % cand.size()];

        DeltaInfo info = deltaBestInfoBothDirs(lines[i].data(), lines[j].data());
        int entropy = info.decisionEntropy;

        if (entropy <= COMPRESS_THRESHOLD) {
            available[i] = available[j] = false;
            stats.numCompressedPairs++;
            stats.compressedBytes += 64;

            LineRecord rec;
            rec.compressed = true;
            rec.data = info.deltas;
            outLines.push_back(rec);
        } else {
            available[i] = false;
            stats.numUncompressedLines++;
            stats.uncompressedBytes += 64;

            LineRecord rec;
            rec.compressed = false;
            rec.data = lines[i];
            outLines.push_back(rec);
        }
    }

    return stats;
}

// ===================== PRINTING =====================

void printPipelineStats(const string& title,
                        const SetStats& s,
                        long long bdiBytes,
                        long long originalBytes,
                        const string& label) {
    long long afterBytes = s.compressedBytes + s.uncompressedBytes;
    cout << "\n================ " << title << " " << label << " PIPELINE ================\n";
    cout << "Total lines: " << s.numLines << "\n";
    cout << "Compressed pairs: " << s.numCompressedPairs << "\n";
    cout << "Uncompressed lines: " << s.numUncompressedLines << "\n";
    cout << "After " << label << " bytes: " << afterBytes << "\n";
    cout << "After BDI on " << label << " bytes: " << bdiBytes << "\n";
    cout << "Final size ratio (" << label << "→BDI): "
         << (double)bdiBytes / originalBytes << "\n";
}

// ===================== MAIN =====================

int main() {
    ifstream fin("llc_dump_sets.txt");
    if (!fin) {
        cerr << "Cannot open llc_dump_sets.txt\n";
        return 1;
    }

    string header;
    getline(fin, header);

    unordered_map<int, vector<Line>> sets;
    vector<Line> bankLines;
    string line;

    while (getline(fin, line)) {
        if (line.empty()) continue;
        stringstream ss(line);
        int setIndex;
        string hexData;
        if (!(ss >> setIndex >> hexData)) continue;
        if (hexData.size() < 128) continue;

        Line bytes{};
        for (int i = 0; i < 64; ++i) {
            string b = hexData.substr(i * 2, 2);
            bytes[i] = (uint8_t)strtol(b.c_str(), nullptr, 16);
        }
        sets[setIndex].push_back(bytes);
        bankLines.push_back(bytes);
    }

    long long totalLines = bankLines.size();
    long long originalBytes = totalLines * LINE_BYTES;

    // Plain BDI
    long long plainBDIBytes = 0;
    {
        char buf[LINE_BYTES];
        for (auto& l : bankLines) {
            for (int k = 0; k < LINE_BYTES; ++k)
                buf[k] = (char)l[k];
            plainBDIBytes += BDICompress(buf, LINE_BYTES);
        }
    }

    cout << fixed << setprecision(6);

    cout << "\n================ PLAIN BDI ================\n";
    cout << "Total lines: " << totalLines << "\n";
    cout << "BDI bytes: " << plainBDIBytes << "\n";
    cout << "Original bytes: " << originalBytes << "\n";
    cout << "Final size ratio: " << (double)plainBDIBytes / originalBytes << "\n";

    // ===== IDEAL SET =====
    vector<LineRecord> idealSetXorOut, idealSetDeltaOut;
    SetStats idealSetXorStats = idealSetXOR(sets, idealSetXorOut);
    SetStats idealSetDeltaStats = idealSetDelta(sets, idealSetDeltaOut);

    long long idealSetXorBDI = computeBDIBytes(idealSetXorOut);
    long long idealSetDeltaBDI = computeBDIBytes(idealSetDeltaOut);

    printPipelineStats("IDEAL SET", idealSetXorStats, idealSetXorBDI, originalBytes, "XOR");
    printPipelineStats("IDEAL SET", idealSetDeltaStats, idealSetDeltaBDI, originalBytes, "DELTA");

    // ===== IDEAL BANK =====
    vector<LineRecord> idealBankXorOut, idealBankDeltaOut;
    SetStats idealBankXorStats = idealBankXOR(bankLines, idealBankXorOut);
    SetStats idealBankDeltaStats = idealBankDelta(bankLines, idealBankDeltaOut);

    long long idealBankXorBDI = computeBDIBytes(idealBankXorOut);
    long long idealBankDeltaBDI = computeBDIBytes(idealBankDeltaOut);

    printPipelineStats("IDEAL BANK", idealBankXorStats, idealBankXorBDI, originalBytes, "XOR");
    printPipelineStats("IDEAL BANK", idealBankDeltaStats, idealBankDeltaBDI, originalBytes, "DELTA");

    // ===== RANDOM BANK =====
    vector<LineRecord> randomBankXorOut, randomBankDeltaOut;
    SetStats randomBankXorStats = randomBankXOR(bankLines, randomBankXorOut);
    SetStats randomBankDeltaStats = randomBankDelta(bankLines, randomBankDeltaOut);

    long long randomBankXorBDI = computeBDIBytes(randomBankXorOut);
    long long randomBankDeltaBDI = computeBDIBytes(randomBankDeltaOut);

    printPipelineStats("RANDOM BANK", randomBankXorStats, randomBankXorBDI, originalBytes, "XOR");
    printPipelineStats("RANDOM BANK", randomBankDeltaStats, randomBankDeltaBDI, originalBytes, "DELTA");

    return 0;
}
