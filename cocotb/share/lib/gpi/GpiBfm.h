/******************************************************************************
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
 ******************************************************************************/
#ifndef INCLUDED_GPI_BFM_H
#define INCLUDED_GPI_BFM_H
#include <stdint.h>
#include <string>
#include <vector>
#include "cocotb_bfm_api.h"
#include "GpiBfmMsg.h"




class GpiBfm {
public:

    GpiBfm(
            const std::string        &type_name,
            const std::string        &inst_name,
            const std::string        &cls_name,
            cocotb_bfm_notify_f        notify_f,
            void                    *notify_data
            );

    virtual ~GpiBfm();

    static int add_bfm(GpiBfm *bfm);

    static const std::vector<GpiBfm *> &get_bfms() { return m_bfm_l; }

    const std::string &get_typename() const { return m_typename; }

    const std::string &get_instname() const { return m_instname; }

    const std::string &get_clsname() const { return m_clsname; }

    void send_msg(GpiBfmMsg *msg);

    int claim_msg();

    GpiBfmMsg *active_msg() const { return m_active_msg; }

    void begin_inbound_msg(uint32_t msg_id);

    GpiBfmMsg *active_inbound_msg() const { return m_active_inbound_msg; }

    void send_inbound_msg();

    static void set_recv_msg_f(bfm_recv_msg_f f) { m_recv_msg_f = f; }

protected:

private:
    uint32_t                         m_bfm_id;
    std::string                      m_typename;
    std::string                      m_instname;
    std::string                      m_clsname;
    cocotb_bfm_notify_f              m_notify_f;
    void                             *m_notify_data;
    std::vector<GpiBfmMsg *>         m_msg_queue;
    GpiBfmMsg                        *m_active_msg;
    // Message ready to be sent to
    GpiBfmMsg                        *m_active_inbound_msg;

    static bfm_recv_msg_f            m_recv_msg_f;
    static std::vector<GpiBfm *>     m_bfm_l;


};

#endif /* INCLUDED_GPI_BFM_H */
