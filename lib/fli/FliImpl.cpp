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

void fli_elab_cb(void *nothing)
{
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

void cocotb_init(void)
{
    LOG_INFO("cocotb_init called\n");
    mti_AddLoadDoneCB(fli_elab_cb, NULL);
}



// Main re-entry point for callbacks from simulator
void handle_fli_callback(void *data)
{
    fflush(stderr);

    FliProcessCbHdl *cb_hdl = (FliProcessCbHdl*)data;

    if (!cb_hdl)
        LOG_CRITICAL("FLI: Callback data corrupted");

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

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
    LOG_DEBUG("Looking for child %s from %s", name.c_str(), parent->get_name_str());


    GpiObjHdl *new_obj = NULL; 
    std::vector<char> writable(name.begin(), name.end());
    writable.push_back('\0');

    mtiSignalIdT sig_hdl;
    sig_hdl = mti_FindSignal(&writable[0]);
    if (sig_hdl) {
        LOG_DEBUG("Found a signal %s -> %p", &writable[0], sig_hdl);
        new_obj = new FliSignalObjHdl(this, sig_hdl);
    }

    if (NULL == new_obj) {
        LOG_DEBUG("Didn't find anything named %s", &writable[0]);
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
        LOG_DEBUG("Iterating over: %s", mti_GetRegionName(root));
        if (name == NULL || !strcmp(name, mti_GetRegionName(root)))
            break;
    }

    if (!root) {
        goto error;
    }

    LOG_DEBUG("Found toplevel: %s, creating handle....", name);

    rv = new FliRegionObjHdl(this, root);
    rv->initialise(root_name);

    LOG_DEBUG("Returning root handle %p", rv);
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
    FliTimedCbHdl *hdl = cache.get_timer(time_ps);

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
int FliProcessCbHdl::cleanup_callback(void)
{

    if (m_sensitised)
        mti_Desensitize(m_proc_hdl);
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

int FliTimedCbHdl::arm_callback(void)
{
    LOG_DEBUG("Creating a new process to sensitise with timer");
    mti_ScheduleWakeup(m_proc_hdl, m_time_ps);
    LOG_DEBUG("Wakeup scheduled on %p for %llu", m_proc_hdl, m_time_ps);
    m_sensitised = true;
    set_call_state(GPI_PRIMED);
    return 0;
}

int FliSignalCbHdl::arm_callback(void)
{
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise to signal %s", mti_GetSignalName(m_sig_hdl));
        m_proc_hdl = mti_CreateProcess(NULL, handle_fli_callback, (void *)this);
    }

    mti_Sensitize(m_proc_hdl, m_sig_hdl, MTI_EVENT);
    m_sensitised = true;
    set_call_state(GPI_PRIMED);
    return 0;
}

int FliSimPhaseCbHdl::arm_callback(void)
{
    if (NULL == m_proc_hdl) {
        LOG_DEBUG("Creating a new process to sensitise with priority %d", m_priority);
        m_proc_hdl = mti_CreateProcessWithPriority(NULL, handle_fli_callback, (void *)this, m_priority);
    }

    mti_ScheduleWakeup(m_proc_hdl, 0);
    m_sensitised = true;
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


GpiCbHdl *FliSignalObjHdl::value_change_cb(unsigned int edge)
{
    FliSignalCbHdl *cb = NULL;

    switch (edge) {
    case 1:
        cb = &m_rising_cb;
        break;
    case 2:
        cb = &m_falling_cb;
        break;
    case 3:
        cb = &m_either_cb;
        break;
    default:
        return NULL;
    }

    if (cb->arm_callback()) {
        return NULL;
    }

    return (GpiValueCbHdl*)cb;
}

// TODO: Could cache various settings here which would save some of the calls
// into FLI
static char val_buff[1024];
static const char value_enum[10] = "UX01ZWLH-";

const char* FliSignalObjHdl::get_signal_value_binstr(void)
{
    switch (mti_GetTypeKind(mti_GetSignalType(m_fli_hdl))) {

        case MTI_TYPE_ENUM:
        case MTI_TYPE_SCALAR:
        case MTI_TYPE_PHYSICAL:
            mtiInt32T scalar_val;
            scalar_val = mti_GetSignalValue(m_fli_hdl);
            val_buff[0] = value_enum[scalar_val];
            val_buff[1] = '\0';
            break;
        case MTI_TYPE_ARRAY: {
            mtiInt32T *array_val;
            array_val = (mtiInt32T *)mti_GetArraySignalValue(m_fli_hdl, NULL);
            int num_elems = mti_TickLength(mti_GetSignalType(m_fli_hdl));
            if (num_elems <= 256) {
                char *iter = (char*)array_val;
                for (int i = 0; i < num_elems; i++ ) {
                    val_buff[i] = value_enum[(int)iter[i]];
                }
            } else {
                for (int i = 0; i < num_elems; i++ ) {
                    val_buff[i] = value_enum[array_val[i]];
                }
            }
            val_buff[num_elems] = '\0';
            mti_VsimFree(array_val);
            } break;
        default:
            LOG_CRITICAL("Signal %s type %d not currently supported", 
                m_name.c_str(), mti_GetTypeKind(mti_GetSignalType(m_fli_hdl)));
            break;
    }

    LOG_DEBUG("Retrieved \"%s\" for signal %s", &val_buff, m_name.c_str());

    return &val_buff[0];
}

int FliSignalObjHdl::set_signal_value(const int value)
{
    int rc;
    char buff[20];

    snprintf(buff, 20, "16#%016X", value);

    rc = mti_ForceSignal(m_fli_hdl, &buff[0], 0, MTI_FORCE_DEPOSIT, -1, -1);

    if (!rc) {
        LOG_CRITICAL("Setting signal value failed!\n");
    }
    return rc-1;
}

int FliSignalObjHdl::set_signal_value(std::string &value)
{
    int rc;
    char buff[128];
    int len = value.copy(buff, value.length());
    buff[len] = '\0';

    rc = mti_ForceSignal(m_fli_hdl, &buff[0], 0, MTI_FORCE_DEPOSIT, -1, -1);
    if (!rc) {
        LOG_CRITICAL("Setting signal value failed!\n");
    }
    return rc-1;
}

FliTimedCbHdl* FliTimerCache::get_timer(uint64_t time_ps)
{
#ifdef USE_CACHE
    FliTimedCbHdl *hdl;

    if (free_list.size()) {
        //LOG_DEBUG("Popping timer from cache list of %d\n", free_list.size()  );
        std::vector<FliTimedCbHdl*>::iterator first = free_list.begin();
        hdl = *first;
        free_list.erase(first);
        hdl->reset_time(time_ps);
    } else {
        //LOG_DEBUG("Created new timer\n");
        hdl = new FliTimedCbHdl(impl, time_ps);
    }

    return hdl;
#else
    return new FliTimedCbHdl(impl, time_ps);
#endif
}

void FliTimerCache::put_timer(FliTimedCbHdl* hdl)
{
#ifdef USE_CACHE
    free_list.push_back(hdl);
    //LOG_INFO("Adding timer to cache, now at %d\n", free_list.size());
#endif
}

GPI_ENTRY_POINT(fli, cocotb_init);

