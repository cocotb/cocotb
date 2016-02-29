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
}

void FliImpl::sim_end(void)
{
    const char *stop = "stop";
    if (GPI_DELETE != sim_finish_cb->get_call_state()) {
        sim_finish_cb->set_call_state(GPI_DELETE);
        mti_Cmd(stop);
    }

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
    const int NUM_ENUMS_IN_CHAR_TYPE = 256;
    return (mti_TickLength(type) == NUM_ENUMS_IN_CHAR_TYPE);
}

bool FliImpl::isValueBoolean(mtiTypeIdT type)
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

bool FliImpl::isTypeValue(int type)
{
    return (type == accAlias || type == accVHDLConstant || type == accGeneric
               || type == accVariable || type == accSignal);
}

bool FliImpl::isTypeSignal(int type, int full_type)
{
    return (type == accSignal || full_type == accAliasSignal);
}

GpiObjHdl *FliImpl::create_gpi_obj_from_handle(void *hdl, std::string &name, std::string &fq_name, int accType, int accFullType)
{
    GpiObjHdl *new_obj = NULL;

    LOG_DEBUG("Attepmting to create GPI object from handle (Type=%d, FullType=%d).", accType, accFullType);
    if (!VS_TYPE_IS_VHDL(accFullType)) {
        LOG_DEBUG("Handle is not a VHDL type.");
        return NULL;
    }

    if (!isTypeValue(accType)) {
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
        new_obj = new FliObjHdl(this, hdl, GPI_MODULE, accType, accFullType);
    } else {
        bool is_var;
        bool is_const;
        mtiTypeIdT valType;
        mtiTypeKindT typeKind;

        if (isTypeSignal(accType, accFullType)) {
            LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
            is_var   = false;
            is_const = false;
            valType  = mti_GetSignalType(static_cast<mtiSignalIdT>(hdl));
        } else {
            LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
            is_var   = true;
            is_const = isValueConst(accFullType);
            valType  = mti_GetVarType(static_cast<mtiVariableIdT>(hdl));
        }

        typeKind = mti_GetTypeKind(valType);

        switch (typeKind) {
            case MTI_TYPE_ENUM:
                if (isValueLogic(valType)) {
                    new_obj = new FliLogicObjHdl(this, hdl, GPI_ENUM, is_const, accType, accFullType, is_var, valType, typeKind);
                } else if (isValueBoolean(valType) || isValueChar(valType)) {
                    new_obj = new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const, accType, accFullType, is_var, valType, typeKind);
                } else {
                    new_obj = new FliEnumObjHdl(this, hdl, GPI_ENUM, is_const, accType, accFullType, is_var, valType, typeKind);
                }
                break;
            case MTI_TYPE_SCALAR:
            case MTI_TYPE_PHYSICAL:
                new_obj = new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const, accType, accFullType, is_var, valType, typeKind);
                break;
            case MTI_TYPE_REAL:
                new_obj = new FliRealObjHdl(this, hdl, GPI_REAL, is_const, accType, accFullType, is_var, valType, typeKind);
                break;
            case MTI_TYPE_ARRAY: {
                    mtiTypeIdT   elemType     = mti_GetArrayElementType(valType);
                    mtiTypeKindT elemTypeKind = mti_GetTypeKind(elemType);

                    switch (elemTypeKind) {
                        case MTI_TYPE_ENUM:
                            if (isValueLogic(elemType)) {
                                new_obj = new FliLogicObjHdl(this, hdl, GPI_ARRAY, is_const, accType, accFullType, is_var, valType, typeKind); // std_logic_vector
                            } else if (isValueChar(elemType)) {
                                new_obj = new FliStringObjHdl(this, hdl, GPI_STRING, is_const, accType, accFullType, is_var, valType, typeKind);
                            } else {
                                new_obj = new FliValueObjHdl(this, hdl, GPI_MODULE, is_const, accType, accFullType, is_var, valType, typeKind); // array of enums
                            }
                            break;
                        default:
                            new_obj = new FliValueObjHdl(this, hdl, GPI_MODULE, is_const, accType, accFullType, is_var, valType, typeKind);// array of (array, Integer, Real, Record, etc.) 
                    }
                }
                break;
            case MTI_TYPE_RECORD:
                new_obj = new FliObjHdl(this, hdl, GPI_STRUCTURE, accType, accFullType);
                break;
            default:
                LOG_ERROR("Unable to handle object type for %s (%d)", name.c_str(), typeKind);
                return NULL;
        }
    }

    if (NULL == new_obj) {
        LOG_DEBUG("Didn't find anything named %s", fq_name.c_str());
        return NULL;
    }

    if (new_obj->initialise(name,fq_name) < 0) {
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

    PLI_INT32 accType     = acc_fetch_type(raw_hdl);
    PLI_INT32 accFullType = acc_fetch_fulltype(raw_hdl);

    return create_gpi_obj_from_handle(raw_hdl, name, fq_name, accType, accFullType);
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

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    HANDLE hdl;
    PLI_INT32 accType;
    PLI_INT32 accFullType;

    if ((hdl = mti_FindRegion(&writable[0])) != NULL) {
        accType     = acc_fetch_type(hdl);
        accFullType = acc_fetch_fulltype(hdl);
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else if ((hdl = mti_FindSignal(&writable[0])) != NULL) {
        accType     = acc_fetch_type(hdl);
        accFullType = acc_fetch_fulltype(hdl);
        LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else if ((hdl = mti_FindVar(&writable[0])) != NULL) {
        accFullType = accType = mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));
        LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else {
        LOG_DEBUG("Didn't find anything named %s", &writable[0]);
        return NULL;
    }

    /* Added to behave like vhpi interface.  Handle.py will does not support a handle to a 
     * "for generate" loop that doesn't contain an index.
     *
     * VHDL (in dut):
     *    a_loop : for i in 0 to 9 generate
     *       ...
     *    end generate a_loop;
     *
     * FLI will return a vaild handle to "/dut/a_loop" as well as /dut/a_loop(0)
     */
    if (accFullType == accForGenerate) {
        return NULL;
    }

    return create_gpi_obj_from_handle(hdl, name, fq_name, accType, accFullType);
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl*  FliImpl::native_check_create(uint32_t index, GpiObjHdl *parent)
{
    if (parent->get_type() == GPI_MODULE || parent->get_type() == GPI_ARRAY || parent->get_type() == GPI_STRING) {
        char buff[15];
        int type;

        LOG_DEBUG("Looking for index %u from %s", index, parent->get_name_str());

        if (parent->get_type() == GPI_MODULE) {
            FliObjHdl *fli_obj = static_cast<FliObjHdl *>(parent);
            type = fli_obj->get_acc_type();
        } else {
            FliSignalObjHdl *fli_obj = static_cast<FliSignalObjHdl *>(parent);
            type = fli_obj->get_acc_type();
        }

        /* To behave like the current VHPI interface, index needs to be properly translated.
         * Index of 0 needs to map to "signal'left" and Index of "length-1" mapping to "signal'right"
         */
        if (!isTypeValue(type)) {
            /* This case would be for indexing into a generate loop.  The way that is currently
             * handled, this code should never be executed.
             */
            snprintf(buff, 15, "(%u)", index);
        } else {
            FliValueObjHdl *fli_obj = static_cast<FliValueObjHdl *>(parent);
            mtiTypeIdT typeId = fli_obj->get_fli_typeid();

            if (mti_TickDir(typeId) < 0) {
                snprintf(buff, 15, "(%u)", mti_TickLeft(typeId) - index);
            } else {
                snprintf(buff, 15, "(%u)", mti_TickLeft(typeId) + index);
            }
        }

        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        std::vector<char> writable(fq_name.begin(), fq_name.end());
        writable.push_back('\0');

        HANDLE hdl;
        PLI_INT32 accType;
        PLI_INT32 accFullType;

        if ((hdl = mti_FindRegion(&writable[0])) != NULL) {
            accType     = acc_fetch_type(hdl);
            accFullType = acc_fetch_fulltype(hdl);
            LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        } else if ((hdl = mti_FindSignal(&writable[0])) != NULL) {
            accType     = acc_fetch_type(hdl);
            accFullType = acc_fetch_fulltype(hdl);
            LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        } else if ((hdl = mti_FindVar(&writable[0])) != NULL) {
            accFullType = accType = mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));
            LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        } else {
            LOG_DEBUG("Didn't find anything named %s", &writable[0]);
            return NULL;
        }

        return create_gpi_obj_from_handle(hdl, name, fq_name, accType, accFullType);
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
    PLI_INT32 accType;
    PLI_INT32 accFullType;

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

    accType     = acc_fetch_type(root);
    accFullType = acc_fetch_fulltype(root);

    return create_gpi_obj_from_handle(root, root_name, root_fullname, accType, accFullType);

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
    int type;

    if (m_parent->get_type() == GPI_MODULE or m_parent->get_type() == GPI_STRUCTURE) {
        FliObjHdl *fli_obj = static_cast<FliObjHdl *>(m_parent);
        type = fli_obj->get_acc_full_type();
    } else {
        FliSignalObjHdl *fli_obj = static_cast<FliSignalObjHdl *>(m_parent);
        type = fli_obj->get_acc_full_type();
    }

    LOG_DEBUG("fli_iterator::Create iterator for %s of type %d:%s", m_parent->get_fullname().c_str(), type, acc_fetch_type_str(type));

    if (NULL == (selected = iterate_over.get_options(type))) {
        LOG_WARN("FLI: Implementation does not know how to iterate over %s(%d)",
                 acc_fetch_type_str(type), type);
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin(); one2many != selected->end(); one2many++) {
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

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try next one until a new object is found
     */
    do {
        obj = NULL;

        if (m_iterator != m_currentHandles->end()) {
            obj = *m_iterator++;
            break;
        } else {
            LOG_DEBUG("No more valid handles in the current OneToMany=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
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
    PLI_INT32 accType;
    PLI_INT32 accFullType;
    switch (*one2many) {
        case FliIterator::OTM_CONSTANTS:
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            c_name = mti_GetVarName(static_cast<mtiVariableIdT>(obj));
            accFullType = accType = mti_GetVarKind(static_cast<mtiVariableIdT>(obj));
            break;
        case FliIterator::OTM_SIGNALS:
            c_name = mti_GetSignalName(static_cast<mtiSignalIdT>(obj));
            accType     = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            c_name = mti_GetSignalNameIndirect(static_cast<mtiSignalIdT>(obj), NULL, 0);
            accType     = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        case FliIterator::OTM_REGIONS:
            c_name = mti_GetRegionName(static_cast<mtiRegionIdT>(obj));
            accType     = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        default:
            LOG_WARN("Unhandled OneToMany Type (%d)", *one2many);
    }

    if (!c_name) {
        int accFullType = acc_fetch_fulltype(obj);

        if (!VS_TYPE_IS_VHDL(accFullType)) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        return GpiIterator::NATIVE_NO_NAME;
    }

    name = c_name;

    if (*one2many == FliIterator::OTM_SIGNAL_SUB_ELEMENTS) {
        mti_VsimFree(c_name);
    }

    std::string fq_name = m_parent->get_fullname();
    if (fq_name == "/") {
        fq_name += name;
    } else if (*one2many == FliIterator::OTM_SIGNAL_SUB_ELEMENTS ||
               *one2many == FliIterator::OTM_VARIABLE_SUB_ELEMENTS) {
        std::size_t found;

        if (m_parent->get_type() == GPI_STRUCTURE) {
            found = name.find_last_of(".");
        } else {
            found = name.find_last_of("(");
        }

        if (found != std::string::npos) {
            fq_name += name.substr(found);
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "/" + name;
        }
    } else {
        fq_name += "/" + name;
    }

    FliImpl *fli_impl = static_cast<FliImpl *>(m_impl);
    new_obj = fli_impl->create_gpi_obj_from_handle(obj, name, fq_name, accType, accFullType);
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
            if (m_parent->get_type() == GPI_MODULE || m_parent->get_type() == GPI_STRUCTURE) {
                mtiSignalIdT parent = m_parent->get_handle<mtiSignalIdT>();

                mtiTypeIdT type = mti_GetSignalType(parent);
                mtiSignalIdT *ids = mti_GetSignalSubelements(parent,0);

                for (int i = 0; i < mti_TickLength(type); i++) {
                    m_sigs.push_back(ids[i]);
                }

                mti_VsimFree(ids);
            }
            break;
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            if (m_parent->get_type() == GPI_MODULE || m_parent->get_type() == GPI_STRUCTURE) {
                mtiVariableIdT parent = m_parent->get_handle<mtiVariableIdT>();

                mtiTypeIdT type = mti_GetVarType(parent);
                mtiVariableIdT *ids = mti_GetVarSubelements(parent,0);

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

