/******************************************************************************
* Copyright (c) 2014 Potential Ventures Ltd
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

#include <vector>

#include "FliImpl.h"
#include "acc_vhdl.h"   // Messy :(
#include "acc_user.h"


extern "C" {

static FliImpl *fli_table;

void fli_elab_cb(void *nothing) {
    LOG_INFO("fli_elab_cb called\n");

    fli_table = new FliImpl("FLI");
    gpi_register_impl(fli_table);
    gpi_load_extra_libs();

    // Elaboration has already happened so jump straight in!
    gpi_sim_info_t sim_info;

    char *version = mti_GetProductVersion();      // Returned pointer must not be freed

    // copy in sim_info.product
    // FIXME split product and version from returned string?
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = version;
    sim_info.version = version;

    gpi_embed_init(&sim_info);
}

void cocotb_init(void) {
    LOG_INFO("cocotb_init called\n");
    mti_AddLoadDoneCB(fli_elab_cb, NULL);
}



// Main re-entry point for callbacks from simulator
void handle_fli_callback(void *data)
{
    fprintf(stderr, "Got a callback\n");
    fflush(stderr);

    FliCbHdl *cb_hdl = (FliCbHdl*)data;

    if (!cb_hdl)
        LOG_CRITICAL("FLI: Callback data corrupted");

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

    fprintf(stderr, "FLI: Old state was %d!\n", old_state);
    fflush(stderr);

    if (old_state == GPI_PRIMED) { 

        cb_hdl->set_call_state(GPI_CALL);
        cb_hdl->run_callback();

        gpi_cb_state_e new_state = cb_hdl->get_call_state();

        /* We have re-primed in the handler */
        if (new_state != GPI_PRIMED)
            if (cb_hdl->cleanup_callback())
                delete cb_hdl;
    }
};

} // extern "C"

void FliImpl::sim_end(void)
{
    mti_Quit();
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    LOG_INFO("Looking for child %s from %s", name.c_str(), parent->get_name_str());


    GpiObjHdl *new_obj = NULL; 
    std::vector<char> writable(name.begin(), name.end());
    writable.push_back('\0');

    mtiSignalIdT sig_hdl;
    sig_hdl = mti_FindSignal(&writable[0]);
    if (sig_hdl) {
        LOG_INFO("Found a signal %s -> %p", &writable[0], sig_hdl);
        new_obj = new FliSignalObjHdl(this, sig_hdl);
    }

    if (NULL == new_obj) {
        LOG_WARN("Didn't find anything named %s", &writable[0]);
        return NULL;
    }

    new_obj->initialise(name);
    return new_obj;
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    return NULL;
}

const char *FliImpl::reason_to_string(int reason)
{
    return "Who can explain it, who can tell you why?";
}


/**
 * @name    Get current simulation time
 * @brief   Get current simulation time
 *
 * NB units depend on the simulation configuration
 */
void FliImpl::get_sim_time(uint32_t *high, uint32_t *low)
{
    *high = mti_NowUpper();
    *low = mti_Now();
}

#if 0
/**
 * @name    Find the root handle
 * @brief   Find the root handle using an optional name
 *
 * Get a handle to the root simulator object.  This is usually the toplevel.
 *
 * If no name is provided, we return the first root instance.
 *
 * If name is provided, we check the name against the available objects until
 * we find a match.  If no match is found we return NULL
 */
int FliObjHdl::initialise(std::string &name) {
    m_name = name;
    m_type = "unknown";

    return 0;
}
#endif


/**
 * @name    Find the root handle
 * @brief   Find the root handle using an optional name
 *
 * Get a handle to the root simulator object.  This is usually the toplevel.
 *
 * If no name is provided, we return the first root instance.
 *
 * If name is provided, we check the name against the available objects until
 * we find a match.  If no match is found we return NULL
 */
