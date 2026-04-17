#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <vector>

#include "../nrn.hpp"

TEST_CASE("RSSI conversion matches expected values") {
    REQUIRE(nrn::calculate_rssi(0) == -100);
    REQUIRE(nrn::calculate_rssi(128) == -65);
    REQUIRE(nrn::calculate_rssi(255) == -30);
}

TEST_CASE("Frequency conversion matches expected values") {
    REQUIRE(nrn::calculate_frequency(0) == Catch::Approx(920.0));
    REQUIRE(nrn::calculate_frequency(10) == Catch::Approx(925.0));
}

TEST_CASE("Antenna mask builder handles sparse antennas") {
    REQUIRE(nrn::build_antenna_mask({1, 4, 7, 32}) == 0x80000049);
}

TEST_CASE("Bytes to hex is uppercase") {
    REQUIRE(nrn::bytes_to_hex({0xDE, 0xAD, 0xBE, 0xEF}) == "DEADBEEF");
}

TEST_CASE("Build frame round-trips through parser") {
    nrn::NRNReader reader("mock");
    const auto payload = std::vector<uint8_t>{0x00, 0x00, 0x00, 0x01, 0x01};
    const auto frame = reader.build_frame(nrn::MID::READ_EPC_TAG, payload);
    const auto parsed = reader.parse_frame(frame);

    REQUIRE(parsed.valid);
    REQUIRE(parsed.category == 0x02);
    REQUIRE(parsed.mid == 0x10);
    REQUIRE(parsed.data == payload);
}

TEST_CASE("Parse frame rejects invalid headers") {
    nrn::NRNReader reader("mock");
    const auto parsed = reader.parse_frame({0x00, 0x01, 0x02});
    REQUIRE_FALSE(parsed.valid);
}

TEST_CASE("Parse EPC handles captured notification payload") {
    nrn::NRNReader reader("mock");
    const auto payload =
        std::vector<uint8_t>{0x00, 0x08, 0x30, 0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x30,
                             0x00, 0x01, 0x01, 0x80, 0x08, 0x00, 0x0E, 0x0B, 0xD4, 0x09, 0x40};
    const auto frame = reader.build_frame(nrn::MID::READ_EPC_TAG, payload);
    const auto parsed = reader.parse_frame(frame);
    const auto tag = reader.parse_epc(parsed.data);

    REQUIRE(parsed.valid);
    REQUIRE(tag.epc == "3000112233445566");
    REQUIRE(tag.pc == "3000");
    REQUIRE(tag.antenna_id == 1);
    REQUIRE(tag.rssi.has_value());
    REQUIRE(*tag.rssi == -65);
    REQUIRE(tag.frequency.has_value());
    REQUIRE(*tag.frequency == Catch::Approx(920.532));
}
