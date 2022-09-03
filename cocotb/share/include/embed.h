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
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#ifndef COCOTB_EMBED_H_
#define COCOTB_EMBED_H_

#include <exports.h>
#ifdef COCOTB_EMBED_EXPORTS
#define COCOTB_EMBED_EXPORT COCOTB_EXPORT
#else
#define COCOTB_EMBED_EXPORT COCOTB_IMPORT
#endif

#include <gpi.h>

#ifdef __cplusplus
extern "C" {
#endif

extern COCOTB_EMBED_EXPORT void embed_init_python(void);
extern COCOTB_EMBED_EXPORT void embed_sim_cleanup(void);
extern COCOTB_EMBED_EXPORT int embed_sim_init(int argc,
                                              char const* const* argv);
extern COCOTB_EMBED_EXPORT void embed_sim_event(const char* msg);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_EMBED_H_ */
