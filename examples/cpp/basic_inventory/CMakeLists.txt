cmake_minimum_required(VERSION 3.14)
project(nrn_basic_inventory LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(../../../sdk/nation/cpp sdk_nrn_cpp)

add_executable(nrn_basic_inventory main.cpp)
target_link_libraries(nrn_basic_inventory PRIVATE nrn-sdk)
