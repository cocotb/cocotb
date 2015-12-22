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
#include "mti.h"
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

    if (!cb_hdl) {
        LOG_CRITICAL("FLI: Callback data corrupted: ABORTING");
    }

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

    if (old_state == GPI_PRIMED) {

        cb_hdl->set_call_state(GPI_CALL);

        cb_hdl->run_callback();
        gpi_cb_state_e new_state = cb_hdl->get_call_state();

        /* We have re-primed in the handler */
        if (new_state != GPI_PRIMED)
            if (cb_hdl->cleanup_callback())
                delete cb_hdl;
    } else {
        /* Issue #188 seems to appear via FLI as well */
        cb_hdl->cleanup_callback();
    }
};

} // extern "C"


void FliImpl::sim_end(void)
{
    const char *stop = "stop";

    mti_Cmd(stop);
}

GpiObjHdl *FliImpl::create_gpi_obj(std::string &name, std::string &fq_name)
{
    GpiObjHdl *new_obj = NULL;

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    mtiRegionIdT   rgn_hdl;
    mtiSignalIdT   sig_hdl;
    mtiVariableIdT var_hdl;

    if ((rgn_hdl = mti_FindRegion(&writable[0])) != NULL) {
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), rgn_hdl);
        new_obj = new GpiObjHdl(this, rgn_hdl, GPI_MODULE);
    } else if ((sig_hdl = mti_FindSignal(&writable[0])) != NULL) {
        LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), sig_hdl);

        gpi_objtype_t objtype;
        mtiTypeKindT typeKind = mti_GetTypeKind(mti_GetSignalType(sig_hdl));

        switch (typeKind) {
            case MTI_TYPE_ENUM:
                objtype = GPI_REGISTER;  // Assumes std_logic
                break;
            case MTI_TYPE_SCALAR:
            case MTI_TYPE_PHYSICAL:
                objtype = GPI_INTEGER;
                break;
            case MTI_TYPE_ARRAY:
                objtype = GPI_REGISTER;  // Assumes std_logic_vector
                break;
            default:
                LOG_ERROR("Unable to handle object type for %s (%d)",
                             name.c_str(), typeKind);
        }

        new_obj = new FliValueObjHdl(this, sig_hdl, objtype, false, false);

    } else if ((var_hdl = mti_FindVar(&writable[0])) != NULL) {
        LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), var_hdl);

        gpi_objtype_t objtype;
        int varKind = mti_GetVarKind(var_hdl);
        mtiTypeKindT typeKind = mti_GetTypeKind(mti_GetVarType(var_hdl));

        switch (typeKind) {
            case MTI_TYPE_ENUM:
                objtype = GPI_REGISTER;  // Assumes std_logic
                break;
            case MTI_TYPE_SCALAR:
            case MTI_TYPE_PHYSICAL:
                objtype = GPI_INTEGER;
                break;
            case MTI_TYPE_ARRAY:
                objtype = GPI_REGISTER;  // Assumes std_logic_vector
                break;
            default:
                LOG_ERROR("Unable to handle object type for %s (%d)",
                             name.c_str(), typeKind);
        }

        new_obj = new FliValueObjHdl(this, var_hdl, objtype, (varKind != accVariable), true);
    }
    else {
        LOG_DEBUG("Unable to query %s", fq_name.c_str());
        return NULL;
    }

    if (NULL == new_obj) {
        LOG_DEBUG("Didn't find anything named %s", &writable[0]);
        return NULL;
    }

    new_obj->initialise(name,fq_name);
    return new_obj;
}

GpiObjHdl* FliImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent)
{
    LOG_WARN("%s implementation can not create from raw handle",
             get_name_c());
    return NULL;
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    std::string fq_name = parent->get_fullname();
    if (fq_name == "/") {
        fq_name += name;
    } else {
        fq_name += "/" + name;
    }
    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');


    LOG_DEBUG("Looking for child %s from %s", name.c_str(), parent->get_name_str());

    return create_gpi_obj(name, fq_name);
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    char buff[15];
    snprintf(buff, 15, "(%u)", index);
    std::string idx = buff;
    std::string name = parent->get_name() + idx;
    std::string fq_name = parent->get_fullname() + idx;
    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');


    LOG_DEBUG("Looking for index %u from %s", index, parent->get_name_str());

    return create_gpi_obj(name, fq_name);
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
    char *rgn_name;
    char *rgn_fullname;
    std::string root_name;
    std::string root_fullname;

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        LOG_DEBUG("Iterating over: %s", mti_GetRegionName(root));
        if (name == NULL || !strcmp(name, mti_GetRegionName(root)))
            break;
    }

    if (!root) {
        goto error;
    }

    rgn_name     = mti_GetRegionName(root);
    rgn_fullname = mti_GetRegionFullName(root);

    root_name     = rgn_name;
    root_fullname = rgn_fullname;
    mti_VsimFree(rgn_fullname);

    LOG_DEBUG("Found toplevel: %s, creating handle....", root_name.c_str());

    return create_gpi_obj(root_name, root_fullname);

error:

    LOG_ERROR("FLI: Couldn't find root handle %s", name);

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        if (name == NULL)
            break;

        LOG_ERROR("FLI: Toplevel instances: %s != %s...", name, mti_GetRegionName(root));
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
    return gpi_hdl->cleanup_callback();
}


GpiIterator *FliImpl::iterate_handle(GpiObjHdl *obj_hdl, gpi_iterator_sel_t type)
{
    /* This function should return a class derived from GpiIterator and follows it's
       interface. Specifically it's new_handle(std::string, std::string) method and
       return values. Using VpiIterator as an example */
    return NULL;
}


FliTimedCbHdl* FliTimerCache::get_timer(uint64_t time_ps)
{
    FliTimedCbHdl *hdl;

    if (!free_list.empty()) {
        hdl = free_list.front();
        free_list.pop();
        hdl->reset_time(time_ps);
    } else {
        hdl = new FliTimedCbHdl(impl, time_ps);
    }

    return hdl;
}

void FliTimerCache::put_timer(FliTimedCbHdl* hdl)
{
    free_list.push(hdl);
}

GPI_ENTRY_POINT(fli, cocotb_init);

