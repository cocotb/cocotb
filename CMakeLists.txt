cmake_minimum_required(VERSION 3.15)

# Clear problematic environment variables before project() command
# This prevents CMake from picking up GCC-style flags for MSVC
if(WIN32)
    set(ENV{CFLAGS} "")
    set(ENV{CXXFLAGS} "")
    set(ENV{LDFLAGS} "")
    
    # Force MSVC-compatible flags from the start using cache variables
    # This will override any environment variables
    set(CMAKE_CXX_FLAGS "/W3" CACHE STRING "CXX compiler flags" FORCE)
    set(CMAKE_CXX_FLAGS_DEBUG "/MDd /Zi /Ob0 /Od /RTC1" CACHE STRING "CXX debug flags" FORCE)
    set(CMAKE_CXX_FLAGS_RELEASE "/MD /O2 /Ob2 /DNDEBUG" CACHE STRING "CXX release flags" FORCE)
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/MD /Zi /O2 /Ob1 /DNDEBUG" CACHE STRING "CXX release with debug info flags" FORCE)
    set(CMAKE_CXX_FLAGS_MINSIZEREL "/MD /O1 /Ob1 /DNDEBUG" CACHE STRING "CXX min size release flags" FORCE)
endif()

project(cocotb LANGUAGES CXX)

# MSVC flag validation
if(MSVC)
    message(STATUS "MSVC detected - using forced MSVC-compatible flags")
    message(STATUS "CMAKE_CXX_FLAGS: ${CMAKE_CXX_FLAGS}")
endif()

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Include scikit-build-core helpers
if(SKBUILD)
    find_package(pybind11 CONFIG REQUIRED)
endif()

# Platform-specific settings
if(WIN32)
    set(LIB_EXT "dll")
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
else()
    set(LIB_EXT "so")
endif()

# Compiler-specific settings
if(MSVC)
    set(EXTRA_CXX_FLAGS "/permissive-" "/W4")
    # Disable automatic manifest generation
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /MANIFEST:NO")
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} /MANIFEST:NO")
else()
    set(BASE_WARNS
        "-Wall" "-Wextra" "-Wcast-qual" "-Wwrite-strings" "-Wconversion"
        "-Wno-missing-field-initializers" "-Werror=shadow"
    )
    set(CXX_WARNS ${BASE_WARNS} "-Wnon-virtual-dtor" "-Woverloaded-virtual")
    set(EXTRA_CXX_FLAGS
        "-std=c++11" "-fvisibility=hidden" "-fvisibility-inlines-hidden"
        ${CXX_WARNS}
    )
    if(NOT WIN32)
        list(APPEND EXTRA_CXX_FLAGS "-flto")
    endif()
    
    # Windows-specific GCC/MinGW settings
    if(WIN32)
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,--exclude-all-symbols")
    else()
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -flto")
        
        # Linux-specific: avoid libstdc++ runtime dependency
        if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
            set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static-libstdc++")
        endif()
    endif()
endif()

# Common definitions
set(EXTRA_DEFINES "__STDC_FORMAT_MACROS")

# Get Python library for linking
if(APPLE)
    set(PYTHON_LIB_VAR "LIBRARY")
else()
    set(PYTHON_LIB_VAR "LDLIBRARY")
endif()

