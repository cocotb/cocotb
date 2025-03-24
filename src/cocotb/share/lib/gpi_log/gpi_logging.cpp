// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "gpi_logging.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <map>
#include <vector>

#include "cocotb_utils.h"  // DEFER

static gpi_log_handler_ftype current_handler = nullptr;
static gpi_log_filter_ftype current_filter = nullptr;
static gpi_log_set_level_ftype current_set_level = nullptr;
static void *current_userdata = nullptr;

extern "C" void gpi_log_(const char *name, int level, const char *pathname,
                         const char *funcname, long lineno, const char *msg,
                         ...) {
    va_list argp;
    va_start(argp, msg);
    gpi_vlog_(name, level, pathname, funcname, lineno, msg, argp);
    va_end(argp);
}

extern "C" void gpi_vlog_(const char *name, int level, const char *pathname,
                          const char *funcname, long lineno, const char *msg,
                          va_list argp) {
    if (current_handler) {
        (*current_handler)(current_userdata, name, level, pathname, funcname,
                           lineno, msg, argp);
    } else {
        gpi_native_logger_vlog_(name, level, pathname, funcname, lineno, msg,
                                argp);
    }
}

extern "C" void gpi_get_log_handler(gpi_log_handler_ftype *handler,
                                    gpi_log_filter_ftype *filter,
                                    gpi_log_set_level_ftype *set_level,
                                    void **userdata) {
    *handler = current_handler;
    *filter = current_filter;
    *set_level = current_set_level;
    *userdata = current_userdata;
}

extern "C" void gpi_set_log_handler(gpi_log_handler_ftype handler,
                                    gpi_log_filter_ftype filter,
                                    gpi_log_set_level_ftype set_level,
                                    void *userdata) {
    current_handler = handler;
    current_filter = filter;
    current_set_level = set_level;
    current_userdata = userdata;
}

extern "C" void gpi_clear_log_handler(void) {
    current_handler = nullptr;
    current_filter = nullptr;
    current_set_level = nullptr;
    current_userdata = nullptr;
}

extern "C" bool gpi_log_filtered(const char *logger, int level) {
    if (current_filter) {
        return current_filter(current_userdata, logger, level);
    } else {
        return gpi_native_logger_filtered(level);
    }
}

extern "C" int gpi_log_set_level(const char *logger, int level) {
    if (current_set_level) {
        return current_set_level(current_userdata, logger, level);
    } else {
        return gpi_native_logger_set_level(level);
    }
}

static const std::map<int, const char *> log_level_str_table = {
    {GPI_TRACE, "TRACE"},     {GPI_DEBUG, "DEBUG"}, {GPI_INFO, "INFO"},
    {GPI_WARNING, "WARNING"}, {GPI_ERROR, "ERROR"}, {GPI_CRITICAL, "CRITICAL"},
};

static const char *unknown_level = "------";

extern "C" const char *gpi_log_level_to_str(int level) {
    const char *log_level_str = unknown_level;
    auto idx = log_level_str_table.find(level);
    if (idx != log_level_str_table.end()) {
        log_level_str = idx->second;
    }
    return log_level_str;
}

/*******************************************************************************
 * GPI Native Logger
 *******************************************************************************/

static int current_native_logger_level = GPI_NOTSET;

extern "C" void gpi_native_logger_log_(const char *name, int level,
                                       const char *pathname,
                                       const char *funcname, long lineno,
                                       const char *msg, ...) {
    va_list argp;
    va_start(argp, msg);
    gpi_native_logger_vlog_(name, level, pathname, funcname, lineno, msg, argp);
    va_end(argp);
}

extern "C" void gpi_native_logger_vlog_(const char *name, int level,
                                        const char *pathname,
                                        const char *funcname, long lineno,
                                        const char *msg, va_list argp) {
    int curr_level = current_native_logger_level;
    if (current_native_logger_level == GPI_NOTSET) {
        curr_level = GPI_INFO;
    }
    if (level < curr_level) {
        return;
    }

    va_list argp_copy;
    va_copy(argp_copy, argp);
    DEFER(va_end(argp_copy));

    static std::vector<char> log_buff(512);

    log_buff.clear();
    int n = vsnprintf(log_buff.data(), log_buff.capacity(), msg, argp);
    if (n < 0) {
        // On Windows with the Visual C Runtime prior to 2015 the above call to
        // vsnprintf will return -1 if the buffer would overflow, rather than
        // the number of bytes that would be written as required by the C99
        // standard.
        // https://docs.microsoft.com/en-us/cpp/c-runtime-library/reference/vsnprintf-vsnprintf-vsnprintf-l-vsnwprintf-vsnwprintf-l
        // So we try the call again with the buffer NULL and the size 0, which
        // should return the number of bytes that would be written.
        va_list argp_copy_again;
        va_copy(argp_copy_again, argp_copy);
        DEFER(va_end(argp_copy_again));
        n = vsnprintf(NULL, 0, msg, argp_copy_again);
        if (n < 0) {
            // Here we know the error is for real, so we complain and move on.
            // LCOV_EXCL_START
            fprintf(stderr,
                    "Log message construction failed: (error code) %d\n", n);
            return;
            // LCOV_EXCL_STOP
        }
    }
    if ((unsigned)n >= log_buff.capacity()) {
        log_buff.reserve((unsigned)n + 1);
        n = vsnprintf(log_buff.data(), (unsigned)n + 1, msg, argp_copy);
        if (n < 0) {
            // LCOV_EXCL_START
            fprintf(stderr,
                    "Log message construction failed: (error code) %d\n", n);
            return;
            // LCOV_EXCL_STOP
        }
    }

    fprintf(stdout, "     -.--ns ");
    fprintf(stdout, "%-9s", gpi_log_level_to_str(level));
    fprintf(stdout, "%-35s", name);

    size_t pathlen = strlen(pathname);
    if (pathlen > 20) {
        fprintf(stdout, "..%18s:", (pathname + (pathlen - 18)));
    } else {
        fprintf(stdout, "%20s:", pathname);
    }

    fprintf(stdout, "%-4ld", lineno);
    fprintf(stdout, " in %-31s ", funcname);
    fprintf(stdout, "%s", log_buff.data());
    fprintf(stdout, "\n");
    fflush(stdout);
}

extern "C" int gpi_native_logger_set_level(int level) {
    int old_level = current_native_logger_level;
    current_native_logger_level = level;
    return old_level;
}

extern "C" bool gpi_native_logger_filtered(int level) {
    return level >= current_native_logger_level;
}