GpiObjHdl *FliImpl::get_root_handle(const char *name)
{
    mtiRegionIdT root;
    GpiObjHdl *rv;
    std::string root_name = name;

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        LOG_INFO("Iterating over: %s", mti_GetRegionName(root));
        if (name == NULL || !strcmp(name, mti_GetRegionName(root)))
            break;
    }

    if (!root) {
        goto error;
    }

    LOG_INFO("Found toplevel: %s, creating handle....", name);

    rv = new FliRegionObjHdl(this, root);
    rv->initialise(root_name);

    LOG_INFO("Returning root handle %p", rv);
    return rv;

  error:

    LOG_CRITICAL("FLI: Couldn't find root handle %s", name);

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {

        LOG_CRITICAL("FLI: Toplevel instances: %s != %s...", name, mti_GetRegionName(root));

        if (name == NULL)
            break;
    }
    return NULL;
}


GpiCbHdl *FliImpl::register_timed_callback(uint64_t time_ps)
{
    FliTimedCbHdl *hdl = new FliTimedCbHdl(this, time_ps);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }
    return hdl;
}


GpiCbHdl *FliImpl::register_readonly_callback(void)
{
    if (m_readonly_cbhdl.arm_callback()) {
        return NULL;
    }
    return &m_readonly_cbhdl;
}

GpiCbHdl *FliImpl::register_readwrite_callback(void)
{
    if (m_readwrite_cbhdl.arm_callback()) {
        return NULL;
    }
    return &m_readwrite_cbhdl;
}

GpiCbHdl *FliImpl::register_nexttime_callback(void)
{
    if (m_nexttime_cbhdl.arm_callback()) {
        return NULL;
    }
    return &m_nexttime_cbhdl;
}


int FliImpl::deregister_callback(GpiCbHdl *gpi_hdl)
{
    int rc = gpi_hdl->cleanup_callback();
    // TOOD: Don't delete if it's a re-usable doobery
//     delete(gpi_hdl);
    return rc;
}





/**
 * @name    cleanup callback
 * @brief   Called while unwinding after a GPI callback
 *
 * We keep the process but de-sensitise it
 * 
 * NB need a way to determine if should leave it sensitised, hmmm...
 * 
 */
int FliProcessCbHdl::cleanup_callback(void) {

    if (m_sensitised)
        mti_Desensitize(m_proc_hdl);
    m_sensitised = false;
    return 0;
}

int FliTimedCbHdl::arm_callback(void) {
    LOG_INFO("Creating a new process to sensitise with timer");
    m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback, (void *)this, MTI_PROC_IMMEDIATE);
    mti_ScheduleWakeup(m_proc_hdl, m_time_ps);
    LOG_INFO("Wakeup scheduled on %p for %llu", m_proc_hdl, m_time_ps);
    m_sensitised = true;
    m_state = GPI_PRIMED;
    return 0;
}

int FliSignalCbHdl::arm_callback(void) {

    if (NULL == m_proc_hdl) {
        LOG_INFO("Creating a new process to sensitise to signal %s", mti_GetSignalName(m_sig_hdl));
        m_proc_hdl = mti_CreateProcess(NULL, handle_fli_callback, (void *)this);
    }

    mti_Sensitize(m_proc_hdl, m_sig_hdl, MTI_EVENT);
    m_sensitised = true;
    m_state = GPI_PRIMED;
    return 0;
}

int FliSimPhaseCbHdl::arm_callback(void) {

    if (NULL == m_proc_hdl) {
        LOG_INFO("Creating a new process to sensitise with priority %d", m_priority);
        m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback, (void *)this, m_priority);
    }

    mti_ScheduleWakeup(m_proc_hdl, 0);
    m_sensitised = true;
    m_state = GPI_PRIMED;
    return 0;
}

GPI_ENTRY_POINT(fli, cocotb_init);



GpiCbHdl *FliSignalObjHdl::value_change_cb(unsigned int edge) {

    LOG_INFO("Creating value change callback for %s", m_name.c_str());

    if (NULL == m_cb_hdl) {
        m_cb_hdl = new FliSignalCbHdl(m_impl, m_fli_hdl);
    }
    m_cb_hdl->arm_callback();

    return m_cb_hdl;
}




const char* FliSignalObjHdl::get_signal_value_binstr(void) {
    return "010101";
}

int FliSignalObjHdl::set_signal_value(const int value) {
    return 0;
}

int FliSignalObjHdl::set_signal_value(std::string &value) {
    return 0;
}