execute_process(
    COMMAND ${Python_EXECUTABLE} -c "import sysconfig; print(sysconfig.get_config_var('${PYTHON_LIB_VAR}') or '')"
    OUTPUT_VARIABLE PYTHON_LDLIBRARY
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

if(PYTHON_LDLIBRARY)
    get_filename_component(PYTHON_LIB_LINK ${PYTHON_LDLIBRARY} NAME_WLE)
    string(REGEX REPLACE "^lib" "" PYTHON_LIB_LINK ${PYTHON_LIB_LINK})
else()
    string(REPLACE "." "" PYTHON_VERSION_NODOT ${Python_VERSION_MAJOR}${Python_VERSION_MINOR})
    set(PYTHON_LIB_LINK "python${PYTHON_VERSION_NODOT}")
endif()

if(WIN32)
    set(PYTHON_LIB "${PYTHON_LIB_LINK}.${LIB_EXT}")
elseif(APPLE)
    set(PYTHON_LIB_DIR ${Python_STDLIB}/../..)
    if(EXISTS "${PYTHON_LIB_DIR}/lib${PYTHON_LIB_LINK}.dylib")
        set(PYTHON_LIB "${PYTHON_LIB_DIR}/lib${PYTHON_LIB_LINK}.dylib")
    else()
        set(PYTHON_LIB "${PYTHON_LIB_DIR}/lib${PYTHON_LIB_LINK}.so")
    endif()
else()
    set(PYTHON_LIB "lib${PYTHON_LIB_LINK}.${LIB_EXT}")
endif()

# Include directories
set(INCLUDE_DIRS
    ${CMAKE_SOURCE_DIR}/src/cocotb/share/include
    ${CMAKE_SOURCE_DIR}/src/cocotb
    ${Python_INCLUDE_DIRS}
)

# Share library directory
set(SHARE_LIB_DIR ${CMAKE_SOURCE_DIR}/src/cocotb/share/lib)

# Windows-specific functions for manifests and resource files
if(WIN32)
    # Function to create side-by-side assembly manifest
    function(create_sxs_assembly_manifest NAME FILENAME LIBRARIES DEPENDENCY_ONLY MANIFEST_VAR)
        if(CMAKE_SIZEOF_VOID_P EQUAL 8)
            set(ARCHITECTURE "amd64")
        else()
            set(ARCHITECTURE "x86")
        endif()
        
        set(DEPENDENCIES "")
        foreach(LIB ${LIBRARIES})
            string(APPEND DEPENDENCIES "        <dependency>\n")
            string(APPEND DEPENDENCIES "            <dependentAssembly>\n")
            string(APPEND DEPENDENCIES "                <assemblyIdentity name=\"${LIB}\" version=\"1.0.0.0\" type=\"win32\" processorArchitecture=\"${ARCHITECTURE}\" />\n")
            string(APPEND DEPENDENCIES "            </dependentAssembly>\n")
            string(APPEND DEPENDENCIES "        </dependency>\n")
        endforeach()
        
        if(NOT DEPENDENCY_ONLY)
            set(MANIFEST_BODY "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n")
            string(APPEND MANIFEST_BODY "<assembly xmlns=\"urn:schemas-microsoft-com:asm.v1\" manifestVersion=\"1.0\">\n")
            string(APPEND MANIFEST_BODY "    <assemblyIdentity name=\"${NAME}\" version=\"1.0.0.0\" type=\"win32\" processorArchitecture=\"${ARCHITECTURE}\" />\n")
            string(APPEND MANIFEST_BODY "    <file name=\"${FILENAME}\" />\n")
            string(APPEND MANIFEST_BODY "${DEPENDENCIES}")
            string(APPEND MANIFEST_BODY "</assembly>\n")
        else()
            set(MANIFEST_BODY "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n")
            string(APPEND MANIFEST_BODY "<assembly xmlns=\"urn:schemas-microsoft-com:asm.v1\" manifestVersion=\"1.0\">\n")
            string(APPEND MANIFEST_BODY "${DEPENDENCIES}")
            string(APPEND MANIFEST_BODY "</assembly>\n")
        endif()
        
        set(${MANIFEST_VAR} "${MANIFEST_BODY}" PARENT_SCOPE)
    endfunction()
    
    # Function to create resource files
    function(create_rc_file RC_FILENAME NAME FILENAME LIBRARIES RUNTIME_LIBRARIES)
        create_sxs_assembly_manifest(${NAME} ${FILENAME} "${LIBRARIES}" FALSE MANIFEST)
        
        # Escape quotes and format for RC file
        string(REPLACE "\"" "\"\"" MANIFEST "${MANIFEST}")
        string(REPLACE "\n" "\\r\\n\"\n\"" MANIFEST "${MANIFEST}")
        set(MANIFEST "\"${MANIFEST}\"")
        
        set(RC_BODY "#pragma code_page(65001) // UTF-8\n")
        string(APPEND RC_BODY "#include <Windows.h>\n\n")
        string(APPEND RC_BODY "LANGUAGE 0x00, 0x00\n\n")
        string(APPEND RC_BODY "ISOLATIONAWARE_MANIFEST_RESOURCE_ID RT_MANIFEST\n")
        string(APPEND RC_BODY "BEGIN\n")
        string(APPEND RC_BODY "${MANIFEST}\n")
        string(APPEND RC_BODY "END\n")
        
        if(RUNTIME_LIBRARIES)
            create_sxs_assembly_manifest(${NAME} ${FILENAME} "${RUNTIME_LIBRARIES}" TRUE RUNTIME_MANIFEST)
            string(REPLACE "\"" "\"\"" RUNTIME_MANIFEST "${RUNTIME_MANIFEST}")
            string(REPLACE "\n" "\\r\\n\"\n\"" RUNTIME_MANIFEST "${RUNTIME_MANIFEST}")
            set(RUNTIME_MANIFEST "\"${RUNTIME_MANIFEST}\"")
            
            string(APPEND RC_BODY "\n1000 RT_MANIFEST\n")
            string(APPEND RC_BODY "BEGIN\n")
            string(APPEND RC_BODY "${RUNTIME_MANIFEST}\n")
            string(APPEND RC_BODY "END\n")
        endif()
        
        file(WRITE ${RC_FILENAME} "${RC_BODY}")
    endfunction()
endif()

# Function to add a cocotb library
function(add_cocotb_library TARGET_NAME)
    set(options "")
    set(oneValueArgs "OUTPUT_NAME")
    set(multiValueArgs "SOURCES" "LIBRARIES" "DEFINES" "RC_LIBRARIES" "RC_RUNTIME_LIBRARIES")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    
    # Handle Windows resource files
    set(ALL_SOURCES ${ARG_SOURCES})
    if(WIN32)
        set(RC_FILENAME "${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}.rc")
        set(LIB_NAME ${ARG_OUTPUT_NAME})
        if(NOT LIB_NAME)
            set(LIB_NAME ${TARGET_NAME})
        endif()
        
        # Strip lib prefix for MSVC
        if(MSVC AND LIB_NAME MATCHES "^lib(.+)")
            string(REGEX REPLACE "^lib" "" LIB_NAME ${LIB_NAME})
        endif()
        
        set(RC_LIBS ${ARG_RC_LIBRARIES})
        if(MSVC)
            # Strip lib prefix from RC libraries for MSVC
            set(RC_LIBS_PROCESSED "")
            foreach(LIB ${RC_LIBS})
                if(LIB MATCHES "^lib(.+)")
                    string(REGEX REPLACE "^lib" "" LIB ${LIB})
                endif()
                list(APPEND RC_LIBS_PROCESSED ${LIB})
            endforeach()
            set(RC_LIBS ${RC_LIBS_PROCESSED})
        endif()
        
        set(RC_RUNTIME_LIBS ${ARG_RC_RUNTIME_LIBRARIES})
        if(MSVC AND RC_RUNTIME_LIBS)
            set(RC_RUNTIME_LIBS_PROCESSED "")
            foreach(LIB ${RC_RUNTIME_LIBS})
                if(LIB MATCHES "^lib(.+)")
                    string(REGEX REPLACE "^lib" "" LIB ${LIB})
                endif()
                list(APPEND RC_RUNTIME_LIBS_PROCESSED ${LIB})
            endforeach()
            set(RC_RUNTIME_LIBS ${RC_RUNTIME_LIBS_PROCESSED})
        endif()
        
        create_rc_file(${RC_FILENAME} ${LIB_NAME} "${LIB_NAME}.${LIB_EXT}" "${RC_LIBS}" "${RC_RUNTIME_LIBS}")
        list(APPEND ALL_SOURCES ${RC_FILENAME})
    endif()
    
    # Create the library
    add_library(${TARGET_NAME} SHARED ${ALL_SOURCES})
    
    # Set output name
    if(ARG_OUTPUT_NAME)
        set_target_properties(${TARGET_NAME} PROPERTIES OUTPUT_NAME ${ARG_OUTPUT_NAME})
    endif()
    
    # Set include directories
    target_include_directories(${TARGET_NAME} PRIVATE ${INCLUDE_DIRS})
    
    # Set compile definitions
    target_compile_definitions(${TARGET_NAME} PRIVATE ${ARG_DEFINES} ${EXTRA_DEFINES})
    
    # Set compile options
    target_compile_options(${TARGET_NAME} PRIVATE ${EXTRA_CXX_FLAGS})
    
    # Link libraries
    if(ARG_LIBRARIES)
        target_link_libraries(${TARGET_NAME} PRIVATE ${ARG_LIBRARIES})
    endif()
    
    # Windows-specific settings
    if(WIN32)
        target_compile_definitions(${TARGET_NAME} PRIVATE WIN32)
        # Add DEF directory to library search path for simulator libraries
        if(TARGET_NAME MATCHES "cocotb.*_(icarus|modelsim|aldec|ghdl)")
            target_link_directories(${TARGET_NAME} PRIVATE ${CMAKE_SOURCE_DIR}/src/cocotb/share/def)
        endif()
    endif()
    
    # Set RPATH for non-Windows platforms
    if(NOT WIN32)
        if(TARGET_NAME STREQUAL "simulator")
            set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN/libs")
        else()
            set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN")
        endif()
        
        if(APPLE)
            if(NOT TARGET_NAME STREQUAL "simulator")
                set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_NAME_DIR "@rpath")
            endif()
        endif()
    endif()
    
    # Set output directory
    set_target_properties(${TARGET_NAME} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb/libs
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb/libs
    )
