set(COCOTB_GPI_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include")
set(COCOTB_GPI_COMMON_DIR "${CMAKE_CURRENT_SOURCE_DIR}/common")
set(COCOTB_GPI_CORE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/core")
set(COCOTB_GPI_DEF_DIR "${CMAKE_CURRENT_SOURCE_DIR}/def")

set(COCOTB_GPI_LINK_LIBRARIES "")
if(UNIX)
    list(APPEND COCOTB_GPI_LINK_LIBRARIES dl)
endif()

function(cocotb_configure_gpi_target target_name)
    cocotb_configure_native_target(${target_name})
    target_include_directories(${target_name} PRIVATE
        "${COCOTB_GPI_INCLUDE_DIR}"
        "${COCOTB_GPI_COMMON_DIR}"
        "${COCOTB_GPI_CORE_DIR}"
        "${CMAKE_CURRENT_SOURCE_DIR}"
    )
endfunction()

add_library(cocotb_bootstrap SHARED
    common/dynload.cpp
    bootstrap/bootstrapper.cpp
)
add_library(cocotb::bootstrap ALIAS cocotb_bootstrap)
set_target_properties(cocotb_bootstrap PROPERTIES EXPORT_NAME bootstrap)
cocotb_configure_gpi_target(cocotb_bootstrap)
target_link_libraries(cocotb_bootstrap PRIVATE ${COCOTB_GPI_LINK_LIBRARIES})

add_library(gpi SHARED
    core/GpiCbHdl.cpp
    core/GpiCommon.cpp
    common/dynload.cpp
    core/logging.cpp
)
add_library(cocotb::gpi ALIAS gpi)
set_target_properties(gpi PROPERTIES EXPORT_NAME gpi)
cocotb_configure_gpi_target(gpi)
target_compile_features(gpi PUBLIC cxx_std_11)
target_include_directories(gpi PUBLIC
    "$<BUILD_INTERFACE:${COCOTB_GPI_INCLUDE_DIR}>"
    "$<INSTALL_INTERFACE:${COCOTB_INSTALL_INCLUDE_DIR}>"
)
target_compile_definitions(gpi PRIVATE GPI_EXPORTS)
target_link_libraries(gpi PRIVATE ${COCOTB_GPI_LINK_LIBRARIES})

function(cocotb_add_vpi_library simulator_name simulator_define)
    set(options "")
    set(one_value_args "")
    set(multi_value_args EXTRA_LIBS EXTRA_LIB_DIRS)
    cmake_parse_arguments(ARG "${options}" "${one_value_args}" "${multi_value_args}" ${ARGN})

    string(TOLOWER "${simulator_name}" simulator_lower)
    set(target_name "gpi_impl_${simulator_lower}_vpi")

    add_library(${target_name} SHARED
        vpi/VpiImpl.cpp
        vpi/VpiCbHdl.cpp
        vpi/VpiObj.cpp
        vpi/VpiIterator.cpp
        vpi/VpiSignal.cpp
    )
    cocotb_configure_gpi_target(${target_name})
    target_compile_definitions(${target_name} PRIVATE
        COCOTBVPI_EXPORTS
        "GPI_IMPL_ENTRY=gpi_impl_${simulator_lower}_vpi_entry"
        "${simulator_define}"
    )
    target_link_libraries(${target_name} PRIVATE gpi ${ARG_EXTRA_LIBS})

    if(WIN32)
        target_link_directories(${target_name} PRIVATE "${COCOTB_GPI_DEF_DIR}")
    endif()
    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${target_name} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()

    cocotb_allow_undefined_symbols(${target_name})
endfunction()

function(cocotb_add_vhpi_library simulator_name simulator_define)
    set(options "")
    set(one_value_args "")
    set(multi_value_args EXTRA_LIBS EXTRA_LIB_DIRS)
    cmake_parse_arguments(ARG "${options}" "${one_value_args}" "${multi_value_args}" ${ARGN})

    string(TOLOWER "${simulator_name}" simulator_lower)
    set(target_name "gpi_impl_${simulator_lower}_vhpi")

    add_library(${target_name} SHARED
        vhpi/VhpiImpl.cpp
        vhpi/VhpiCbHdl.cpp
        vhpi/VhpiObj.cpp
        vhpi/VhpiIterator.cpp
        vhpi/VhpiSignal.cpp
    )
    cocotb_configure_gpi_target(${target_name})
    target_compile_definitions(${target_name} PRIVATE
        COCOTBVHPI_EXPORTS
        "GPI_IMPL_ENTRY=gpi_impl_${simulator_lower}_vhpi_entry"
        "${simulator_define}"
    )
    target_link_libraries(${target_name} PRIVATE gpi ${ARG_EXTRA_LIBS})

    if(WIN32)
        target_link_directories(${target_name} PRIVATE "${COCOTB_GPI_DEF_DIR}")
    endif()
    if(ARG_EXTRA_LIB_DIRS)
        target_link_directories(${target_name} PRIVATE ${ARG_EXTRA_LIB_DIRS})
    endif()

    cocotb_allow_undefined_symbols(${target_name})
endfunction()

set(ICARUS_EXTRA_LIBS "")
if(WIN32)
    set(ICARUS_EXTRA_LIBS icarus)
endif()
cocotb_add_vpi_library(ICARUS ICARUS EXTRA_LIBS ${ICARUS_EXTRA_LIBS})

set(MODELSIM_EXTRA_LIBS "")
if(WIN32)
    set(MODELSIM_EXTRA_LIBS modelsim)
endif()
cocotb_add_vpi_library(MODELSIM MODELSIM EXTRA_LIBS ${MODELSIM_EXTRA_LIBS})
cocotb_add_vhpi_library(MODELSIM MODELSIM EXTRA_LIBS ${MODELSIM_EXTRA_LIBS})

add_library(gpi_impl_modelsim_fli SHARED
    fli/FliImpl.cpp
    fli/FliCbHdl.cpp
    fli/FliObjHdl.cpp
)
cocotb_configure_gpi_target(gpi_impl_modelsim_fli)
target_compile_definitions(gpi_impl_modelsim_fli PRIVATE
    COCOTBFLI_EXPORTS
    GPI_IMPL_ENTRY=gpi_impl_modelsim_fli_entry
)
target_link_libraries(gpi_impl_modelsim_fli PRIVATE gpi ${MODELSIM_EXTRA_LIBS})
if(WIN32)
    target_link_directories(gpi_impl_modelsim_fli PRIVATE "${COCOTB_GPI_DEF_DIR}")
endif()
cocotb_allow_undefined_symbols(gpi_impl_modelsim_fli)

set(GHDL_EXTRA_LIBS "")
if(WIN32)
    set(GHDL_EXTRA_LIBS ghdl)
endif()
cocotb_add_vpi_library(GHDL GHDL EXTRA_LIBS ${GHDL_EXTRA_LIBS})

if(UNIX)
    cocotb_add_vpi_library(IUS IUS)
    cocotb_add_vhpi_library(IUS IUS)
    cocotb_add_vpi_library(VCS VCS)
    cocotb_add_vpi_library(VERILATOR VERILATOR)
    cocotb_add_vpi_library(DSim DSim)
endif()

set(NVC_EXTRA_LIBS "")
if(WIN32)
    set(NVC_EXTRA_LIBS nvcvhpi)
endif()
cocotb_add_vhpi_library(NVC NVC EXTRA_LIBS ${NVC_EXTRA_LIBS})

set(ALDEC_EXTRA_LIBS "")
if(WIN32)
    set(ALDEC_EXTRA_LIBS aldec)
endif()
cocotb_add_vpi_library(ALDEC ALDEC EXTRA_LIBS ${ALDEC_EXTRA_LIBS})
cocotb_add_vhpi_library(ALDEC ALDEC EXTRA_LIBS ${ALDEC_EXTRA_LIBS})

if(WIN32)
    if(MSVC)
        foreach(simulator icarus modelsim aldec ghdl nvcvhpi)
            add_custom_command(
                OUTPUT "${COCOTB_GPI_DEF_DIR}/${simulator}.lib"
                COMMAND lib /def:${COCOTB_GPI_DEF_DIR}/${simulator}.def /out:${COCOTB_GPI_DEF_DIR}/${simulator}.lib /machine:$<IF:$<EQUAL:${CMAKE_SIZEOF_VOID_P},8>,X64,X86>
                DEPENDS "${COCOTB_GPI_DEF_DIR}/${simulator}.def"
                COMMENT "Generating import library for ${simulator}"
            )
        endforeach()
    else()
        foreach(simulator icarus modelsim aldec ghdl nvcvhpi)
            add_custom_command(
                OUTPUT "${COCOTB_GPI_DEF_DIR}/lib${simulator}.a"
                COMMAND dlltool -d "${COCOTB_GPI_DEF_DIR}/${simulator}.def" -l "${COCOTB_GPI_DEF_DIR}/lib${simulator}.a"
                DEPENDS "${COCOTB_GPI_DEF_DIR}/${simulator}.def"
                COMMENT "Generating import library for ${simulator}"
            )
        endforeach()
    endif()

    foreach(simulator icarus modelsim aldec ghdl nvcvhpi)
        if(MSVC)
            set(import_library "${COCOTB_GPI_DEF_DIR}/${simulator}.lib")
        else()
            set(import_library "${COCOTB_GPI_DEF_DIR}/lib${simulator}.a")
        endif()
        add_custom_target(${simulator}_import_lib ALL DEPENDS "${import_library}")
    endforeach()

    add_dependencies(gpi_impl_icarus_vpi icarus_import_lib)
    add_dependencies(gpi_impl_modelsim_vpi modelsim_import_lib)
    add_dependencies(gpi_impl_modelsim_vhpi modelsim_import_lib)
    add_dependencies(gpi_impl_modelsim_fli modelsim_import_lib)
    add_dependencies(gpi_impl_ghdl_vpi ghdl_import_lib)
    add_dependencies(gpi_impl_nvc_vhpi nvcvhpi_import_lib)
    add_dependencies(gpi_impl_aldec_vpi aldec_import_lib)
    add_dependencies(gpi_impl_aldec_vhpi aldec_import_lib)
endif()

if(COCOTB_INSTALL_ARTIFACTS)
    install(
        TARGETS cocotb_bootstrap gpi
        EXPORT cocotbTargets
        RUNTIME DESTINATION "${COCOTB_INSTALL_LIBRARY_DIR}"
        LIBRARY DESTINATION "${COCOTB_INSTALL_LIBRARY_DIR}"
        ARCHIVE DESTINATION "${COCOTB_INSTALL_LIBRARY_DIR}"
    )
    install(DIRECTORY include/ DESTINATION "${COCOTB_INSTALL_INCLUDE_DIR}")

    set(COCOTB_SIMULATOR_TARGETS
        gpi_impl_icarus_vpi
        gpi_impl_modelsim_vpi
        gpi_impl_modelsim_vhpi
        gpi_impl_modelsim_fli
        gpi_impl_ghdl_vpi
        gpi_impl_aldec_vpi
        gpi_impl_aldec_vhpi
        gpi_impl_nvc_vhpi
    )
    if(UNIX)
        list(APPEND COCOTB_SIMULATOR_TARGETS
            gpi_impl_ius_vpi
            gpi_impl_ius_vhpi
            gpi_impl_vcs_vpi
            gpi_impl_verilator_vpi
            gpi_impl_dsim_vpi
        )
    endif()
    install(
        TARGETS ${COCOTB_SIMULATOR_TARGETS}
        RUNTIME DESTINATION "${COCOTB_INSTALL_LIBRARY_DIR}"
        LIBRARY DESTINATION "${COCOTB_INSTALL_LIBRARY_DIR}"
        OPTIONAL
    )
endif()
