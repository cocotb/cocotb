function(cocotb_configure_native_target target_name)
    target_compile_features(${target_name} PRIVATE cxx_std_11)
    target_compile_definitions(${target_name} PRIVATE __STDC_FORMAT_MACROS)

    if(MSVC)
        target_compile_options(${target_name} PRIVATE /permissive- /W4)
    else()
        target_compile_options(${target_name} PRIVATE
            -Wall
            -Wextra
            -Wcast-qual
            -Wwrite-strings
            -Wconversion
            -Wno-missing-field-initializers
            -Werror=shadow
            -Wnon-virtual-dtor
            -Woverloaded-virtual
            -fvisibility=hidden
            -fvisibility-inlines-hidden
            -flto
        )

        if(WIN32)
            target_link_options(${target_name} PRIVATE -Wl,--exclude-all-symbols)
        else()
            target_link_options(${target_name} PRIVATE -flto)
            if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
                target_link_options(${target_name} PRIVATE -static-libstdc++)
            endif()
        endif()
    endif()

    if(WIN32)
        target_compile_definitions(${target_name} PRIVATE WIN32)
    endif()

    if(APPLE)
        set_target_properties(${target_name} PROPERTIES SUFFIX ".so")
    endif()

    if(SKBUILD_STATE STREQUAL "editable")
        set_target_properties(${target_name} PROPERTIES
            LIBRARY_OUTPUT_DIRECTORY "${COCOTB_PYTHON_PACKAGE_DIR}/libs"
            RUNTIME_OUTPUT_DIRECTORY "${COCOTB_PYTHON_PACKAGE_DIR}/libs"
        )
    endif()
endfunction()

function(cocotb_allow_undefined_symbols target_name)
    if(NOT WIN32)
        if(APPLE)
            target_link_options(${target_name} PRIVATE -undefined dynamic_lookup)
        else()
            target_link_options(${target_name} PRIVATE -Wl,--allow-shlib-undefined)
        endif()
    endif()
endfunction()
