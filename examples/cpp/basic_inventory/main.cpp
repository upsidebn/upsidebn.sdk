#include "../../../sdk/nation/cpp/nrn.hpp"

#include <iostream>

int main() {
    nrn::NRNReader reader("/dev/ttyUSB0", 115200);
    if (!reader.open()) {
        std::cerr << "Failed to open reader\n";
        return 1;
    }

    reader.connect_and_initialize();
    reader.start_inventory(0x01, [](const nrn::TagData& tag) { std::cout << tag.epc << '\n'; });
    reader.stop_inventory();
    reader.close();
    return 0;
}
