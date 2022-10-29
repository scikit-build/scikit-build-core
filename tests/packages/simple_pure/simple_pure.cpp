#include <vector>
#include <variant>
#include <string>
#include <iostream>

int main() {
    std::vector<std::variant<int, std::string>> v{0, "one", 2, "three"};

    for (auto& e : v) {
        std::visit([](auto&& arg) {
            std::cout << arg << ' ';
        }, e);
    }
    std::cout << '\n';

    return 0;
}