endfunction()

# Build libraries in dependency order

# 1. gpilog
add_cocotb_library(gpilog
    SOURCES ${SHARE_LIB_DIR}/gpi_log/gpi_logging.cpp
    DEFINES GPILOG_EXPORTS
    RC_LIBRARIES ""
)

# 2. pygpilog  
add_cocotb_library(pygpilog
    SOURCES ${SHARE_LIB_DIR}/py_gpi_log/py_gpi_logging.cpp
    DEFINES PYGPILOG_EXPORTS
    LIBRARIES gpilog ${Python_LIBRARIES}
    RC_LIBRARIES "gpilog"
)
if(WIN32)
    target_link_directories(pygpilog PRIVATE ${Python_LIBRARY_DIRS})
endif()

# 3. cocotbutils
set(COCOTBUTILS_LIBS gpilog)
if(UNIX AND NOT APPLE)
    list(APPEND COCOTBUTILS_LIBS dl)
endif()

add_cocotb_library(cocotbutils
    SOURCES ${SHARE_LIB_DIR}/utils/cocotb_utils.cpp
    DEFINES COCOTBUTILS_EXPORTS
    LIBRARIES ${COCOTBUTILS_LIBS}
    RC_LIBRARIES "gpilog"
)

# 4. embed
if(MSVC)
    set(EMBED_IMPL_LIB_NAME "cocotb.${LIB_EXT}")
