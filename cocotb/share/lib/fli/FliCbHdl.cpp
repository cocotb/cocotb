/******************************************************************************
* Copyright (c) 2015/16 Potential Ventures Ltd
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*    * Redistributions of source code must retain the above copyright
*      notice, this list of conditions and the following disclaimer.
*    * Redistributions in binary form must reproduce the above copyright
*      notice, this list of conditions and the following disclaimer in the
*      documentation and/or other materials provided with the distribution.
*    * Neither the name of Potential Ventures Ltd
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

#include "FliImpl.h"

/**
 * @name    cleanup callback
 * @brief   Called while unwinding after a GPI callback
 *
 * We keep the process but desensitize it
 *
 * NB: need a way to determine if should leave it sensitized...
 *
 */
int FliProcessCbHdl::cleanup_callback()
{
    if (m_sensitised) {
        mti_Desensitize(m_proc_hdl);
    }
    m_sensitised = false;
    return 0;
}

FliTimedCbHdl::FliTimedCbHdl(GpiImplInterface *impl,
                             uint64_t time_ps) : GpiCbHdl(impl),
                                                 FliProcessCbHdl(impl),
                                                 m_time_ps(time_ps)
{
    m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback, (void *)this, MTI_PROC_IMMEDIATE);
}

int FliTimedCbHdl::arm_callback()
{
    #if defined(__LP64__) || defined(_WIN64)
        mti_ScheduleWakeup64(m_proc_hdl, m_time_ps);
    #else
        mtiTime64T m_time_union_ps;
        MTI_TIME64_ASGN(m_time_union_ps, (mtiInt32T)((m_time_ps) >> 32), (mtiUInt32T)(m_time_ps));
        mti_ScheduleWakeup64(m_proc_hdl, m_time_union_ps);
    #endif
    m_sensitised = true;
    set_call_state(GPI_PRIMED);
    return 0;
}

int FliTimedCbHdl::cleanup_callback()
{
    switch (get_call_state()) {
    case GPI_PRIMED:
        /* Issue #188: Work around for modelsim that is harmless to othes too,
           we tag the time as delete, let it fire then do not pass up
           */
        LOG_DEBUG("Not removing PRIMED timer %p", m_time_ps);
        set_call_state(GPI_DELETE);
        return 0;
    case GPI_CALL:
        LOG_DEBUG("Not removing CALL timer yet %p", m_time_ps);
        set_call_state(GPI_DELETE);
        return 0;
    case GPI_DELETE:
        LOG_DEBUG("Removing Postponed DELETE timer %p", m_time_ps);
        break;
    default:
        break;
    }
    FliProcessCbHdl::cleanup_callback();
    FliImpl* impl = (FliImpl*)m_impl;
    impl->cache.put_timer(this);
    return 0;
}

int FliSignalCbHdl::arm_callback()
{
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise to signal %s", mti_GetSignalName(m_sig_hdl));
        m_proc_hdl = mti_CreateProcess(NULL, handle_fli_callback, (void *)this);
    }

    if (!m_sensitised) {
        mti_Sensitize(m_proc_hdl, m_sig_hdl, MTI_EVENT);
        m_sensitised = true;
    }
    set_call_state(GPI_PRIMED);
    return 0;
}

int FliSimPhaseCbHdl::arm_callback()
{
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise with priority %d", m_priority);
        m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback, (void *)this, m_priority);
    }

    if (!m_sensitised) {
        mti_ScheduleWakeup(m_proc_hdl, 0);
        m_sensitised = true;
    }
    set_call_state(GPI_PRIMED);
    return 0;
}

FliSignalCbHdl::FliSignalCbHdl(GpiImplInterface *impl,
                               FliSignalObjHdl *sig_hdl,
                               unsigned int edge) : GpiCbHdl(impl),
                                                    FliProcessCbHdl(impl),
                                                    GpiValueCbHdl(impl, sig_hdl, edge)
{
    m_sig_hdl = m_signal->get_handle<mtiSignalIdT>();
}

int FliStartupCbHdl::arm_callback()
{
    mti_AddLoadDoneCB(handle_fli_callback,(void *)this);
    set_call_state(GPI_PRIMED);

    return 0;
}

int FliStartupCbHdl::run_callback()
{
    gpi_sim_info_t sim_info;

    char *c_info       = mti_GetProductVersion();      // Returned pointer must not be freed
    std::string info   = c_info;
    std::string search = " Version ";
    std::size_t found  = info.find(search);

    std::string product_str = c_info;
    std::string version_str = c_info;

    if (found != std::string::npos) {
        product_str = info.substr(0,found);
        version_str = info.substr(found+search.length());

        LOG_DEBUG("Found Version string at %d", found);
        LOG_DEBUG("   product: %s", product_str.c_str());
        LOG_DEBUG("   version: %s", version_str.c_str());
    }

    std::vector<char> product(product_str.begin(), product_str.end());
    std::vector<char> version(version_str.begin(), version_str.end());
    product.push_back('\0');
    version.push_back('\0');


    // copy in sim_info.product
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = &product[0];
    sim_info.version = &version[0];

    gpi_embed_init(&sim_info);

    return 0;
}

int FliShutdownCbHdl::arm_callback()
{
    mti_AddQuitCB(handle_fli_callback,(void *)this);
    set_call_state(GPI_PRIMED);

    return 0;
}

int FliShutdownCbHdl::run_callback()
{
    gpi_embed_end();

    return 0;
}

