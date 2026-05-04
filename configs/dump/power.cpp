#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

#pragma pack(push, 1)
struct LoadRecord {
    int64_t timestamp;
    int32_t load;
};
#pragma pack(pop)

static_assert(sizeof(LoadRecord) == 12, "LoadRecord must be 12 bytes");

int main(int argc, char** argv) {
    const char* filename = (argc > 1) ? argv[1] : "configs/dump/power.bin";

    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "Failed to open " << filename << "\n";
        return 1;
    }

    std::vector<LoadRecord> data;
    LoadRecord r;

    while (file.read(reinterpret_cast<char*>(&r), sizeof(r))) {
        data.push_back(r);
    }

    std::cout << "Loaded " << data.size() << " records\n";

    volatile int64_t sum = 0;

    for (int pass = 0; pass < 10000; pass++) {
        for (size_t i = 1; i < data.size(); i++) {
            sum += data[i].load;
            sum += data[i].load - data[i - 1].load;
        }
    }

    std::cout << "Sum = " << sum << "\n";
    return 0;
}