else()
    set(EMBED_IMPL_LIB_NAME "libcocotb.${LIB_EXT}")
endif()

add_cocotb_library(embed
    SOURCES ${SHARE_LIB_DIR}/embed/embed.cpp
    DEFINES COCOTB_EMBED_EXPORTS "PYTHON_LIB=${PYTHON_LIB}" "EMBED_IMPL_LIB=${EMBED_IMPL_LIB_NAME}"
    LIBRARIES gpilog cocotbutils
    RC_LIBRARIES "gpilog;cocotbutils"
    RC_RUNTIME_LIBRARIES "cocotb"
)

# 5. gpi
add_cocotb_library(gpi
    SOURCES 
        ${SHARE_LIB_DIR}/gpi/GpiCbHdl.cpp
        ${SHARE_LIB_DIR}/gpi/GpiCommon.cpp
    DEFINES GPI_EXPORTS "LIB_EXT=${LIB_EXT}" SINGLETON_HANDLES
    LIBRARIES cocotbutils gpilog embed
    RC_LIBRARIES "cocotbutils;gpilog;embed"
)

# 6. cocotb
add_cocotb_library(cocotb
    SOURCES ${SHARE_LIB_DIR}/embed/gpi_embed.cpp
    LIBRARIES gpilog cocotbutils pygpilog gpi ${Python_LIBRARIES}
    RC_LIBRARIES "gpilog;cocotbutils;pygpilog;gpi"
)
if(WIN32)
    target_link_directories(cocotb PRIVATE ${Python_LIBRARY_DIRS})
