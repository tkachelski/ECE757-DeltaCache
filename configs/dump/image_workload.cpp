#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>

struct Image {
    int width;
    int height;
    int maxval;
    std::vector<uint8_t> data; // RGBRGBRGB...
};

Image load_ppm(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Failed to open image");
    }

    std::string magic;
    file >> magic;

    if (magic != "P6") {
        throw std::runtime_error("Only binary PPM P6 supported");
    }

    Image img;
    file >> img.width >> img.height >> img.maxval;
    file.get(); // consume newline after maxval

    if (img.maxval != 255) {
        throw std::runtime_error("Only maxval 255 supported");
    }

    img.data.resize(img.width * img.height * 3);
    file.read(reinterpret_cast<char*>(img.data.data()), img.data.size());

    return img;
}

int main(int argc, char** argv) {
    std::string filename = "input.ppm";
    if (argc > 1) filename = argv[1];

    Image img = load_ppm(filename);

    std::cout << "Loaded image: "
              << img.width << "x" << img.height
              << " bytes=" << img.data.size() << "\n";

    volatile uint64_t checksum = 0;

    // Repeated image processing to create cache activity
    for (int pass = 0; pass < 1000; pass++) {
        for (size_t i = 3; i + 3 < img.data.size(); i += 3) {
            uint8_t r = img.data[i];
            uint8_t g = img.data[i + 1];
            uint8_t b = img.data[i + 2];

            // simple grayscale-ish computation
            uint8_t gray = static_cast<uint8_t>((r + g + b) / 3);

            img.data[i]     = gray;
            img.data[i + 1] = gray;
            img.data[i + 2] = gray;

            checksum += gray;
        }
    }

    std::cout << "Checksum: " << checksum << "\n";
    return 0;
}
