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
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#ifndef COCOTB_GPI_LOGGING_H_
#define COCOTB_GPI_LOGGING_H_

#include <exports.h>
#ifdef GPILOG_EXPORTS
#define GPILOG_EXPORT COCOTB_EXPORT
#else
#define GPILOG_EXPORT COCOTB_IMPORT
#endif

#ifdef __cplusplus
# define EXTERN_C_START extern "C" {
# define EXTERN_C_END }
#else
# define EXTERN_C_START
# define EXTERN_C_END
#endif

EXTERN_C_START

enum gpi_log_levels {
    GPIDebug = 10,
    GPIInfo = 20,
    GPIWarning = 30,
    GPIError = 40,
    GPICritical = 50
};


#define LOG_DEBUG(...)     gpi_log("cocotb.gpi", GPIDebug,         __FILE__, __func__, __LINE__, __VA_ARGS__);
#define LOG_INFO(...)      gpi_log("cocotb.gpi", GPIInfo,          __FILE__, __func__, __LINE__, __VA_ARGS__);
#define LOG_WARN(...)      gpi_log("cocotb.gpi", GPIWarning,       __FILE__, __func__, __LINE__, __VA_ARGS__);
#define LOG_ERROR(...)     gpi_log("cocotb.gpi", GPIError,         __FILE__, __func__, __LINE__, __VA_ARGS__);
#define LOG_CRITICAL(...)  gpi_log("cocotb.gpi", GPICritical,      __FILE__, __func__, __LINE__, __VA_ARGS__);

GPILOG_EXPORT void set_log_handler(void *handler);
GPILOG_EXPORT void clear_log_handler(void);
GPILOG_EXPORT void set_log_filter(void *filter);
GPILOG_EXPORT void clear_log_filter(void);
GPILOG_EXPORT void set_log_level(enum gpi_log_levels new_level);

GPILOG_EXPORT void gpi_log(const char *name, enum gpi_log_levels level, const char *pathname, const char *funcname, long lineno, const char *msg, ...);

EXTERN_C_END

#endif /* COCOTB_GPI_LOGGING_H_ */
