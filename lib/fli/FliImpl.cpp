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

bool FliImpl::isValueConst(int kind)
{
    return (kind == accGeneric || kind == accVHDLConstant);
}

bool FliImpl::isValueLogic(mtiTypeIdT type)
{
    mtiInt32T numEnums = mti_TickLength(type);
    if (numEnums == 2) {
        char **enum_values = mti_GetEnumValues(type);
        std::string str0 = enum_values[0];
        std::string str1  = enum_values[1];

        if (str0.compare("'0'") == 0 && str1.compare("'1'") == 0) {
            return true;
        }
    } else if (numEnums == 9) {
        const char enums[9][4] = {"'U'","'X'","'0'","'1'","'Z'","'W'","'L'","'H'","'-'"};
        char **enum_values = mti_GetEnumValues(type);

        for (int i = 0; i < 9; i++) {
            std::string str = enum_values[i];
            if (str.compare(enums[i]) != 0) {
                return false;
            }
        }

        return true;
    }

    return false;
}

bool FliImpl::isValueChar(mtiTypeIdT type)
{
    return (mti_TickLength(type) == 256);
}

bool FliImpl::isValueBoolean(mtiTypeIdT type)
{
    if (mti_TickLength(type) == 2) {
        char **enum_values = mti_GetEnumValues(type);
        std::string strFalse = enum_values[0];
        std::string strTrue  = enum_values[1];

        if (strFalse.compare("false") == 0 && strTrue.compare("true") == 0) {
            return true;
        }
    }

    return false;
}

GpiObjHdl *FliImpl::create_gpi_obj(std::string &name, std::string &fq_name)
{
    GpiObjHdl *new_obj = NULL;

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    void * hdl;

    if ((hdl = mti_FindRegion(&writable[0])) != NULL) {
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
        new_obj = new GpiObjHdl(this, hdl, GPI_MODULE);
    } else {
        bool is_var;
        bool is_const;
        mtiTypeIdT valType;
        mtiTypeKindT typeKind;

        if ((hdl = mti_FindSignal(&writable[0])) != NULL) {
            LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
            is_var   = false;
            is_const = false;
            valType  = mti_GetSignalType(static_cast<mtiSignalIdT>(hdl));
        } else if ((hdl = mti_FindVar(&writable[0])) != NULL) {
            LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
            is_var   = true;
            is_const = isValueConst(mti_GetVarKind(static_cast<mtiVariableIdT>(hdl)));
            valType  = mti_GetVarType(static_cast<mtiVariableIdT>(hdl));
        } else {
            LOG_DEBUG("Didn't find anything named %s", &writable[0]);
            return NULL;
        }

        typeKind = mti_GetTypeKind(valType);

        switch (typeKind) {
            case MTI_TYPE_ENUM:
                if (isValueLogic(valType)) {
                    new_obj = new FliLogicObjHdl(this, hdl, GPI_ENUM, is_const, is_var, valType, typeKind);
                } else if (isValueBoolean(valType) || isValueChar(valType)) {
                    new_obj = new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const, is_var, valType, typeKind);
                } else {
                    new_obj = new FliEnumObjHdl(this, hdl, GPI_ENUM, is_const, is_var, valType, typeKind);
                }
                break;
            case MTI_TYPE_SCALAR:
            case MTI_TYPE_PHYSICAL:
                new_obj = new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const, is_var, valType, typeKind);
                break;
            case MTI_TYPE_REAL:
                new_obj = new FliRealObjHdl(this, hdl, GPI_REAL, is_const, is_var, valType, typeKind);
                break;
            case MTI_TYPE_ARRAY: {
                    mtiTypeIdT   elemType     = mti_GetArrayElementType(valType);
                    mtiTypeKindT elemTypeKind = mti_GetTypeKind(elemType);

                    switch (elemTypeKind) {
                        case MTI_TYPE_ENUM:
                            if (isValueLogic(elemType)) {
                                new_obj = new FliLogicObjHdl(this, hdl, GPI_ARRAY, is_const, is_var, valType, typeKind); // std_logic_vector
                            } else if (isValueChar(elemType)) {
                                new_obj = new FliStringObjHdl(this, hdl, GPI_STRING, is_const, is_var, valType, typeKind);
                            } else {
                                new_obj = new GpiObjHdl(this, hdl, GPI_MODULE); // array of enums
                            }
                            break;
                        default:
                            new_obj = new GpiObjHdl(this, hdl, GPI_MODULE);// array of (array, Integer, Real, Record, etc.) 
                    }
                }
                break;
            case MTI_TYPE_RECORD:
                new_obj = new GpiObjHdl(this, hdl, GPI_STRUCTURE);
                break;
            default:
                LOG_ERROR("Unable to handle object type for %s (%d)", name.c_str(), typeKind);
                return NULL;
        }
    }

    if (NULL == new_obj) {
        LOG_DEBUG("Didn't find anything named %s", &writable[0]);
        return NULL;
    }

    if (new_obj->initialise(name,fq_name) < 0) {
        LOG_ERROR("Failed to initialise the handle %s", name.c_str());
        return NULL;
    }

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
    } else if (parent->get_type() == GPI_MODULE) {
        fq_name += "/" + name;
    } else if (parent->get_type() == GPI_STRUCTURE) {
        fq_name += "." + name;
    } else {
        LOG_ERROR("FLI: Parent of type %d must be of type GPI_MODULE or GPI_STRUCTURE to have a child.", parent->get_type());
        return NULL;
    }
 
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
    if (parent->get_type() == GPI_MODULE or parent->get_type() == GPI_ARRAY) {
        char buff[15];
        snprintf(buff, 15, "(%u)", index);
        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        LOG_DEBUG("Looking for index %u from %s", index, parent->get_name_str());

        return create_gpi_obj(name, fq_name);
    } else {
        LOG_ERROR("FLI: Parent of type %d must be of type GPI_MODULE or GPI_ARRAY to have an index.", parent->get_type());
        return NULL;
    }
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