endif()

# Set simulator Python extension suffix first
if(WIN32)
    set(PYTHON_EXT_SUFFIX ".${Python_SOABI}.pyd")
else()
    set(PYTHON_EXT_SUFFIX ".${Python_SOABI}${CMAKE_SHARED_LIBRARY_SUFFIX}")
endif()

# 7. simulator (Python extension)
if(WIN32)
    # For Windows, don't use RC manifest for simulator to avoid SxS issues
    # The DLL search path approach handles dependency loading
    add_library(simulator SHARED ${SHARE_LIB_DIR}/simulator/simulatormodule.cpp)
    target_include_directories(simulator PRIVATE ${INCLUDE_DIRS})
    target_compile_definitions(simulator PRIVATE ${EXTRA_DEFINES} WIN32)
    target_compile_options(simulator PRIVATE ${EXTRA_CXX_FLAGS})
    target_link_libraries(simulator PRIVATE cocotbutils gpilog gpi pygpilog ${Python_LIBRARIES})
    target_link_directories(simulator PRIVATE ${Python_LIBRARY_DIRS})
else()
    # For non-Windows, use the standard approach with RC manifest
    add_cocotb_library(simulator
        SOURCES ${SHARE_LIB_DIR}/simulator/simulatormodule.cpp
        LIBRARIES cocotbutils gpilog gpi pygpilog ${Python_LIBRARIES}
        RC_LIBRARIES "cocotbutils;gpilog;gpi;pygpilog"
    )
endif()

# Set simulator to be a Python extension module
set_target_properties(simulator PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb
    PREFIX ""
    SUFFIX ${PYTHON_EXT_SUFFIX}
)

# Function to add VPI libraries
function(add_vpi_library SIM_NAME SIM_DEFINE)
    set(options "")
    set(oneValueArgs "")
    set(multiValueArgs "EXTRA_LIBS" "EXTRA_LIB_DIRS")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    
    string(TOLOWER ${SIM_NAME} SIM_LOWER)
    set(TARGET_NAME cocotbvpi_${SIM_LOWER})
    
    add_cocotb_library(${TARGET_NAME}
        SOURCES
            ${SHARE_LIB_DIR}/vpi/VpiImpl.cpp
            ${SHARE_LIB_DIR}/vpi/VpiCbHdl.cpp
            ${SHARE_LIB_DIR}/vpi/VpiObj.cpp
            ${SHARE_LIB_DIR}/vpi/VpiIterator.cpp
            ${SHARE_LIB_DIR}/vpi/VpiSignal.cpp
        DEFINES COCOTBVPI_EXPORTS ${SIM_DEFINE}
        LIBRARIES gpi gpilog ${ARG_EXTRA_LIBS}
        RC_LIBRARIES "gpi;gpilog"
    )
    
    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${TARGET_NAME} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()
    
    # Special handling for Icarus Verilog extension
    if(SIM_LOWER STREQUAL "icarus")
        set_target_properties(${TARGET_NAME} PROPERTIES SUFFIX ".vpl")
    endif()
endfunction()

# Function to add VHPI libraries
function(add_vhpi_library SIM_NAME SIM_DEFINE)
    set(options "")
    set(oneValueArgs "")
    set(multiValueArgs "EXTRA_LIBS" "EXTRA_LIB_DIRS")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    
    string(TOLOWER ${SIM_NAME} SIM_LOWER)
    set(TARGET_NAME cocotbvhpi_${SIM_LOWER})
    
    add_cocotb_library(${TARGET_NAME}
        SOURCES
            ${SHARE_LIB_DIR}/vhpi/VhpiImpl.cpp
            ${SHARE_LIB_DIR}/vhpi/VhpiCbHdl.cpp
        DEFINES COCOTBVHPI_EXPORTS ${SIM_DEFINE}
        LIBRARIES gpi gpilog ${ARG_EXTRA_LIBS}
        RC_LIBRARIES "gpi;gpilog"
    )
    
    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${TARGET_NAME} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()
