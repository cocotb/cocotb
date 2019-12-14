/******************************************************************************
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
 ******************************************************************************/
#ifndef INCLUDED_COCOTB_BFM_API_H
#define INCLUDED_COCOTB_BFM_API_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Callback function type used to notify
// implementation when a message is available
typedef void (*cocotb_bfm_notify_f)(void *);

int cocotb_bfm_register(
        const char                *inst_name,
        const char                *cls_name,
        cocotb_bfm_notify_f        notify_f,
        void                    *notify_data);

// Returns the number of registered BFMs
int cocotb_bfm_num_registered(void);

// Returns the instance name of the specified BFM
const char *cocotb_bfm_instname(int id);

// Returns the class name of the specified BFM
const char *cocotb_bfm_clsname(int id);

// Claims the next message in the queue.
// If none is available, returns -1
int cocotb_bfm_claim_msg(int id);

// Get an unsigned-integer parameter from the active message
uint64_t cocotb_bfm_get_ui_param(int id);

// Get an signed-integer parameter from the active message
int64_t cocotb_bfm_get_si_param(int id);

// Get a string parameter from the active message
const char *cocotb_bfm_get_str_param(int id);

/*
 * Called from the simulator side to begin
 * a message
 */
void cocotb_bfm_begin_msg(
        uint32_t            bfm_id,
        uint32_t            msg_id);

void cocotb_bfm_add_ui_param(
        uint32_t            bfm_id,
        uint64_t            p);

void cocotb_bfm_add_si_param(
        uint32_t            bfm_id,
        int64_t                p);

void cocotb_bfm_add_str_param(
        uint32_t            bfm_id,
        const char            *p);

/*
 * Called from the simulator side to complete
 * a message and send it to the Python side
 */
void cocotb_bfm_end_msg(
        uint32_t            bfm_id);


typedef enum {
    GpiBfmParamType_Ui,
    GpiBfmParamType_Si,
    GpiBfmParamType_Str
} cocotb_bfm_param_type_e;

typedef struct cocotb_bfm_msg_param_s {
    cocotb_bfm_param_type_e    ptype;
    union {
        const char            *str;
        uint64_t            ui64;
        int64_t                i64;
    } pval;
} cocotb_bfm_msg_param_t;

/**
 * Send a message to a specific BFM
 */
void cocotb_bfm_send_msg(
        uint32_t                bfm_id,
        uint32_t                msg_id,
        uint32_t                paramc,
        cocotb_bfm_msg_param_t    *paramv);

/**
 * Callback function type to receive
 * messages from BFMs
 */
typedef void (*bfm_recv_msg_f)(
        uint32_t                 bfm_id,
        uint32_t                 msg_id,
        uint32_t                paramc,
        cocotb_bfm_msg_param_t    *paramv);

void cocotb_bfm_set_recv_msg_f(
        bfm_recv_msg_f        recv_msg_f);

#ifdef __cplusplus
}
#endif
#endif /* INCLUDED_COCOTB_BFM_API_H */
