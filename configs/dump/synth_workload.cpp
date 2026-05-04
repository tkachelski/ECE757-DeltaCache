#include <iostream>
#include <vector>
#include <cmath>

int main() {
    const int N = 1 << 20;      // 1M elements
    const double base = 1.0;
    const double tiny_delta = 1e-6;

    std::vector<double> A(N);
    std::vector<double> B(N);

    // A: smooth affine pattern with occasional exponent jumps
    for (int i = 0; i < N; i++) {
        double v = base + i * 1e-3;   // smooth ramp
        if ((i % 1024) == 0) {
            // inject exponent jump every 1024 elements
            v *= 1e3;
        }
        A[i] = v;
    }

    // B: A plus tiny numeric delta (Delta-friendly)
    for (int i = 0; i < N; i++) {
        B[i] = A[i] + tiny_delta;
    }

    // Simple daxpy-like sweep to touch both arrays repeatedly
    double acc = 0.0;
    for (int r = 0; r < 50; r++) {
        for (int i = 0; i < N; i++) {
            acc += A[i] * 1.000001 + B[i] * 0.999999;
        }
    }

    std::cout << "acc = " << acc << "\n";
    return 0;
}