endfunction()

# Windows-specific: Generate import libraries first
if(WIN32)
    # Generate import libraries from DEF files
    set(DEF_DIR ${CMAKE_SOURCE_DIR}/src/cocotb/share/def)
    
    if(MSVC)
        foreach(SIM icarus modelsim aldec ghdl)
            add_custom_command(
                OUTPUT ${DEF_DIR}/${SIM}.lib
                COMMAND lib /def:${DEF_DIR}/${SIM}.def /out:${DEF_DIR}/${SIM}.lib /machine:$<IF:$<EQUAL:${CMAKE_SIZEOF_VOID_P},8>,X64,X86>
                DEPENDS ${DEF_DIR}/${SIM}.def
                COMMENT "Generating import library for ${SIM}"
            )
            add_custom_target(${SIM}_import_lib ALL DEPENDS ${DEF_DIR}/${SIM}.lib)
        endforeach()
    else()
        foreach(SIM icarus modelsim aldec ghdl)
            add_custom_command(
                OUTPUT ${DEF_DIR}/lib${SIM}.a
                COMMAND dlltool -d ${DEF_DIR}/${SIM}.def -l ${DEF_DIR}/lib${SIM}.a
                DEPENDS ${DEF_DIR}/${SIM}.def
                COMMENT "Generating import library for ${SIM}"
            )
            add_custom_target(${SIM}_import_lib ALL DEPENDS ${DEF_DIR}/lib${SIM}.a)
        endforeach()
    endif()
    
    # Create application configuration file for SxS assembly loading
    # This tells Windows to look for DLL dependencies in the libs subdirectory
    set(APPCONFIG_CONTENT "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<configuration>
    <windows>
        <assemblyBinding xmlns=\"urn:schemas-microsoft-com:asm.v1\">
            <probing privatePath=\"libs\" />
        </assemblyBinding>
    </windows>
</configuration>")
    
    file(WRITE ${CMAKE_BINARY_DIR}/cocotb/simulator.2.config "${APPCONFIG_CONTENT}")
endif()

# Build simulator-specific libraries

# Icarus Verilog
set(ICARUS_EXTRA_LIBS "")
if(WIN32)
    set(ICARUS_EXTRA_LIBS icarus)
endif()
add_vpi_library(ICARUS ICARUS EXTRA_LIBS ${ICARUS_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_icarus icarus_import_lib)
endif()

# Modelsim/Questa
set(MODELSIM_EXTRA_LIBS "")
if(WIN32)
    set(MODELSIM_EXTRA_LIBS modelsim)
endif()

add_vpi_library(MODELSIM MODELSIM EXTRA_LIBS ${MODELSIM_EXTRA_LIBS})
add_vhpi_library(MODELSIM MODELSIM EXTRA_LIBS ${MODELSIM_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_modelsim modelsim_import_lib)
    add_dependencies(cocotbvhpi_modelsim modelsim_import_lib)
endif()

# FLI for Modelsim
add_cocotb_library(cocotbfli_modelsim
    SOURCES
        ${SHARE_LIB_DIR}/fli/FliImpl.cpp
        ${SHARE_LIB_DIR}/fli/FliCbHdl.cpp
        ${SHARE_LIB_DIR}/fli/FliObjHdl.cpp
    DEFINES COCOTBFLI_EXPORTS
    LIBRARIES gpi gpilog ${MODELSIM_EXTRA_LIBS}
    RC_LIBRARIES "gpi;gpilog"
)
if(WIN32)
    add_dependencies(cocotbfli_modelsim modelsim_import_lib)
endif()

# GHDL
set(GHDL_EXTRA_LIBS "")
if(WIN32)
    set(GHDL_EXTRA_LIBS ghdl)
endif()
add_vpi_library(GHDL GHDL EXTRA_LIBS ${GHDL_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_ghdl ghdl_import_lib)
endif()

# POSIX-only simulators
if(UNIX)
    # IUS/Xcelium
    add_vpi_library(IUS IUS)
    add_vhpi_library(IUS IUS)
    
    # VCS
    add_vpi_library(VCS VCS)
    
    # Verilator
    add_vpi_library(VERILATOR VERILATOR)
    
    # NVC
    add_vhpi_library(NVC NVC)
    
    # DSim
    add_vpi_library(DSim DSim)
endif()

# Aldec Riviera Pro
set(ALDEC_EXTRA_LIBS "")
if(WIN32)
    set(ALDEC_EXTRA_LIBS aldec)
endif()
add_vpi_library(ALDEC ALDEC EXTRA_LIBS ${ALDEC_EXTRA_LIBS})
add_vhpi_library(ALDEC ALDEC EXTRA_LIBS ${ALDEC_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_aldec aldec_import_lib)
    add_dependencies(cocotbvhpi_aldec aldec_import_lib)
endif()

# Version generation logic matching setup.py
# Read version from pyproject.toml
file(READ ${CMAKE_SOURCE_DIR}/pyproject.toml PYPROJECT_CONTENT)
string(REGEX MATCH "version = \"([^\"]+)\"" VERSION_MATCH "${PYPROJECT_CONTENT}")
if(VERSION_MATCH)
    set(COCOTB_VERSION "${CMAKE_MATCH_1}")
    message(STATUS "Version from pyproject.toml: ${COCOTB_VERSION}")
else()
    # Fallback version if parsing fails
    set(COCOTB_VERSION "2.0.0.dev0")
    message(WARNING "Could not parse version from pyproject.toml, using fallback: ${COCOTB_VERSION}")
endif()

# If this is a dev version, try to append git hash like setup.py does
if(COCOTB_VERSION MATCHES "dev")
    find_package(Git QUIET)
    if(Git_FOUND)
        execute_process(
            COMMAND ${GIT_EXECUTABLE} rev-parse --short HEAD
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
            OUTPUT_VARIABLE GIT_SHORT_HASH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
            RESULT_VARIABLE GIT_RESULT
        )
        if(GIT_RESULT EQUAL 0 AND GIT_SHORT_HASH)
            set(COCOTB_VERSION "${COCOTB_VERSION}+${GIT_SHORT_HASH}")
            message(STATUS "Appended git hash to version: ${COCOTB_VERSION}")
        else()
            message(STATUS "Git hash not available, using base version: ${COCOTB_VERSION}")
        endif()
    else()
        message(STATUS "Git not found, using base version: ${COCOTB_VERSION}")
    endif()
endif()

# Generate the _version.py file (matching setup.py format)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/cocotb/_version.py
"# Package version
# Generated by setup.py -- do not modify directly

__version__ = \"${COCOTB_VERSION}\"
")

# Install rules
if(SKBUILD)
    # Install the _version.py file generated by CMake
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/cocotb/_version.py DESTINATION cocotb)
    
    install(TARGETS gpilog pygpilog cocotbutils embed gpi cocotb
            DESTINATION cocotb/libs)
    
    # Install simulator-specific libraries
    set(SIM_TARGETS 
        cocotbvpi_icarus cocotbvpi_modelsim cocotbvhpi_modelsim 
        cocotbfli_modelsim cocotbvpi_ghdl cocotbvpi_aldec cocotbvhpi_aldec)
    
    if(UNIX)
        list(APPEND SIM_TARGETS 
            cocotbvpi_ius cocotbvhpi_ius cocotbvpi_vcs 
            cocotbvpi_verilator cocotbvhpi_nvc cocotbvpi_dsim)
    endif()
    
    install(TARGETS ${SIM_TARGETS} DESTINATION cocotb/libs OPTIONAL)
    
    # Install simulator extension separately
    install(TARGETS simulator 
            RUNTIME DESTINATION cocotb
            LIBRARY DESTINATION cocotb)
    
    if(WIN32)
        install(FILES ${CMAKE_BINARY_DIR}/cocotb/simulator.2.config DESTINATION cocotb)
    endif()
endif()
