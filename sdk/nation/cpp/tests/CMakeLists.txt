include(FetchContent)

FetchContent_Declare(
  Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG v3.7.1
)

FetchContent_MakeAvailable(Catch2)

add_executable(nrn-sdk-tests test_nrn.cpp)
target_link_libraries(nrn-sdk-tests PRIVATE nrn-sdk Catch2::Catch2WithMain)

include(Catch)
catch_discover_tests(nrn-sdk-tests)
