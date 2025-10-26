// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

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

extern COCOTB_EMBED_EXPORT void embed_entry_point(void);
extern COCOTB_EMBED_EXPORT void embed_finalize(void);
extern COCOTB_EMBED_EXPORT int embed_start_of_sim_time(int argc,
                                                       char const *const *argv);
extern COCOTB_EMBED_EXPORT void embed_end_of_sim_time(void);

#ifdef __cplusplus
}
#endif

#endif /* COCOTB_EMBED_H_ */
