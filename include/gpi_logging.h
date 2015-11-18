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
#define LOG_CRITICAL(...)  do { \
    gpi_log("cocotb.gpi", GPICritical,      __FILE__, __func__, __LINE__, __VA_ARGS__); \
    exit(1); \
} while (0)

// #ifdef DEBUG
// #define FENTER LOG_DEBUG(__func__)
// #define FEXIT  LOG_DEBUG(__func__)
// #else
#define FENTER
#define FEXIT
// #endif

void set_log_handler(void *handler);
void set_make_record(void *makerecord);
void set_log_filter(void *filter);
void set_log_level(enum gpi_log_levels new_level);

void gpi_log(const char *name, long level, const char *pathname, const char *funcname, long lineno, const char *msg, ...);

EXTERN_C_END

#endif /* COCOTB_GPI_LOGGING_H_ */
