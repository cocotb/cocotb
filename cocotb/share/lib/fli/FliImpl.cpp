/******************************************************************************
* Copyright (c) 2014, 2018 Potential Ventures Ltd
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

#include <cstddef>
#include <string>
#include <vector>

#include "FliImpl.h"
#include "mti.h"
#include "acc_vhdl.h"   // Messy :(
#include "acc_user.h"

extern "C" {
static FliProcessCbHdl *sim_init_cb;
static FliProcessCbHdl *sim_finish_cb;
static FliImpl         *fli_table;

bool fli_is_logic(mtiTypeIdT type)
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

bool fli_is_char(mtiTypeIdT type)
{
    const int NUM_ENUMS_IN_CHAR_TYPE = 256;
    return (mti_TickLength(type) == NUM_ENUMS_IN_CHAR_TYPE);
}

bool fli_is_boolean(mtiTypeIdT type)
{
    if (mti_TickLength(type) == 2) {
        char **enum_values = mti_GetEnumValues(type);
        std::string strFalse = enum_values[0];
        std::string strTrue  = enum_values[1];

        if (strFalse.compare("FALSE") == 0 && strTrue.compare("TRUE") == 0) {
            return true;
        }
    }

    return false;
}

bool fli_is_signal(void *hdl)
{
    return (acc_fetch_type(hdl) == accSignal || acc_fetch_fulltype(hdl) == accAliasSignal);
}

bool fli_is_variable(void *hdl)
{
    mtiTypeIdT _typeid = mti_GetVarType(static_cast<mtiVariableIdT>(hdl));
    PLI_INT32  _type   = mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));

    return ((mti_GetTypeKind(_typeid) == acc_fetch_type(hdl)) && (_type == accAliasConstant
                                                                     || _type == accAliasGeneric
                                                                     || _type == accVHDLConstant
                                                                     || _type == accGeneric
                                                                     || _type == accVariable));
}

bool fli_is_region(void *hdl)
{
    return (!fli_is_signal(hdl) && !fli_is_variable(hdl) && VS_TYPE_IS_VHDL(acc_fetch_fulltype(hdl)));
}

PLI_INT32 fli_handle_fulltype(void *hdl)
{
    if (fli_is_variable(hdl))
        return mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));
    else
        return acc_fetch_fulltype(hdl);
}

bool fli_is_const(void *hdl)
{
    PLI_INT32 _type = fli_handle_fulltype(hdl);
    return (_type == accGeneric || _type == accVHDLConstant
                                || _type == accAliasConstant
                                || _type == accAliasGeneric);
}

} //extern "C"

void FliImpl::sim_end(void)
{
    if (GPI_DELETE != sim_finish_cb->get_call_state()) {
        sim_finish_cb->set_call_state(GPI_DELETE);
        if (mti_NowUpper() == 0 && mti_Now() == 0 && mti_Delta() == 0) {
            mti_Quit();
        } else {
            mti_Break();
        }
    }
}

gpi_objtype_t FliImpl::get_gpi_obj_type(mtiTypeIdT _typeid)
{
    gpi_objtype_t rv;

    switch (mti_GetTypeKind(_typeid)) {
        case MTI_TYPE_ENUM:
            if (fli_is_logic(_typeid))
                rv = GPI_REGISTER;
            else if (fli_is_boolean(_typeid) || fli_is_char(_typeid))
                rv = GPI_INTEGER;
            else
                rv = GPI_ENUM;
            break;
        case MTI_TYPE_SCALAR:
        case MTI_TYPE_PHYSICAL:
            rv = GPI_INTEGER;
            break;
        case MTI_TYPE_REAL:
            rv = GPI_REAL;
            break;
        case MTI_TYPE_ARRAY: {
                mtiTypeIdT   elemType     = mti_GetArrayElementType(_typeid);
                mtiTypeKindT elemTypeKind = mti_GetTypeKind(elemType);

                switch (elemTypeKind) {
                    case MTI_TYPE_ENUM:
                        if (fli_is_logic(elemType))
                            rv = GPI_REGISTER;
                        else if (fli_is_char(elemType))
                            rv = GPI_STRING;
                        else
                            rv = GPI_ARRAY;
                        break;
                    default:
                        rv = GPI_ARRAY;
                }
            }
            break;
        case MTI_TYPE_RECORD:
            rv = GPI_STRUCTURE;
            break;
        default:
            rv = GPI_UNKNOWN;
    }

    return rv;
}


GpiObjHdl *FliImpl::create_gpi_obj_from_handle(mtiRegionIdT hdl, std::string &name, std::string &fq_name)
{
    GpiObjHdl *new_obj = NULL;

    LOG_DEBUG("FLI::Attempting to create GPI object (%s) from handle.", fq_name.c_str());

    if (!VS_TYPE_IS_VHDL(acc_fetch_fulltype(hdl))) {
        LOG_DEBUG("Handle is not a VHDL type.");
        return NULL;
    }

    /* Need a Pseudo-region to handle generate loops in a consistent manner across interfaces
     * and across the different methods of accessing data.
     */
    std::string rgn_name = mti_GetRegionName(hdl);
    if (name != rgn_name) {
        LOG_DEBUG("Found pseudo-region %s -> %p", fq_name.c_str(), hdl);
        new_obj = new FliObjHdl(this, static_cast<mtiRegionIdT>(hdl), GPI_GENARRAY);
    } else {
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
        new_obj = new FliObjHdl(this, static_cast<mtiRegionIdT>(hdl), GPI_MODULE);
    }

    if (new_obj->initialise(name, fq_name)) {
        LOG_ERROR("Failed to initialise the handle %s", name.c_str());
        delete new_obj;
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *FliImpl::create_gpi_obj_from_handle(mtiSignalIdT hdl, std::string &name, std::string &fq_name)
{
    GpiObjHdl *new_obj = NULL;

    LOG_DEBUG("FLI::Attempting to create GPI object (%s) from handle.", fq_name.c_str());

    switch (get_gpi_obj_type(mti_GetSignalType(hdl))) {
        case GPI_ENUM:
            new_obj = new FliEnumObjHdl(this, hdl);
            break;
        case GPI_REGISTER:
            new_obj = new FliLogicObjHdl(this, hdl);
            break;
        case GPI_INTEGER:
            new_obj = new FliIntObjHdl(this, hdl);
            break;
        case GPI_REAL:
            new_obj = new FliRealObjHdl(this, hdl);
            break;
        case GPI_STRING:
            new_obj = new FliStringObjHdl(this, hdl);
            break;
        case GPI_ARRAY:
            new_obj = new FliArrayObjHdl(this, hdl);
            break;
        case GPI_STRUCTURE:
            new_obj = new FliRecordObjHdl(this, hdl);
            break;
        default:
            return NULL;
    }

    if (new_obj->initialise(name, fq_name)) {
        LOG_ERROR("Failed to initialise the handle %s", name.c_str());
        delete new_obj;
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *FliImpl::create_gpi_obj_from_handle(mtiVariableIdT hdl, std::string &name, std::string &fq_name)
{
    GpiObjHdl *new_obj = NULL;

    bool is_const = fli_is_const(hdl);

    LOG_DEBUG("FLI::Attempting to create GPI object (%s) from handle.", fq_name.c_str());

    switch (get_gpi_obj_type(mti_GetVarType(hdl))) {
        case GPI_ENUM:
            new_obj = new FliEnumObjHdl(this, hdl, is_const);
            break;
        case GPI_REGISTER:
            new_obj = new FliLogicObjHdl(this, hdl, is_const);
            break;
        case GPI_INTEGER:
            new_obj = new FliIntObjHdl(this, hdl, is_const);
            break;
        case GPI_REAL:
            new_obj = new FliRealObjHdl(this, hdl, is_const);
            break;
        case GPI_STRING:
            new_obj = new FliStringObjHdl(this, hdl, is_const);
            break;
        case GPI_ARRAY:
            new_obj = new FliArrayObjHdl(this, hdl, is_const);
            break;
        case GPI_STRUCTURE:
            new_obj = new FliRecordObjHdl(this, hdl, is_const);
            break;
        default:
            return NULL;
    }

    if (new_obj->initialise(name, fq_name)) {
        LOG_ERROR("Failed to initialise the handle %s", name.c_str());
        delete new_obj;
        return NULL;
    }

    return new_obj;
}

GpiObjHdl* FliImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent)
{
    LOG_DEBUG("Trying to convert a raw handle to an FLI Handle.");

    const char * c_name     = acc_fetch_name(raw_hdl);
    const char * c_fullname = acc_fetch_fullname(raw_hdl);

    if (!c_name) {
        LOG_DEBUG("Unable to query the name of the raw handle.");
        return NULL;
    }

    std::string name    = c_name;
    std::string fq_name = c_fullname;

    if (fli_is_region(raw_hdl))
        return create_gpi_obj_from_handle(static_cast<mtiRegionIdT>(raw_hdl), name, fq_name);
    else if (fli_is_signal(raw_hdl))
        return create_gpi_obj_from_handle(static_cast<mtiSignalIdT>(raw_hdl), name, fq_name);
    else if (fli_is_variable(raw_hdl))
        return create_gpi_obj_from_handle(static_cast<mtiVariableIdT>(raw_hdl), name, fq_name);
    else
        return NULL;
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    bool search_rgn       = false;
    bool search_sig       = false;
    bool search_var       = false;

    std::string   fq_name  = parent->get_fullname();
    gpi_objtype_t obj_type = parent->get_type();

    if (fq_name == "/") {
        fq_name += name;
        search_rgn = true;
        search_sig = true;
        search_var = true;
    } else if (obj_type == GPI_MODULE) {
        fq_name += "/" + name;
        search_rgn = true;
        search_sig = true;
        search_var = true;
    } else if (obj_type == GPI_STRUCTURE) {
        fq_name += "." + name;
        search_rgn = false;
        search_var = fli_is_variable(parent->get_handle<void *>());
        search_sig = !search_var;
    } else {
        LOG_ERROR("FLI: Parent of type %d must be of type GPI_MODULE or GPI_STRUCTURE to have a child.", obj_type);
        return NULL;
    }

    LOG_DEBUG("Looking for child %s from %s", name.c_str(), parent->get_name_str());

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    mtiRegionIdT rgn;
    mtiSignalIdT sig;
    mtiVariableIdT var;

    if (search_rgn && (rgn = mti_FindRegion(&writable[0])) != NULL) {
        /* Generate Loops have inconsistent behavior across fli.  A "name"
         * without an index, i.e. dut.loop vs dut.loop(0), will attempt to map
         * to index 0, if index 0 exists.  If it doesn't then it won't find anything.
         *
         * If this unique case is hit, we need to create the Pseudo-region, with the handle
         * being equivalent to the parent region.
         */
        if (acc_fetch_fulltype(rgn) == accForGenerate) {
            rgn = mti_HigherRegion(rgn);
        }

        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), rgn);
        return create_gpi_obj_from_handle(rgn, name, fq_name);
    } else if (search_sig && (sig = mti_FindSignal(&writable[0])) != NULL) {
        LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), sig);
        return create_gpi_obj_from_handle(sig, name, fq_name);
    } else if (search_var && (var = mti_FindVar(&writable[0])) != NULL) {
        LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), var);
        return create_gpi_obj_from_handle(var, name, fq_name);
    } else if (search_rgn){
        /* If not found, check to see if the name of a generate loop and create a pseudo-region */
        for (rgn = mti_FirstLowerRegion(parent->get_handle<mtiRegionIdT>()); rgn != NULL; rgn = mti_NextRegion(rgn)) {
            if (acc_fetch_fulltype(rgn) == accForGenerate) {
                std::string rgn_name = mti_GetRegionName(rgn);
                if (rgn_name.compare(0,name.length(),name) == 0) {
                    return create_gpi_obj_from_handle(mti_HigherRegion(rgn), name, fq_name);
                }
            }
        }
    }

    LOG_DEBUG("Didn't find anything named %s", &writable[0]);
    return NULL;
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(int32_t index, GpiObjHdl *parent)
{
    gpi_objtype_t obj_type = parent->get_type();

    char buff[14];

    LOG_DEBUG("Looking for index %d from %s", index, parent->get_name_str());

    if (obj_type == GPI_GENARRAY) {
        mtiRegionIdT rgn;

        snprintf(buff, 14, "(%d)", index);

        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        std::vector<char> writable(fq_name.begin(), fq_name.end());
        writable.push_back('\0');

        if ((rgn = mti_FindRegion(&writable[0])) != NULL) {
            LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), rgn);
        } else {
            LOG_DEBUG("Didn't find anything named %s", &writable[0]);
            return NULL;
        }

        return create_gpi_obj_from_handle(rgn, name, fq_name);
    } else if (obj_type == GPI_REGISTER || obj_type == GPI_ARRAY || obj_type == GPI_STRING) {
        if (!parent->get_indexable()) {
            LOG_DEBUG("Handle is not indexable");
            return NULL;
        }

        int left  = parent->get_range_left();
        int right = parent->get_range_right();
        int32_t norm_idx;

        if (left > right) {
            norm_idx = left - index;
        } else {
            norm_idx = index - left;
        }

        if (norm_idx < 0 || norm_idx >= parent->get_num_elems()) {
            LOG_DEBUG("Invalid index: %d is out of range [%d,%d]", index, left, right);
            return NULL;
        }

        snprintf(buff, 14, "(%d)", index);

        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        void *parent_hdl = parent->get_handle<void *>();

        if (fli_is_variable(parent_hdl)) {
            mtiVariableIdT *handles = mti_GetVarSubelements(static_cast<mtiVariableIdT>(parent_hdl), NULL);
            mtiVariableIdT hdl;

            if (handles == NULL) {
                LOG_DEBUG("Error allocating memory for array elements");
                return NULL;
            }
            hdl = handles[norm_idx];
            mti_VsimFree(handles);
            return create_gpi_obj_from_handle(hdl, name, fq_name);
        } else {
            mtiSignalIdT *handles = mti_GetSignalSubelements(static_cast<mtiSignalIdT>(parent_hdl), NULL);
            mtiSignalIdT hdl;

            if (handles == NULL) {
                LOG_DEBUG("Error allocating memory for array elements");
                return NULL;
            }
            hdl = handles[norm_idx];
            mti_VsimFree(handles);
            return create_gpi_obj_from_handle(hdl, name, fq_name);
        }

    } else {
        LOG_ERROR("FLI: Parent of type %d must be of type GPI_GENARRAY, GPI_REGISTER, GPI_ARRAY, or GPI_STRING to have an index.", obj_type);
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

void FliImpl::get_sim_precision(int32_t *precision)
{
    *precision = mti_GetResolutionLimit();
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

    return create_gpi_obj_from_handle(root, root_name, root_fullname);

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
    GpiIterator *new_iter = NULL;

    switch (type) {
        case GPI_OBJECTS:
            new_iter = new FliIterator(this, obj_hdl);
            break;
        default:
            LOG_WARN("Other iterator types not implemented yet");
            break;
    }

    return new_iter;
}

void fli_mappings(GpiIteratorMapping<int, FliIterator::OneToMany> &map)
{
    FliIterator::OneToMany region_options[] = {
        FliIterator::OTM_CONSTANTS,
        FliIterator::OTM_SIGNALS,
        FliIterator::OTM_REGIONS,
        FliIterator::OTM_END,
    };
    map.add_to_options(accArchitecture, &region_options[0]);
    map.add_to_options(accEntityVitalLevel0, &region_options[0]);
    map.add_to_options(accArchVitalLevel0, &region_options[0]);
    map.add_to_options(accArchVitalLevel1, &region_options[0]);
    map.add_to_options(accBlock, &region_options[0]);
    map.add_to_options(accCompInst, &region_options[0]);
    map.add_to_options(accDirectInst, &region_options[0]);
    map.add_to_options(accinlinedBlock, &region_options[0]);
    map.add_to_options(accinlinedinnerBlock, &region_options[0]);
    map.add_to_options(accGenerate, &region_options[0]);
    map.add_to_options(accIfGenerate, &region_options[0]);
#ifdef accElsifGenerate
    map.add_to_options(accElsifGenerate, &region_options[0]);
#endif
#ifdef accElseGenerate
    map.add_to_options(accElseGenerate, &region_options[0]);
#endif
#ifdef accCaseGenerate
    map.add_to_options(accCaseGenerate, &region_options[0]);
#endif
#ifdef accCaseOTHERSGenerate
    map.add_to_options(accCaseOTHERSGenerate, &region_options[0]);
#endif
    map.add_to_options(accForGenerate, &region_options[0]);
    map.add_to_options(accConfiguration, &region_options[0]);

    FliIterator::OneToMany signal_options[] = {
        FliIterator::OTM_SIGNAL_SUB_ELEMENTS,
        FliIterator::OTM_END,
    };
    map.add_to_options(accSignal, &signal_options[0]);
    map.add_to_options(accSignalBit, &signal_options[0]);
    map.add_to_options(accSignalSubComposite, &signal_options[0]);
    map.add_to_options(accAliasSignal, &signal_options[0]);

    FliIterator::OneToMany variable_options[] = {
        FliIterator::OTM_VARIABLE_SUB_ELEMENTS,
        FliIterator::OTM_END,
    };
    map.add_to_options(accVariable, &variable_options[0]);
    map.add_to_options(accGeneric, &variable_options[0]);
    map.add_to_options(accGenericConstant, &variable_options[0]);
    map.add_to_options(accAliasConstant, &variable_options[0]);
    map.add_to_options(accAliasGeneric, &variable_options[0]);
    map.add_to_options(accAliasVariable, &variable_options[0]);
    map.add_to_options(accVHDLConstant, &variable_options[0]);
}

GpiIteratorMapping<int, FliIterator::OneToMany> FliIterator::iterate_over(fli_mappings);

FliIterator::FliIterator(GpiImplInterface *impl, GpiObjHdl *hdl) : GpiIterator(impl, hdl),
                                                                   m_vars(),
                                                                   m_sigs(),
                                                                   m_regs(),
                                                                   m_currentHandles(NULL)
{
    int type = fli_handle_fulltype(m_parent->get_handle<void *>());

    LOG_DEBUG("fli_iterator::Create iterator for %s of type %d:%s", m_parent->get_fullname().c_str(), type, acc_fetch_type_str(type));

    if (NULL == (selected = iterate_over.get_options(type))) {
        LOG_WARN("FLI: Implementation does not know how to iterate over %s(%d)",
                 acc_fetch_type_str(type), type);
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin(); one2many != selected->end(); one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY && *one2many != FliIterator::OTM_REGIONS) {
            LOG_DEBUG("fli_iterator OneToMany=%d skipped for GPI_GENARRAY type", *one2many);
            continue;
        }

        populate_handle_list(*one2many);

        switch (*one2many) {
            case FliIterator::OTM_CONSTANTS:
            case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
                m_currentHandles = &m_vars;
                m_iterator = m_vars.begin();
                break;
            case FliIterator::OTM_SIGNALS:
            case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
                m_currentHandles = &m_sigs;
                m_iterator = m_sigs.begin();
                break;
            case FliIterator::OTM_REGIONS:
                m_currentHandles = &m_regs;
                m_iterator = m_regs.begin();
                break;
            default:
                LOG_WARN("Unhandled OneToMany Type (%d)", *one2many);
        }

        if (m_iterator != m_currentHandles->end())
            break;

        LOG_DEBUG("fli_iterator OneToMany=%d returned NULL", *one2many);
    }

    if (m_iterator == m_currentHandles->end()) {
        LOG_DEBUG("fli_iterator return NULL for all relationships on %s (%d) kind:%s",
                  m_parent->get_name_str(), type, acc_fetch_type_str(type));
        selected = NULL;
        return;
    }

    LOG_DEBUG("Created iterator working from scope %d",
              *one2many);
}

