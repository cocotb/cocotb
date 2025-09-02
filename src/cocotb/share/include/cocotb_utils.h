// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_UTILS_H_
#define COCOTB_UTILS_H_

#include <exports.h>
#ifdef COCOTBUTILS_EXPORTS
#define COCOTBUTILS_EXPORT COCOTB_EXPORT
#else
#define COCOTBUTILS_EXPORT COCOTB_IMPORT
#endif

#include <gpi_logging.h>

#define xstr(a) str(a)
#define str(a) #a

extern "C" COCOTBUTILS_EXPORT void *utils_dyn_open(const char *lib_name);
extern "C" COCOTBUTILS_EXPORT void *utils_dyn_sym(void *handle,
                                                  const char *sym_name);
extern "C" COCOTBUTILS_EXPORT int is_python_context;

// to_python and to_simulator are implemented as macros instead of functions so
// that the logs reference the user's lineno and filename

#define to_python()                                      \
    do {                                                 \
        if (is_python_context) {                         \
            LOG_ERROR("FATAL: We are calling up again"); \
            exit(1);                                     \
        }                                                \
        ++is_python_context;                             \
        LOG_TRACE("Returning to Python");                \
    } while (0)

#define to_simulator()                                              \
    do {                                                            \
        if (!is_python_context) {                                   \
            LOG_ERROR("FATAL: We have returned twice from Python"); \
            exit(1);                                                \
        }                                                           \
        --is_python_context;                                        \
        LOG_TRACE("Returning to simulator");                        \
    } while (0)

template <typename F>
class Deferable {
  public:
    constexpr Deferable(F f) : f_(f) {};
    ~Deferable() { f_(); }

  private:
    F f_;
};

template <typename F>
constexpr Deferable<F> make_deferable(F f) {
    return Deferable<F>(f);
}

#define DEFER1(a, b) a##b
#define DEFER0(a, b) DEFER1(a, b)
#define DEFER(statement) \
    auto DEFER0(_defer, __COUNTER__) = make_deferable([&]() { statement; });

#endif /* COCOTB_UTILS_H_ */
