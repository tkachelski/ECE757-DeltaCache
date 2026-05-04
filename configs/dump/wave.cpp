#include <cmath>
#include <vector>

int main() {
    const int N = 1000000;
    std::vector<int> data(N);

    for (int i = 0; i < N; i++) {
        data[i] = (int)(1000 * sin(i * 0.01));
    }

    // prevent optimization from removing it
    long long sum = 0;
    for (int i = 0; i < N; i++) {
        sum += data[i];
    }

    return sum;
}
