// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <exports.h>

#include <cstdio>
#include <cstdlib>
#include <string>

#include "./dynload.hpp"

#ifdef _WIN32
static const char entry_separator = ';';
#else
static const char entry_separator = ':';
#endif
static const char entry_point_separator = ',';

typedef int (*bootstrap_entry_func)();

static int load_bootstrap() {
    const char *bootstrap_env = getenv("COCOTB_BOOTSTRAP");
    if (!bootstrap_env || !bootstrap_env[0]) {
        fprintf(stderr, "[%s:%d]: COCOTB_BOOTSTRAP is not set or is empty\n",
                __FILE__, __LINE__);
        return -1;
    }

    std::string entries = bootstrap_env;
    std::string::size_type start = 0;
    while (start <= entries.size()) {
        const auto next_separator = entries.find(entry_separator, start);
        const auto end = next_separator == std::string::npos ? entries.size()
                                                             : next_separator;
        const std::string entry = entries.substr(start, end - start);
        if (entry.empty()) {
            fprintf(stderr, "[%s:%d]: Empty entry in COCOTB_BOOTSTRAP '%s'\n",
                    __FILE__, __LINE__, bootstrap_env);
            return -1;
        }

        const auto function_separator = entry.rfind(entry_point_separator);
        const bool has_entry_point = function_separator != std::string::npos;
        const std::string library =
            has_entry_point ? entry.substr(0, function_separator) : entry;
        const std::string function =
            has_entry_point ? entry.substr(function_separator + 1) : "";
        if (library.empty() || (has_entry_point && function.empty())) {
            fprintf(stderr, "[%s:%d]: Invalid entry '%s' in COCOTB_BOOTSTRAP\n",
                    __FILE__, __LINE__, entry.c_str());
            return -1;
        }

        void *library_handle = utils_dyn_open(library.c_str());
        if (!library_handle) {
            fprintf(stderr, "[%s:%d]: Unable to load library '%s'\n", __FILE__,
                    __LINE__, library.c_str());
            return -1;
        }

        if (has_entry_point) {
            void *function_handle =
                utils_dyn_sym(library_handle, function.c_str());
            if (!function_handle) {
                fprintf(stderr,
                        "[%s:%d]: Unable to find entry point '%s' in library "
                        "'%s'\n",
                        __FILE__, __LINE__, function.c_str(), library.c_str());
                return -1;
            }

            auto entry_func =
                reinterpret_cast<bootstrap_entry_func>(function_handle);
            const int result = entry_func();
            if (result < 0) {
                fprintf(stderr,
                        "[%s:%d]: Entry point '%s' in library '%s' failed\n",
                        __FILE__, __LINE__, function.c_str(), library.c_str());
                return -1;
            }
            if (result > 0) {
                return 0;
            }
        }

        if (next_separator == std::string::npos) {
            break;
        }
        start = next_separator + 1;
    }

    return 0;
}

extern "C" {

COCOTB_EXPORT void cocotb_bootstrap_entry() {
    if (load_bootstrap() < 0) {
        exit(EXIT_FAILURE);
    }
}

// VPI: Verilog simulators call vlog_startup_routines[].
COCOTB_EXPORT void (*vlog_startup_routines[])() = {cocotb_bootstrap_entry,
                                                   nullptr};

// VHPI: VHDL simulators call vhpi_startup_routines[].
COCOTB_EXPORT void (*vhpi_startup_routines[])() = {cocotb_bootstrap_entry,
                                                   nullptr};
}
