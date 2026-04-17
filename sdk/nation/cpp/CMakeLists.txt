cmake_minimum_required(VERSION 3.14)

project(nrn-sdk VERSION 1.0.0 LANGUAGES CXX)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)

option(NRN_SDK_BUILD_EXAMPLES "Build C++ SDK examples" OFF)
option(NRN_SDK_INSTALL "Enable install rules" ON)
option(NRN_BUILD_TESTS "Build C++ SDK tests" OFF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Threads REQUIRED)

add_library(nrn-sdk nrn.cpp)
add_library(nrn::sdk ALIAS nrn-sdk)

target_include_directories(
  nrn-sdk
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/nrn-sdk>
)

target_link_libraries(nrn-sdk PUBLIC Threads::Threads)

if(WIN32)
  target_link_libraries(nrn-sdk PUBLIC ws2_32)
endif()

if(NRN_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

if(NRN_SDK_INSTALL)
  install(TARGETS nrn-sdk EXPORT nrn-sdkTargets)
  install(FILES nrn.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/nrn-sdk)

  write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/nrn-sdkConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
  )

  configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/nrn-sdkConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/nrn-sdkConfig.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/nrn-sdk"
  )

  install(
    EXPORT nrn-sdkTargets
    FILE nrn-sdkTargets.cmake
    NAMESPACE nrn::
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/nrn-sdk"
  )

  install(
    FILES
      "${CMAKE_CURRENT_BINARY_DIR}/nrn-sdkConfig.cmake"
      "${CMAKE_CURRENT_BINARY_DIR}/nrn-sdkConfigVersion.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/nrn-sdk"
  )
endif()
