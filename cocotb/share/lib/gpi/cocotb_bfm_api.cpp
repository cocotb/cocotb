/******************************************************************************
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
 ******************************************************************************/
#include <stdio.h>
#include "cocotb_bfm_api.h"
#include "GpiBfm.h"

int cocotb_bfm_register(
        const char                *inst_name,
        const char                *cls_name,
        cocotb_bfm_notify_f        notify_f,
        void                    *notify_data) {

    return GpiBfm::add_bfm(new GpiBfm(
            inst_name,
            cls_name,
            notify_f,
            notify_data
            ));
}

// Returns the number of registered BFMs
int cocotb_bfm_num_registered(void) {
    return GpiBfm::get_bfms().size();
}

// Returns the instance name of the specified BFM
const char *cocotb_bfm_instname(int id) {
    return GpiBfm::get_bfms().at(id)->get_instname().c_str();
}

// Returns the class name of the specified BFM
const char *cocotb_bfm_clsname(int id) {
    return GpiBfm::get_bfms().at(id)->get_clsname().c_str();
}

//
int cocotb_bfm_claim_msg(int id) {
    return GpiBfm::get_bfms().at(id)->claim_msg();
}

uint64_t cocotb_bfm_get_ui_param(int id) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(id);
    GpiBfmMsg *msg = bfm->active_msg();

    if (msg) {
        return msg->get_param_ui();
    } else {
        return 0;
    }
}

int64_t cocotb_bfm_get_si_param(int id) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(id);
    GpiBfmMsg *msg = bfm->active_msg();

    if (msg) {
        return msg->get_param_si();
    } else {
        return 0;
    }
}

const char *cocotb_bfm_get_str_param(int id) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(id);
    GpiBfmMsg *msg = bfm->active_msg();

    if (msg) {
        return msg->get_param_str();
    } else {
        return 0;
    }
}

void cocotb_bfm_begin_msg(uint32_t bfm_id, uint32_t msg_id) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);

    bfm->begin_inbound_msg(msg_id);
}

void cocotb_bfm_add_si_param(uint32_t bfm_id, int64_t pval) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
    GpiBfmMsg *msg = bfm->active_inbound_msg();

    if (msg) {
        msg->add_param_si(pval);
    } else {
        fprintf(stdout, "Error: attempting to add a signed parameter to a NULL message\n");
    }
}

void cocotb_bfm_add_ui_param(uint32_t bfm_id, uint64_t pval) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
    GpiBfmMsg *msg = bfm->active_inbound_msg();

    if (msg) {
        msg->add_param_ui(pval);
    } else {
        fprintf(stdout, "Error: attempting to add an unsigned parameter to a NULL message\n");
    }
}

void cocotb_bfm_end_msg(uint32_t bfm_id) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);

    bfm->send_inbound_msg();
}

void cocotb_bfm_send_msg(
        uint32_t                bfm_id,
        uint32_t                msg_id,
        uint32_t                paramc,
        cocotb_bfm_msg_param_t    *paramv) {
    GpiBfm *bfm = GpiBfm::get_bfms().at(bfm_id);
    GpiBfmMsg *msg = new GpiBfmMsg(msg_id, paramc, paramv);
    bfm->send_msg(msg);
}

void cocotb_bfm_set_recv_msg_f(bfm_recv_msg_f recv_msg_f) {
    GpiBfm::set_recv_msg_f(recv_msg_f);
}
