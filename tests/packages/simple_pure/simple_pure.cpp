#include <vector>
#include <string>
#include <iostream>

int main() {
    std::vector<std::string> v{"0", "one", "2", "three"};

    for (const auto& arg : v) {
        std::cout << arg << ' ';
    }
    std::cout << '\n';

    return 0;
}
