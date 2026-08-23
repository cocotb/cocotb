cmake_minimum_required(VERSION 3.15)

# Prevent CMake from picking up GCC-style environment flags when targeting
# MSVC. These values are intentionally established before project() enables
# the compiler.
if(WIN32)
    set(ENV{CFLAGS} "")
    set(ENV{CXXFLAGS} "")
    set(ENV{LDFLAGS} "")

    set(CMAKE_CXX_FLAGS "/W3" CACHE STRING "CXX compiler flags" FORCE)
    set(CMAKE_CXX_FLAGS_DEBUG "/MDd /Zi /Ob0 /Od /RTC1" CACHE STRING "CXX debug flags" FORCE)
    set(CMAKE_CXX_FLAGS_RELEASE "/MD /O2 /Ob2 /DNDEBUG" CACHE STRING "CXX release flags" FORCE)
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/MD /Zi /O2 /Ob1 /DNDEBUG" CACHE STRING "CXX release with debug info flags" FORCE)
    set(CMAKE_CXX_FLAGS_MINSIZEREL "/MD /O1 /Ob1 /DNDEBUG" CACHE STRING "CXX min size release flags" FORCE)
endif()

file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" COCOTB_VERSION LIMIT_COUNT 1)
project(cocotb VERSION "${COCOTB_VERSION}" LANGUAGES CXX)

set(CMAKE_SKIP_RPATH TRUE)

if(WIN32)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

set(COCOTB_PYTHON_DIR "${PROJECT_SOURCE_DIR}/python")
set(COCOTB_PYTHON_PACKAGE_DIR "${COCOTB_PYTHON_DIR}/cocotb")
set(COCOTB_INSTALL_LIBRARY_DIR "cocotb/libs")
set(COCOTB_INSTALL_INCLUDE_DIR "cocotb/share/include")
set(COCOTB_INSTALL_CMAKE_DIR "cocotb/share/cmake/cocotb")

# Editable installs build native libraries directly into the source packages and
# therefore do not need CMake install rules. Normal CMake and wheel builds
# install artifacts.
if(SKBUILD_STATE STREQUAL "editable")
    set(COCOTB_INSTALL_ARTIFACTS FALSE)
else()
    set(COCOTB_INSTALL_ARTIFACTS TRUE)
endif()

include(cmake/CocotbBuild.cmake)

add_subdirectory(cpp)
add_subdirectory(python)

include(CMakePackageConfigHelpers)

if(SKBUILD_STATE STREQUAL "editable")
    set(COCOTB_BUILD_TREE_CMAKE_DIR
        "${PROJECT_SOURCE_DIR}/build/cmake/cocotb"
    )
    file(MAKE_DIRECTORY "${COCOTB_BUILD_TREE_CMAKE_DIR}")
    export(
        TARGETS cocotb_bootstrap gpi
        FILE "${COCOTB_BUILD_TREE_CMAKE_DIR}/cocotbTargets.cmake"
        NAMESPACE cocotb::
    )
    configure_file(
        cmake/cocotbBuildTreeConfig.cmake.in
        "${COCOTB_BUILD_TREE_CMAKE_DIR}/cocotbConfig.cmake"
        @ONLY
    )
    write_basic_package_version_file(
        "${COCOTB_BUILD_TREE_CMAKE_DIR}/cocotbConfigVersion.cmake"
        VERSION "${PROJECT_VERSION}"
        COMPATIBILITY SameMajorVersion
    )
endif()

if(COCOTB_INSTALL_ARTIFACTS)
    install(
        EXPORT cocotbTargets
        FILE cocotbTargets.cmake
        NAMESPACE cocotb::
        DESTINATION "${COCOTB_INSTALL_CMAKE_DIR}"
    )

    configure_package_config_file(
        cmake/cocotbConfig.cmake.in
        "${CMAKE_CURRENT_BINARY_DIR}/cocotbConfig.cmake"
        INSTALL_DESTINATION "${COCOTB_INSTALL_CMAKE_DIR}"
    )
    write_basic_package_version_file(
        "${CMAKE_CURRENT_BINARY_DIR}/cocotbConfigVersion.cmake"
        VERSION "${PROJECT_VERSION}"
        COMPATIBILITY SameMajorVersion
    )
    install(
        FILES
            "${CMAKE_CURRENT_BINARY_DIR}/cocotbConfig.cmake"
            "${CMAKE_CURRENT_BINARY_DIR}/cocotbConfigVersion.cmake"
        DESTINATION "${COCOTB_INSTALL_CMAKE_DIR}"
    )
endif()