GpiIterator::Status FliIterator::next_handle(std::string &name, GpiObjHdl **hdl, void **raw_hdl)
{
    HANDLE obj;
    GpiObjHdl *new_obj;

    if (!selected)
        return GpiIterator::END;

    gpi_objtype_t obj_type  = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try next one until a new object is found
     */
    do {
        obj = NULL;

        if (m_iterator != m_currentHandles->end()) {
            obj = *m_iterator++;

            /* For GPI_GENARRAY, only allow the generate statements through that match the name
             * of the generate block.
             */
            if (obj_type == GPI_GENARRAY) {
                if (acc_fetch_fulltype(obj) == accForGenerate) {
                    std::string rgn_name = mti_GetRegionName(static_cast<mtiRegionIdT>(obj));
                    if (rgn_name.compare(0,parent_name.length(),parent_name) != 0) {
                        obj = NULL;
                        continue;
                    }
                } else {
                    obj = NULL;
                    continue;
                }
            }

            break;
        } else {
            LOG_DEBUG("No more valid handles in the current OneToMany=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != FliIterator::OTM_REGIONS) {
            LOG_DEBUG("fli_iterator OneToMany=%d skipped for GPI_GENARRAY type", *one2many);
            continue;
        }

        populate_handle_list(*one2many);

        switch (*one2many) {
            case FliIterator::OTM_CONSTANTS:
            case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
                m_currentHandles = &m_vars;
                m_iterator = m_vars.begin();
                break;
            case FliIterator::OTM_SIGNALS:
            case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
                m_currentHandles = &m_sigs;
                m_iterator = m_sigs.begin();
                break;
            case FliIterator::OTM_REGIONS:
                m_currentHandles = &m_regs;
                m_iterator = m_regs.begin();
                break;
            default:
                LOG_WARN("Unhandled OneToMany Type (%d)", *one2many);
        }
    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("No more children, all relationships tested");
        return GpiIterator::END;
    }

    char *c_name;
    switch (*one2many) {
        case FliIterator::OTM_CONSTANTS:
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            c_name = mti_GetVarName(static_cast<mtiVariableIdT>(obj));
            break;
        case FliIterator::OTM_SIGNALS:
            c_name = mti_GetSignalName(static_cast<mtiSignalIdT>(obj));
            break;
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            c_name = mti_GetSignalNameIndirect(static_cast<mtiSignalIdT>(obj), NULL, 0);
            break;
        case FliIterator::OTM_REGIONS:
            c_name = mti_GetRegionName(static_cast<mtiRegionIdT>(obj));
            break;
        default:
            LOG_WARN("Unhandled OneToMany Type (%d)", *one2many);
    }

    if (!c_name) {
        if (!VS_TYPE_IS_VHDL(fli_handle_fulltype(obj))) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and create
     * the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region object.
     *       Otherwise a list would be required and checked while iterating
     */
    if (*one2many == FliIterator::OTM_REGIONS && obj_type != GPI_GENARRAY && fli_handle_fulltype(obj) == accForGenerate) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.find_last_of("(");

        if (found != std::string::npos && found != 0) {
            name        = idx_str.substr(0,found);
            obj         = m_parent->get_handle<HANDLE>();
        } else {
            LOG_WARN("Unhandled Generate Loop Format - %s", name.c_str());
            name = c_name;
        }
    } else {
        name = c_name;
    }

    if (*one2many == FliIterator::OTM_SIGNAL_SUB_ELEMENTS) {
        mti_VsimFree(c_name);
    }

    std::string fq_name = m_parent->get_fullname();
    if (fq_name == "/") {
        fq_name += name;
    } else if (*one2many == FliIterator::OTM_SIGNAL_SUB_ELEMENTS ||
               *one2many == FliIterator::OTM_VARIABLE_SUB_ELEMENTS ||
                obj_type == GPI_GENARRAY) {
        std::size_t found;

        if (obj_type == GPI_STRUCTURE) {
            found = name.find_last_of(".");
        } else {
            found = name.find_last_of("(");
        }

        if (found != std::string::npos) {
            fq_name += name.substr(found);
            if (obj_type != GPI_GENARRAY) {
                name = name.substr(found+1);
            }
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "/" + name;
        }
    } else {
        fq_name += "/" + name;
    }

    FliImpl *fli_impl = reinterpret_cast<FliImpl*>(m_impl);
    switch (*one2many) {
        case FliIterator::OTM_CONSTANTS:
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            new_obj = fli_impl->create_gpi_obj_from_handle(static_cast<mtiVariableIdT>(obj), name, fq_name);
            break;
        case FliIterator::OTM_SIGNALS:
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            new_obj = fli_impl->create_gpi_obj_from_handle(static_cast<mtiSignalIdT>(obj), name, fq_name);
            break;
        case FliIterator::OTM_REGIONS:
            new_obj = fli_impl->create_gpi_obj_from_handle(static_cast<mtiRegionIdT>(obj), name, fq_name);
            break;
        default:
            break;
    }

    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else {
        return GpiIterator::NOT_NATIVE;
    }
}

void FliIterator::populate_handle_list(FliIterator::OneToMany childType)
{
    switch (childType) {
        case FliIterator::OTM_CONSTANTS: {
                mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
                mtiVariableIdT id;

                for (id = mti_FirstVarByRegion(parent); id; id = mti_NextVar()) {
                    if (id) {
                        m_vars.push_back(id);
                    }
                }
            }
            break;
        case FliIterator::OTM_SIGNALS: {
                mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
                mtiSignalIdT id;

                for (id = mti_FirstSignal(parent); id; id = mti_NextSignal()) {
                    if (id) {
                        m_sigs.push_back(id);
                    }
                }
            }
            break;
        case FliIterator::OTM_REGIONS: {
                mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
                mtiRegionIdT id;

                for (id = mti_FirstLowerRegion(parent); id; id = mti_NextRegion(id)) {
                    if (id) {
                        m_regs.push_back(id);
                    }
                }
            }
            break;
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            if (m_parent->get_type() == GPI_STRUCTURE || m_parent->get_indexable()) {
                mtiSignalIdT parent = m_parent->get_handle<mtiSignalIdT>();

                mtiTypeIdT type = mti_GetSignalType(parent);
                mtiSignalIdT *ids = mti_GetSignalSubelements(parent,NULL);

                for (int i = 0; i < mti_TickLength(type); i++) {
                    m_sigs.push_back(ids[i]);
                }
                mti_VsimFree(ids);
            }
            break;
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            if (m_parent->get_type() == GPI_STRUCTURE || m_parent->get_indexable()) {
                mtiVariableIdT parent = m_parent->get_handle<mtiVariableIdT>();

                mtiTypeIdT type = mti_GetVarType(parent);
                mtiVariableIdT *ids = mti_GetVarSubelements(parent,NULL);

                for (int i = 0; i < mti_TickLength(type); i++) {
                    m_vars.push_back(ids[i]);
                }

                mti_VsimFree(ids);
            }
            break;
        default:
            LOG_WARN("Unhandled OneToMany Type (%d)", childType);
    }
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

extern "C" {

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

static void register_initial_callback(void)
{
    FENTER
    sim_init_cb = new FliStartupCbHdl(fli_table);
    sim_init_cb->arm_callback();
    FEXIT
}

static void register_final_callback(void)
{
    FENTER
    sim_finish_cb = new FliShutdownCbHdl(fli_table);
    sim_finish_cb->arm_callback();
    FEXIT
}

static void register_embed(void)
{
    fli_table = new FliImpl("FLI");
    gpi_register_impl(fli_table);
    gpi_load_extra_libs();
}


void cocotb_init(void)
{
    LOG_INFO("cocotb_init called\n");
    register_embed();
    register_initial_callback();
    register_final_callback();
}

} // extern "C"

GPI_ENTRY_POINT(fli, register_embed);

