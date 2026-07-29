#include <iostream>
#include <string>
#include <vector>

class TokenCompressor {
public:
    double compute_compression_ratio(size_t raw_tokens, size_t compressed_tokens) {
        if (raw_tokens == 0) return 0.0;
        return (1.0 - (static_cast<double>(compressed_tokens) / raw_tokens)) * 100.0;
    }
};

int main() {
    TokenCompressor compressor;
    double ratio = compressor.compute_compression_ratio(128000, 18500);
    std::cout << "Token Saver Compression Ratio: " << ratio << "%" << std::endl;
    return 0;
}
