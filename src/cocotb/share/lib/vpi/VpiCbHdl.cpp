/******************************************************************************
 * Copyright (c) 2013, 2018 Potential Ventures Ltd
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

#include <assert.h>

#include <stdexcept>

#include "VpiImpl.h"

extern "C" int32_t handle_vpi_callback(p_cb_data cb_data);

VpiCbHdl::VpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl) {
    vpi_time.high = 0;
    vpi_time.low = 0;
    vpi_time.type = vpiSimTime;

    cb_data.reason = 0;
    cb_data.cb_rtn = handle_vpi_callback;
    cb_data.obj = NULL;
    cb_data.time = &vpi_time;
    cb_data.value = NULL;
    cb_data.index = 0;
    cb_data.user_data = (char *)this;
}

/* If the user data already has a callback handle then deregister
 * before getting the new one
 */
int VpiCbHdl::arm_callback() {
    if (m_state == GPI_PRIMED) {
        fprintf(stderr, "Attempt to prime an already primed trigger for %s!\n",
                m_impl->reason_to_string(cb_data.reason));
    }

    // Only a problem if we have not been asked to deregister and register
    // in the same simulation callback
    if (m_obj_hdl != NULL && m_state != GPI_DELETE) {
        fprintf(stderr, "We seem to already be registered, deregistering %s!\n",
                m_impl->reason_to_string(cb_data.reason));
        cleanup_callback();
    }

    vpiHandle new_hdl = vpi_register_cb(&cb_data);

    if (!new_hdl) {
        LOG_ERROR(
            "VPI: Unable to register a callback handle for VPI type %s(%d)",
            m_impl->reason_to_string(cb_data.reason), cb_data.reason);
        check_vpi_error();
        return -1;

    } else {
        m_state = GPI_PRIMED;
    }

    m_obj_hdl = new_hdl;

    return 0;
}

int VpiCbHdl::cleanup_callback() {
    if (m_state == GPI_FREE) return 0;

    /* If the one-time callback has not come back then
     * remove it, it is has then free it. The remove is done
     * internally */

    if (m_state == GPI_PRIMED) {
        if (!m_obj_hdl) {
            LOG_ERROR("VPI: passed a NULL pointer");
            return -1;
        }

        if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
            LOG_ERROR("VPI: unable to remove callback");
            return -1;
        }

        check_vpi_error();
    } else {
#ifndef MODELSIM
        /* This is disabled for now, causes a small leak going to put back in */
        if (!(vpi_free_object(get_handle<vpiHandle>()))) {
            LOG_ERROR("VPI: unable to free handle");
            return -1;
        }
#endif
    }

    m_obj_hdl = NULL;
    m_state = GPI_FREE;

    return 0;
}

VpiValueCbHdl::VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig,
                             int edge)
    : GpiCbHdl(impl),
      GpiCommonCbHdl(impl),
      VpiCbHdl(impl),
      GpiValueCbHdl(impl, sig, edge) {
    vpi_time.type = vpiSuppressTime;
    m_vpi_value.format = vpiIntVal;

    cb_data.reason = cbValueChange;
    cb_data.time = &vpi_time;
    cb_data.value = &m_vpi_value;
    cb_data.obj = m_signal->get_handle<vpiHandle>();
}

int VpiValueCbHdl::cleanup_callback() {
    if (m_state == GPI_FREE) return 0;

    /* This is a recurring callback so just remove when
     * not wanted */
    if (!(vpi_remove_cb(get_handle<vpiHandle>()))) {
        LOG_ERROR("VPI: unable to remove callback");
        return -1;
    }

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 0;
}

VpiStartupCbHdl::VpiStartupCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
#ifndef IUS
    cb_data.reason = cbStartOfSimulation;
#else
    vpi_time.high = (uint32_t)(0);
    vpi_time.low = (uint32_t)(0);
    vpi_time.type = vpiSimTime;
    cb_data.reason = cbAfterDelay;
#endif
}

int VpiStartupCbHdl::run_callback() {
    s_vpi_vlog_info info;

    if (!vpi_get_vlog_info(&info)) {
        LOG_WARN("Unable to get argv and argc from simulator");
        info.argc = 0;
        info.argv = nullptr;
    }

    gpi_embed_init(info.argc, info.argv);

    return 0;
}

VpiShutdownCbHdl::VpiShutdownCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCbHdl(impl) {
    cb_data.reason = cbEndOfSimulation;
}

int VpiShutdownCbHdl::run_callback() {
    gpi_embed_end();
    return 0;
}

VpiTimedCbHdl::VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time)
    : GpiCbHdl(impl), VpiCommonCbHdl(impl) {
    vpi_time.high = (uint32_t)(time >> 32);
    vpi_time.low = (uint32_t)(time);
    vpi_time.type = vpiSimTime;

    cb_data.reason = cbAfterDelay;
}

int VpiTimedCbHdl::cleanup_callback() {
    switch (m_state) {
        case GPI_PRIMED:
            /* Issue #188: Work around for modelsim that is harmless to others
               too, we tag the time as delete, let it fire then do not pass up
               */
            LOG_DEBUG("Not removing PRIMED timer %d", vpi_time.low);
            set_call_state(GPI_DELETE);
            return 0;
        case GPI_DELETE:
            LOG_DEBUG("Removing DELETE timer %d", vpi_time.low);
        default:
            break;
    }
    VpiCbHdl::cleanup_callback();
    /* Return one so we delete this object */
    return 1;
}

VpiReadWriteCbHdl::VpiReadWriteCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCommonCbHdl(impl) {
    cb_data.reason = cbReadWriteSynch;
}

VpiReadOnlyCbHdl::VpiReadOnlyCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCommonCbHdl(impl) {
    cb_data.reason = cbReadOnlySynch;
}

VpiNextPhaseCbHdl::VpiNextPhaseCbHdl(GpiImplInterface *impl)
    : GpiCbHdl(impl), VpiCommonCbHdl(impl) {
    cb_data.reason = cbNextSimTime;
}
