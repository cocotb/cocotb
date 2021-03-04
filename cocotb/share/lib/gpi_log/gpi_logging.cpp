/******************************************************************************
 * Copyright (c) 2013 Potential Ventures Ltd
 * Copyright (c) 2013 SolarFlare Communications Inc
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *    * Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *    * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *    * Neither the name of Potential Ventures Ltd,
 *       SolarFlare Communications Inc nor the
 *      names of its contributors may be used to endorse or promote products
 *      derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 *AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 *IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#include <gpi_logging.h>

#include <cstdarg>
#include <cstdio>
#include <cstring>

static gpi_log_handler_type *current_handler = nullptr;
static void *current_userdata = nullptr;

extern "C" void gpi_log(const char *name, int level, const char *pathname,
                        const char *funcname, long lineno, const char *msg,
                        ...) {
    va_list argp;
    va_start(argp, msg);
    gpi_vlog(name, level, pathname, funcname, lineno, msg, argp);
    va_end(argp);
}

extern "C" void gpi_vlog(const char *name, int level, const char *pathname,
                         const char *funcname, long lineno, const char *msg,
                         va_list argp) {
    if (current_handler) {
        (*current_handler)(current_userdata, name, level, pathname, funcname,
                           lineno, msg, argp);
    } else {
        gpi_native_logger_vlog(name, level, pathname, funcname, lineno, msg,
                               argp);
    }
}

extern "C" void gpi_get_log_handler(gpi_log_handler_type **handler,
                                    void **userdata) {
    *handler = current_handler;
    *userdata = current_userdata;
}

extern "C" void gpi_set_log_handler(gpi_log_handler_type *handler,
                                    void *userdata) {
    current_handler = handler;
    current_userdata = userdata;
}

extern "C" void gpi_clear_log_handler(void) {
    current_handler = nullptr;
    current_userdata = nullptr;
}

static int current_native_logger_level = GPIInfo;

extern "C" void gpi_native_logger_log(const char *name, int level,
                                      const char *pathname,
                                      const char *funcname, long lineno,
                                      const char *msg, ...) {
    va_list argp;
    va_start(argp, msg);
    gpi_native_logger_vlog(name, level, pathname, funcname, lineno, msg, argp);
    va_end(argp);
}

// Decode the level into a string matching the Python interpretation
struct _log_level_table {
    long level;
    const char *levelname;
};

static struct _log_level_table log_level_table[] = {
    {10, "DEBUG"}, {20, "INFO"},     {30, "WARNING"},
    {40, "ERROR"}, {50, "CRITICAL"}, {0, NULL}};

const char *log_level(long level) {
    struct _log_level_table *p;
    const char *str = "------";

    for (p = log_level_table; p->levelname; p++) {
        if (level == p->level) {
            str = p->levelname;
            break;
        }
    }
    return str;
}

// We keep this module global to avoid reallocation
// we do not need to worry about locking here as
// are single threaded and can not have multiple calls
// into gpi_log at once.
#define LOG_SIZE 512
static char log_buff[LOG_SIZE];

extern "C" void gpi_native_logger_vlog(const char *name, int level,
                                       const char *pathname,
                                       const char *funcname, long lineno,
                                       const char *msg, va_list argp) {
    if (level < current_native_logger_level) {
        return;
    }

    int n = vsnprintf(log_buff, LOG_SIZE, msg, argp);

    if (n < 0 || n >= LOG_SIZE) {
        fprintf(stderr, "Log message construction failed\n");
    }

    fprintf(stdout, "     -.--ns ");
    fprintf(stdout, "%-9s", log_level(level));
    fprintf(stdout, "%-35s", name);

    size_t pathlen = strlen(pathname);
    if (pathlen > 20) {
        fprintf(stdout, "..%18s:", (pathname + (pathlen - 18)));
    } else {
        fprintf(stdout, "%20s:", pathname);
    }

    fprintf(stdout, "%-4ld", lineno);
    fprintf(stdout, " in %-31s ", funcname);
    fprintf(stdout, "%s", log_buff);
    fprintf(stdout, "\n");
    fflush(stdout);
}

extern "C" int gpi_native_logger_set_level(int level) {
    int old_level = current_native_logger_level;
    current_native_logger_level = level;
    return old_level;
}
