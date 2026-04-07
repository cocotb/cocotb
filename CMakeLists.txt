cmake_minimum_required(VERSION 3.15)

# Clear problematic environment variables before project() command
# This prevents CMake from picking up GCC-style flags for MSVC
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

project(cocotb LANGUAGES CXX)

if(MSVC)
    message(STATUS "MSVC detected - using forced MSVC-compatible flags")
    message(STATUS "CMAKE_CXX_FLAGS: ${CMAKE_CXX_FLAGS}")
endif()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module Development.Embed)

if(WIN32)
    set(LIB_EXT "dll")
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
else()
    set(LIB_EXT "so")
    if(APPLE)
        set(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
    endif()
endif()

if(MSVC)
    set(EXTRA_CXX_FLAGS "/permissive-" "/W4")
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

    if(WIN32)
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,--exclude-all-symbols")
    else()
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -flto")

        if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
            set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static-libstdc++")
        endif()
    endif()
endif()

set(EXTRA_DEFINES "__STDC_FORMAT_MACROS")

set(INCLUDE_DIRS
    ${CMAKE_SOURCE_DIR}/src/cocotb/share/include
    ${CMAKE_SOURCE_DIR}/src/cocotb
    ${Python_INCLUDE_DIRS}
)

set(SHARE_LIB_DIR ${CMAKE_SOURCE_DIR}/src/cocotb/share/lib)

# Match cocotb_build_libs.py: dl on linux, darwin, cygwin, msys
set(GPI_EXTRA_LIBS "")
if(UNIX OR CYGWIN)
    list(APPEND GPI_EXTRA_LIBS dl)
elseif(CMAKE_SYSTEM_NAME STREQUAL "MSYS")
    list(APPEND GPI_EXTRA_LIBS dl)
endif()

if(WIN32)
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

    function(create_rc_file RC_FILENAME NAME FILENAME LIBRARIES RUNTIME_LIBRARIES)
        create_sxs_assembly_manifest(${NAME} ${FILENAME} "${LIBRARIES}" FALSE MANIFEST)

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

function(add_cocotb_library TARGET_NAME)
    set(options "")
    set(oneValueArgs "OUTPUT_NAME")
    set(multiValueArgs "SOURCES" "LIBRARIES" "DEFINES" "RC_LIBRARIES" "RC_RUNTIME_LIBRARIES")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(ALL_SOURCES ${ARG_SOURCES})
    if(WIN32)
        set(RC_FILENAME "${CMAKE_CURRENT_BINARY_DIR}/${TARGET_NAME}.rc")
        set(LIB_NAME ${ARG_OUTPUT_NAME})
        if(NOT LIB_NAME)
            set(LIB_NAME ${TARGET_NAME})
        endif()

        if(MSVC AND LIB_NAME MATCHES "^lib(.+)")
            string(REGEX REPLACE "^lib" "" LIB_NAME ${LIB_NAME})
        endif()

        set(RC_LIBS ${ARG_RC_LIBRARIES})
        if(MSVC)
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

    add_library(${TARGET_NAME} SHARED ${ALL_SOURCES})

    if(ARG_OUTPUT_NAME)
        set_target_properties(${TARGET_NAME} PROPERTIES OUTPUT_NAME ${ARG_OUTPUT_NAME})
    endif()

    target_include_directories(${TARGET_NAME} PRIVATE ${INCLUDE_DIRS})

    target_compile_definitions(${TARGET_NAME} PRIVATE ${ARG_DEFINES} ${EXTRA_DEFINES})

    target_compile_options(${TARGET_NAME} PRIVATE ${EXTRA_CXX_FLAGS})

    if(ARG_LIBRARIES)
        target_link_libraries(${TARGET_NAME} PRIVATE ${ARG_LIBRARIES})
    endif()

    if(WIN32)
        target_compile_definitions(${TARGET_NAME} PRIVATE WIN32)
        if(${TARGET_NAME} MATCHES "^cocotbvpi_(icarus|modelsim|aldec|ghdl)$"
                OR ${TARGET_NAME} MATCHES "^cocotbvhpi_(modelsim|aldec|nvc)$"
                OR ${TARGET_NAME} STREQUAL "cocotbfli_modelsim")
            target_link_directories(${TARGET_NAME} PRIVATE ${CMAKE_SOURCE_DIR}/src/cocotb/share/def)
        endif()
    endif()

    if(NOT WIN32)
        if(${TARGET_NAME} STREQUAL "simulator")
            if(APPLE)
                set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_RPATH "@loader_path/libs")
            else()
                set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN/libs")
            endif()
        else()
            if(APPLE)
                set_target_properties(${TARGET_NAME} PROPERTIES
                    INSTALL_RPATH "@loader_path"
                    INSTALL_NAME_DIR "@rpath"
                )
                set_target_properties(${TARGET_NAME} PROPERTIES
                    LINK_FLAGS "-Wl,-install_name,@rpath/lib${TARGET_NAME}.so"
                )
            else()
                set_target_properties(${TARGET_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN")
            endif()
        endif()
    endif()

    set_target_properties(${TARGET_NAME} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb/libs
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb/libs
    )
endfunction()

# --- libgpi (cocotb_build_libs _get_common_lib_ext) ---
add_cocotb_library(gpi
    SOURCES
        ${SHARE_LIB_DIR}/gpi/GpiCbHdl.cpp
        ${SHARE_LIB_DIR}/gpi/GpiCommon.cpp
        ${SHARE_LIB_DIR}/gpi/dynload.cpp
        ${SHARE_LIB_DIR}/gpi/logging.cpp
    DEFINES GPI_EXPORTS
    LIBRARIES ${GPI_EXTRA_LIBS}
    RC_LIBRARIES ""
)

# --- PyGPI Python extension (output name: simulator) ---
if(WIN32)
    set(PYTHON_EXT_SUFFIX ".${Python_SOABI}.pyd")
else()
    set(PYTHON_EXT_SUFFIX ".${Python_SOABI}${CMAKE_SHARED_LIBRARY_SUFFIX}")
endif()

add_cocotb_library(simulator
    SOURCES
        ${SHARE_LIB_DIR}/pygpi/bind.cpp
        ${SHARE_LIB_DIR}/pygpi/embed.cpp
        ${SHARE_LIB_DIR}/pygpi/logging.cpp
    DEFINES PYGPI_EXPORTS
    LIBRARIES gpi ${Python_LIBRARIES}
    RC_LIBRARIES "gpi"
)
if(WIN32)
    target_link_directories(simulator PRIVATE ${Python_LIBRARY_DIRS})
endif()
if(APPLE AND Python_LIBRARY)
    get_filename_component(PYTHON_MACOS_LIBDIR "${Python_LIBRARY}" DIRECTORY)
    target_link_directories(simulator PRIVATE "${PYTHON_MACOS_LIBDIR}")
endif()

set_target_properties(simulator PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/cocotb
    PREFIX ""
    SUFFIX ${PYTHON_EXT_SUFFIX}
)

function(add_vpi_library SIM_NAME SIM_DEFINE)
    set(options "")
    set(oneValueArgs "")
    set(multiValueArgs "EXTRA_LIBS" "EXTRA_LIB_DIRS")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    string(TOLOWER ${SIM_NAME} SIM_LOWER)
    set(TARGET_NAME cocotbvpi_${SIM_LOWER})

    add_cocotb_library(${TARGET_NAME}
        SOURCES
            ${SHARE_LIB_DIR}/gpi/vpi/VpiImpl.cpp
            ${SHARE_LIB_DIR}/gpi/vpi/VpiCbHdl.cpp
            ${SHARE_LIB_DIR}/gpi/vpi/VpiObj.cpp
            ${SHARE_LIB_DIR}/gpi/vpi/VpiIterator.cpp
            ${SHARE_LIB_DIR}/gpi/vpi/VpiSignal.cpp
        DEFINES COCOTBVPI_EXPORTS ${SIM_DEFINE}
        LIBRARIES gpi ${ARG_EXTRA_LIBS}
        RC_LIBRARIES "gpi"
    )

    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${TARGET_NAME} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()

    if(NOT WIN32)
        if(APPLE)
            target_link_options(${TARGET_NAME} PRIVATE -undefined dynamic_lookup)
        else()
            target_link_options(${TARGET_NAME} PRIVATE -Wl,--allow-shlib-undefined)
        endif()
    endif()

    if(SIM_LOWER STREQUAL "icarus")
        set_target_properties(${TARGET_NAME} PROPERTIES SUFFIX ".vpl")
    endif()
endfunction()

function(add_vhpi_library SIM_NAME SIM_DEFINE)
    set(options "")
    set(oneValueArgs "")
    set(multiValueArgs "EXTRA_LIBS" "EXTRA_LIB_DIRS")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    string(TOLOWER ${SIM_NAME} SIM_LOWER)
    set(TARGET_NAME cocotbvhpi_${SIM_LOWER})

    add_cocotb_library(${TARGET_NAME}
        SOURCES
            ${SHARE_LIB_DIR}/gpi/vhpi/VhpiImpl.cpp
            ${SHARE_LIB_DIR}/gpi/vhpi/VhpiCbHdl.cpp
            ${SHARE_LIB_DIR}/gpi/vhpi/VhpiObj.cpp
            ${SHARE_LIB_DIR}/gpi/vhpi/VhpiIterator.cpp
            ${SHARE_LIB_DIR}/gpi/vhpi/VhpiSignal.cpp
        DEFINES COCOTBVHPI_EXPORTS ${SIM_DEFINE}
        LIBRARIES gpi ${ARG_EXTRA_LIBS}
        RC_LIBRARIES "gpi"
    )

    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${TARGET_NAME} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()

    if(NOT WIN32)
        if(APPLE)
            target_link_options(${TARGET_NAME} PRIVATE -undefined dynamic_lookup)
        else()
            target_link_options(${TARGET_NAME} PRIVATE -Wl,--allow-shlib-undefined)
        endif()
    endif()
endfunction()

if(WIN32)
    set(DEF_DIR ${CMAKE_SOURCE_DIR}/src/cocotb/share/def)

    if(MSVC)
        foreach(SIM icarus modelsim aldec ghdl nvcvhpi)
            add_custom_command(
                OUTPUT ${DEF_DIR}/${SIM}.lib
                COMMAND lib /def:${DEF_DIR}/${SIM}.def /out:${DEF_DIR}/${SIM}.lib /machine:$<IF:$<EQUAL:${CMAKE_SIZEOF_VOID_P},8>,X64,X86>
                DEPENDS ${DEF_DIR}/${SIM}.def
                COMMENT "Generating import library for ${SIM}"
            )
            add_custom_target(${SIM}_import_lib ALL DEPENDS ${DEF_DIR}/${SIM}.lib)
        endforeach()
    else()
        foreach(SIM icarus modelsim aldec ghdl nvcvhpi)
            add_custom_command(
                OUTPUT ${DEF_DIR}/lib${SIM}.a
                COMMAND dlltool -d ${DEF_DIR}/${SIM}.def -l ${DEF_DIR}/lib${SIM}.a
                DEPENDS ${DEF_DIR}/${SIM}.def
                COMMENT "Generating import library for ${SIM}"
            )
            add_custom_target(${SIM}_import_lib ALL DEPENDS ${DEF_DIR}/lib${SIM}.a)
        endforeach()
    endif()

    set(APPCONFIG_CONTENT "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<configuration>
    <windows>
        <assemblyBinding xmlns=\"urn:schemas-microsoft-com:asm.v1\">
            <probing privatePath=\"libs\" />
        </assemblyBinding>
    </windows>
</configuration>")

    file(WRITE ${CMAKE_BINARY_DIR}/cocotb/simulator.2.config "${APPCONFIG_CONTENT}")

    get_filename_component(SIMULATOR_NAME ${CMAKE_BINARY_DIR}/cocotb/simulator.cp311-win_amd64.pyd NAME_WLE)
    file(WRITE ${CMAKE_BINARY_DIR}/cocotb/${SIMULATOR_NAME}.pyd.2.config "${APPCONFIG_CONTENT}")
endif()

set(ICARUS_EXTRA_LIBS "")
if(WIN32)
    set(ICARUS_EXTRA_LIBS icarus)
endif()
add_vpi_library(ICARUS ICARUS EXTRA_LIBS ${ICARUS_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_icarus icarus_import_lib)
endif()

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

add_cocotb_library(cocotbfli_modelsim
    SOURCES
        ${SHARE_LIB_DIR}/gpi/fli/FliImpl.cpp
        ${SHARE_LIB_DIR}/gpi/fli/FliCbHdl.cpp
        ${SHARE_LIB_DIR}/gpi/fli/FliObjHdl.cpp
    DEFINES COCOTBFLI_EXPORTS
    LIBRARIES gpi ${MODELSIM_EXTRA_LIBS}
    RC_LIBRARIES "gpi"
)
if(WIN32)
    add_dependencies(cocotbfli_modelsim modelsim_import_lib)
else()
    if(APPLE)
        target_link_options(cocotbfli_modelsim PRIVATE -undefined dynamic_lookup)
    else()
        target_link_options(cocotbfli_modelsim PRIVATE -Wl,--allow-shlib-undefined)
    endif()
endif()

set(GHDL_EXTRA_LIBS "")
if(WIN32)
    set(GHDL_EXTRA_LIBS ghdl)
endif()
add_vpi_library(GHDL GHDL EXTRA_LIBS ${GHDL_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvpi_ghdl ghdl_import_lib)
endif()

if(UNIX AND NOT WIN32)
    add_vpi_library(IUS IUS)
    add_vhpi_library(IUS IUS)

    add_vpi_library(VCS VCS)

    add_vpi_library(VERILATOR VERILATOR)

    add_vpi_library(DSim DSim)
endif()

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

set(NVC_EXTRA_LIBS "")
if(WIN32)
    set(NVC_EXTRA_LIBS nvcvhpi)
endif()
add_vhpi_library(NVC NVC EXTRA_LIBS ${NVC_EXTRA_LIBS})
if(WIN32)
    add_dependencies(cocotbvhpi_nvc nvcvhpi_import_lib)
endif()

set(COCOTB_VERSION "${SKBUILD_PROJECT_VERSION_FULL}")

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

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/cocotb/_version.py
"# Package version
# Generated by setup -- do not modify directly

__version__ = \"${COCOTB_VERSION}\"
")

if(SKBUILD)
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/cocotb/_version.py DESTINATION cocotb)

    install(TARGETS gpi DESTINATION cocotb/libs)

    install(TARGETS
        cocotbvpi_icarus cocotbvpi_modelsim cocotbvhpi_modelsim
        cocotbfli_modelsim cocotbvpi_ghdl cocotbvpi_aldec cocotbvhpi_aldec
        cocotbvhpi_nvc
        DESTINATION cocotb/libs)

    if(UNIX AND NOT WIN32)
        install(TARGETS
            cocotbvpi_ius cocotbvhpi_ius cocotbvpi_vcs
            cocotbvpi_verilator cocotbvpi_dsim
            DESTINATION cocotb/libs)
    endif()

    install(TARGETS simulator
            RUNTIME DESTINATION cocotb
            LIBRARY DESTINATION cocotb)

    if(WIN32)
        install(FILES ${CMAKE_BINARY_DIR}/cocotb/simulator.2.config DESTINATION cocotb)
        file(GLOB PYD_CONFIG_FILES ${CMAKE_BINARY_DIR}/cocotb/*.pyd.2.config)
        if(PYD_CONFIG_FILES)
            install(FILES ${PYD_CONFIG_FILES} DESTINATION cocotb)
        endif()
    endif()
endif()
