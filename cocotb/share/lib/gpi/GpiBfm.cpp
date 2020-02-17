/******************************************************************************
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
 ******************************************************************************/
#include "GpiBfm.h"
#include <stdio.h>

GpiBfm::GpiBfm(
        const std::string        &inst_name,
        const std::string        &cls_name,
        cocotb_bfm_notify_f      notify_f,
        void                    *notify_data) :
        m_instname(inst_name),
        m_clsname(cls_name),
        m_notify_f(notify_f),
        m_notify_data(notify_data) {
    m_active_msg = 0;
    m_active_inbound_msg = 0;
}

GpiBfm::~GpiBfm() {
    if (m_active_msg) {
        delete m_active_msg;
        m_active_msg = 0;
    }
    if (m_active_inbound_msg) {
    	  delete m_active_inbound_msg;
    }
}

uint32_t GpiBfm::add_bfm(GpiBfm *bfm) {
    bfm->m_bfm_id = static_cast<uint32_t>(m_bfm_l.size());

    m_bfm_l.push_back(bfm);

    return bfm->m_bfm_id;
}

void GpiBfm::send_msg(GpiBfmMsg *msg) {
    m_msg_queue.push_back(msg);
    if (m_notify_f) {
        m_notify_f(m_notify_data);
    }
}

int GpiBfm::claim_msg() {
    if (m_active_msg) {
        delete m_active_msg;
        m_active_msg = 0;
    }
    if (m_msg_queue.size() > 0) {
        m_active_msg = m_msg_queue.at(0);
        m_msg_queue.erase(m_msg_queue.begin());
        return static_cast<int32_t>(m_active_msg->id());
    } else {
        return -1;
    }
}

void GpiBfm::begin_inbound_msg(uint32_t msg_id) {
    m_active_inbound_msg = new GpiBfmMsg(msg_id);
}

void GpiBfm::send_inbound_msg() {
    if (m_recv_msg_f) {
        m_recv_msg_f(
            m_bfm_id,
            m_active_inbound_msg->id(),
            m_active_inbound_msg->num_params(),
            m_active_inbound_msg->get_param_l());
    } else {
        fprintf(stdout, "Error: Attempting to send a message (%d) before initialization\n",
                m_active_inbound_msg->id());
        fflush(stdout);
    }

    // Clean up
    delete m_active_inbound_msg;
    m_active_inbound_msg = 0;
}

std::vector<GpiBfm *> GpiBfm::m_bfm_l;
bfm_recv_msg_f GpiBfm::m_recv_msg_f = 0;
