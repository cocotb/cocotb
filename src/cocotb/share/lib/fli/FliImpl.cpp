// Copyright cocotb contributors
// Copyright (c) 2014, 2018 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "FliImpl.h"

#include <cstddef>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include "_vendor/fli/acc_user.h"
#include "_vendor/fli/acc_vhdl.h"
#include "_vendor/fli/mti.h"
#include "_vendor/tcl/tcl.h"

void FliImpl::sim_end() {
    m_sim_finish_cb->remove();
    if (mti_NowUpper() == 0 && mti_Now() == 0 && mti_Delta() == 0) {
        mti_Quit();
    } else {
        mti_Break();
    }
}

bool FliImpl::isValueConst(int kind) {
    return (kind == accGeneric || kind == accVHDLConstant);
}

bool FliImpl::isValueLogic(mtiTypeIdT type) {
    mtiInt32T numEnums = mti_TickLength(type);
    if (numEnums == 2) {
        char **enum_values = mti_GetEnumValues(type);
        std::string str0 = enum_values[0];
        std::string str1 = enum_values[1];

        if (str0.compare("'0'") == 0 && str1.compare("'1'") == 0) {
            return true;
        }
    } else if (numEnums == 9) {
        const char enums[9][4] = {"'U'", "'X'", "'0'", "'1'", "'Z'",
                                  "'W'", "'L'", "'H'", "'-'"};
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

bool FliImpl::isValueChar(mtiTypeIdT type) {
    const int NUM_ENUMS_IN_CHAR_TYPE = 256;
    return (mti_TickLength(type) == NUM_ENUMS_IN_CHAR_TYPE);
}

bool FliImpl::isValueBoolean(mtiTypeIdT type) {
    if (mti_TickLength(type) == 2) {
        char **enum_values = mti_GetEnumValues(type);
        std::string strFalse = enum_values[0];
        std::string strTrue = enum_values[1];

        if (strFalse.compare("FALSE") == 0 && strTrue.compare("TRUE") == 0) {
            return true;
        }
    }

    return false;
}

bool FliImpl::isTypeValue(int type) {
    return (type == accAlias || type == accVHDLConstant || type == accGeneric ||
            type == accVariable || type == accSignal);
}

bool FliImpl::isTypeSignal(int type, int full_type) {
    return (type == accSignal || full_type == accAliasSignal);
}

GpiObjHdl *FliImpl::create_gpi_obj_from_handle(void *hdl,
                                               const std::string &name,
                                               const std::string &fq_name,
                                               int accType, int accFullType) {
    GpiObjHdl *new_obj = NULL;

    LOG_DEBUG(
        "Attempting to create GPI object from handle (Type=%d, FullType=%d).",
        accType, accFullType);
    if (!VS_TYPE_IS_VHDL(accFullType)) {
        LOG_DEBUG("Handle is not a VHDL type.");
        return NULL;
    }

    if (!isTypeValue(accType)) {
        /* Need a Pseudo-region to handle generate loops in a consistent manner
         * across interfaces and across the different methods of accessing data.
         */
        std::string rgn_name =
            mti_GetRegionName(static_cast<mtiRegionIdT>(hdl));
        if (name != rgn_name) {
            LOG_DEBUG("Found pseudo-region %s -> %p", fq_name.c_str(), hdl);
            new_obj =
                new FliObjHdl(this, hdl, GPI_GENARRAY, accType, accFullType);
        } else {
            LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
            new_obj =
                new FliObjHdl(this, hdl, GPI_MODULE, accType, accFullType);
        }
    } else {
        bool is_var;
        bool is_const;
        mtiTypeIdT valType;
        mtiTypeKindT typeKind;

        if (isTypeSignal(accType, accFullType)) {
            LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
            is_var = false;
            is_const = false;
            valType = mti_GetSignalType(static_cast<mtiSignalIdT>(hdl));
        } else {
            LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
            is_var = true;
            is_const = isValueConst(accFullType);
            valType = mti_GetVarType(static_cast<mtiVariableIdT>(hdl));
        }

        typeKind = mti_GetTypeKind(valType);

        switch (typeKind) {
            case MTI_TYPE_ENUM:
                if (isValueLogic(valType)) {
                    new_obj = new FliLogicObjHdl(this, hdl, GPI_LOGIC, is_const,
                                                 accType, accFullType, is_var,
                                                 valType, typeKind);
                } else if (isValueBoolean(valType) || isValueChar(valType)) {
                    new_obj = new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const,
                                               accType, accFullType, is_var,
                                               valType, typeKind);
                } else {
                    new_obj = new FliEnumObjHdl(this, hdl, GPI_ENUM, is_const,
                                                accType, accFullType, is_var,
                                                valType, typeKind);
                }
                break;
            case MTI_TYPE_SCALAR:
            case MTI_TYPE_PHYSICAL:
                new_obj =
                    new FliIntObjHdl(this, hdl, GPI_INTEGER, is_const, accType,
                                     accFullType, is_var, valType, typeKind);
                break;
            case MTI_TYPE_REAL:
                new_obj =
                    new FliRealObjHdl(this, hdl, GPI_REAL, is_const, accType,
                                      accFullType, is_var, valType, typeKind);
                break;
            case MTI_TYPE_ARRAY: {
                mtiTypeIdT elemType = mti_GetArrayElementType(valType);
                mtiTypeKindT elemTypeKind = mti_GetTypeKind(elemType);

                switch (elemTypeKind) {
                    case MTI_TYPE_ENUM:
                        if (isValueLogic(elemType)) {
                            new_obj = new FliLogicObjHdl(
                                this, hdl, GPI_LOGIC_ARRAY, is_const, accType,
                                accFullType, is_var, valType,
                                typeKind);  // std_logic_vector
                        } else if (isValueChar(elemType)) {
                            new_obj = new FliStringObjHdl(
                                this, hdl, GPI_STRING, is_const, accType,
                                accFullType, is_var, valType, typeKind);
                        } else {
                            new_obj = new FliValueObjHdl(
                                this, hdl, GPI_ARRAY, false, accType,
                                accFullType, is_var, valType,
                                typeKind);  // array of enums
                        }
                        break;
                    default:
                        new_obj = new FliValueObjHdl(
                            this, hdl, GPI_ARRAY, false, accType, accFullType,
                            is_var, valType,
                            typeKind);  // array of (array, Integer, Real,
                                        // Record, etc.)
                }
            } break;
            case MTI_TYPE_RECORD:
                new_obj =
                    new FliValueObjHdl(this, hdl, GPI_STRUCTURE, false, accType,
                                       accFullType, is_var, valType, typeKind);
                break;
            default:
                LOG_ERROR("Unable to handle object type for %s (%d)",
                          name.c_str(), typeKind);
                return NULL;
        }
    }

    if (NULL == new_obj) {
        LOG_DEBUG("Didn't find anything named %s", fq_name.c_str());
        return NULL;
    }

    if (new_obj->initialise(name, fq_name) < 0) {
        LOG_ERROR("Failed to initialize the handle %s", name.c_str());
        delete new_obj;
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *FliImpl::native_check_create(void *raw_hdl, GpiObjHdl *) {
    LOG_DEBUG("Trying to convert a raw handle to an FLI Handle.");

    const char *c_name = acc_fetch_name(raw_hdl);
    const char *c_fullname = acc_fetch_fullname(raw_hdl);

    if (!c_name) {
        LOG_DEBUG("Unable to query the name of the raw handle.");
        return NULL;
    }

    std::string name = c_name;
    std::string fq_name = c_fullname;

    PLI_INT32 accType = acc_fetch_type(raw_hdl);
    PLI_INT32 accFullType = acc_fetch_fulltype(raw_hdl);

    return create_gpi_obj_from_handle(raw_hdl, name, fq_name, accType,
                                      accFullType);
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl *FliImpl::native_check_create(const std::string &name,
                                        GpiObjHdl *parent) {
    bool search_rgn = false;
    bool search_sig = false;
    bool search_var = false;

    std::string fq_name = parent->get_fullname();
    gpi_objtype obj_type = parent->get_type();

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
        FliValueObjHdl *fli_obj = reinterpret_cast<FliValueObjHdl *>(parent);

        fq_name += "." + name;
        search_rgn = false;
        search_var = fli_obj->is_variable();
        search_sig = !search_var;
    } else {
        LOG_ERROR(
            "FLI: Parent of type %d must be of type GPI_MODULE or "
            "GPI_STRUCTURE to have a child.",
            obj_type);
        return NULL;
    }

    LOG_DEBUG("Looking for child %s from %s", name.c_str(),
              parent->get_name_str());

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    HANDLE hdl = NULL;
    PLI_INT32 accType;
    PLI_INT32 accFullType;

    if (search_rgn && (hdl = mti_FindRegion(&writable[0])) != NULL) {
        accType = acc_fetch_type(hdl);
        accFullType = acc_fetch_fulltype(hdl);
        LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else if (search_sig && (hdl = mti_FindSignal(&writable[0])) != NULL) {
        accType = acc_fetch_type(hdl);
        accFullType = acc_fetch_fulltype(hdl);
        LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else if (search_var && (hdl = mti_FindVar(&writable[0])) != NULL) {
        accFullType = accType =
            mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));
        LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
        LOG_DEBUG("        Type: %d", accType);
        LOG_DEBUG("   Full Type: %d", accFullType);
    } else if (search_rgn) {
        mtiRegionIdT rgn;

        // Looking for generates should only occur if the parent is from this
        // implementation
        if (!parent->is_this_impl(this)) {
            return NULL;
        }

        /* If not found, check to see if the name of a generate loop and create
         * a pseudo-region */
        for (rgn = mti_FirstLowerRegion(parent->get_handle<mtiRegionIdT>());
             rgn != NULL; rgn = mti_NextRegion(rgn)) {
            if (acc_fetch_fulltype(rgn) == accForGenerate) {
                std::string rgn_name =
                    mti_GetRegionName(static_cast<mtiRegionIdT>(rgn));
                if (compare_generate_labels(rgn_name, name)) {
                    FliObj *fli_obj = dynamic_cast<FliObj *>(parent);
                    return create_gpi_obj_from_handle(
                        parent->get_handle<HANDLE>(), name, fq_name,
                        fli_obj->get_acc_type(), fli_obj->get_acc_full_type());
                }
            }
        }
    }

    if (NULL == hdl) {
        LOG_DEBUG("Didn't find anything named %s", &writable[0]);
        return NULL;
    }

    /* Generate Loops have inconsistent behavior across fli.  A "name"
     * without an index, i.e. dut.loop vs dut.loop(0), will attempt to map
     * to index 0, if index 0 exists.  If it doesn't then it won't find
     * anything.
     *
     * If this unique case is hit, we need to create the Pseudo-region, with the
     * handle being equivalent to the parent handle.
     */
    if (accFullType == accForGenerate) {
        FliObj *fli_obj = dynamic_cast<FliObj *>(parent);
        return create_gpi_obj_from_handle(parent->get_handle<HANDLE>(), name,
                                          fq_name, fli_obj->get_acc_type(),
                                          fli_obj->get_acc_full_type());
    }

    return create_gpi_obj_from_handle(hdl, name, fq_name, accType, accFullType);
}

/**
 * @name    Native Check Create
 * @brief   Determine whether a simulation object is native to FLI and create
 *          a handle if it is
 */
GpiObjHdl *FliImpl::native_check_create(int32_t index, GpiObjHdl *parent) {
    gpi_objtype obj_type = parent->get_type();

    HANDLE hdl;
    PLI_INT32 accType;
    PLI_INT32 accFullType;
    char buff[14];

    if (obj_type == GPI_GENARRAY) {
        LOG_DEBUG("Looking for index %d from %s", index,
                  parent->get_name_str());

        snprintf(buff, 14, "(%d)", index);

        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        std::vector<char> writable(fq_name.begin(), fq_name.end());
        writable.push_back('\0');

        if ((hdl = mti_FindRegion(&writable[0])) != NULL) {
            accType = acc_fetch_type(hdl);
            accFullType = acc_fetch_fulltype(hdl);
            LOG_DEBUG("Found region %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        } else {
            LOG_DEBUG("Didn't find anything named %s", &writable[0]);
            return NULL;
        }

        return create_gpi_obj_from_handle(hdl, name, fq_name, accType,
                                          accFullType);
    } else if (obj_type == GPI_LOGIC || obj_type == GPI_LOGIC_ARRAY ||
               obj_type == GPI_ARRAY || obj_type == GPI_STRING) {
        FliValueObjHdl *fli_obj = reinterpret_cast<FliValueObjHdl *>(parent);

        LOG_DEBUG("Looking for index %u from %s", index,
                  parent->get_name_str());

        if ((hdl = fli_obj->get_sub_hdl(index)) == NULL) {
            LOG_DEBUG("Didn't find the index %d", index);
            return NULL;
        }

        snprintf(buff, 14, "(%d)", index);

        std::string idx = buff;
        std::string name = parent->get_name() + idx;
        std::string fq_name = parent->get_fullname() + idx;

        if (!(fli_obj->is_variable())) {
            accType = acc_fetch_type(hdl);
            accFullType = acc_fetch_fulltype(hdl);
            LOG_DEBUG("Found a signal %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        } else {
            accFullType = accType =
                mti_GetVarKind(static_cast<mtiVariableIdT>(hdl));
            LOG_DEBUG("Found a variable %s -> %p", fq_name.c_str(), hdl);
            LOG_DEBUG("        Type: %d", accType);
            LOG_DEBUG("   Full Type: %d", accFullType);
        }
        return create_gpi_obj_from_handle(hdl, name, fq_name, accType,
                                          accFullType);
    } else {
        LOG_ERROR(
            "FLI: Parent of type %d must be of type GPI_GENARRAY, "
            "GPI_LOGIC, GPI_ARRAY, or GPI_STRING to have an index.",
            obj_type);
        return NULL;
    }
}

const char *FliImpl::reason_to_string(int) {
    return "Who can explain it, who can tell you why?";
}

/**
 * @name    Get current simulation time
 * @brief   Get current simulation time
 *
 * NB units depend on the simulation configuration
 */
void FliImpl::get_sim_time(uint32_t *high, uint32_t *low) {
    *high = static_cast<uint32_t>(
        mti_NowUpper());  // these functions return a int32_t for some reason
    *low = static_cast<uint32_t>(mti_Now());
}

void FliImpl::get_sim_precision(int32_t *precision) {
    *precision = mti_GetResolutionLimit();
}

const char *FliImpl::get_simulator_product() {
    if (m_product.empty() && m_version.empty()) {
        const std::string info =
            mti_GetProductVersion();  // Returned pointer must not be freed,
                                      // does not fail
        const std::string search = " Version ";
        const std::size_t found = info.find(search);

        if (found != std::string::npos) {
            m_product = info.substr(0, found);
            m_version = info.substr(found + search.length());
        } else {
            m_product = info;
            m_version = "UNKNOWN";
        }
    }
    return m_product.c_str();
}

const char *FliImpl::get_simulator_version() {
    get_simulator_product();
    return m_version.c_str();
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
GpiObjHdl *FliImpl::get_root_handle(const char *name) {
    mtiRegionIdT root;
    char *rgn_name;
    char *rgn_fullname;
    std::string root_name;
    std::string root_fullname;
    PLI_INT32 accType;
    PLI_INT32 accFullType;

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        LOG_DEBUG("Iterating over: %s", mti_GetRegionName(root));
        if (name == NULL || !strcmp(name, mti_GetRegionName(root))) break;
    }

    if (!root) {
        goto error;
    }

    rgn_name = mti_GetRegionName(root);
    rgn_fullname = mti_GetRegionFullName(root);

    root_name = rgn_name;
    root_fullname = rgn_fullname;
    mti_VsimFree(rgn_fullname);

    LOG_DEBUG("Found toplevel: %s, creating handle....", root_name.c_str());

    accType = acc_fetch_type(root);
    accFullType = acc_fetch_fulltype(root);

    return create_gpi_obj_from_handle(root, root_name, root_fullname, accType,
                                      accFullType);

error:

    LOG_ERROR("FLI: Couldn't find root handle %s", name);

    for (root = mti_GetTopRegion(); root != NULL; root = mti_NextRegion(root)) {
        if (name == NULL) break;

        LOG_ERROR("FLI: Toplevel instances: %s != %s...", name,
                  mti_GetRegionName(root));
    }
    return NULL;
}

GpiCbHdl *FliImpl::register_timed_callback(uint64_t time,
                                           int (*cb_func)(void *),
                                           void *cb_data) {
    // get timer from cache
    auto cb_hdl = m_timer_cache.acquire();
    cb_hdl->set_time(time);
    int err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        m_timer_cache.release(cb_hdl);
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *FliImpl::register_readonly_callback(int (*cb_func)(void *),
                                              void *cb_data) {
    auto cb_hdl = m_read_only_cache.acquire();
    int err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        m_read_only_cache.release(cb_hdl);
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *FliImpl::register_readwrite_callback(int (*cb_func)(void *),
                                               void *cb_data) {
    auto cb_hdl = m_read_write_cache.acquire();
    int err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        m_read_write_cache.release(cb_hdl);
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *FliImpl::register_nexttime_callback(int (*cb_func)(void *),
                                              void *cb_data) {
    auto cb_hdl = m_next_phase_cache.acquire();
    int err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        m_next_phase_cache.release(cb_hdl);
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiIterator *FliImpl::iterate_handle(GpiObjHdl *obj_hdl,
                                     gpi_iterator_sel type) {
    GpiIterator *new_iter = NULL;

    switch (type) {
        case GPI_OBJECTS:
            new_iter = new FliIterator(this, obj_hdl);
            break;
        case GPI_DRIVERS:
            LOG_WARN("FLI: Drivers iterator not implemented yet");
            break;
        case GPI_LOADS:
            LOG_WARN("FLI: Loads iterator not implemented yet");
            break;
        default:
            LOG_WARN("FLI: Other iterator types not implemented yet");
            break;
    }

    return new_iter;
}

bool FliImpl::compare_generate_labels(const std::string &a,
                                      const std::string &b) {
    /* Compare two generate labels for equality ignoring any suffixed index. */
    std::size_t a_idx = a.rfind("(");
    std::size_t b_idx = b.rfind("(");
    return a.substr(0, a_idx) == b.substr(0, b_idx);
}

decltype(FliIterator::iterate_over) FliIterator::iterate_over = [] {
    std::initializer_list<FliIterator::OneToMany> region_options = {
        FliIterator::OTM_CONSTANTS,
        FliIterator::OTM_SIGNALS,
        FliIterator::OTM_REGIONS,
    };
    std::initializer_list<FliIterator::OneToMany> signal_options = {
        FliIterator::OTM_SIGNAL_SUB_ELEMENTS,
    };
    std::initializer_list<FliIterator::OneToMany> variable_options = {
        FliIterator::OTM_VARIABLE_SUB_ELEMENTS,
    };

    return decltype(FliIterator::iterate_over){
        {accArchitecture, region_options},
        {accEntityVitalLevel0, region_options},
        {accArchVitalLevel0, region_options},
        {accArchVitalLevel1, region_options},
        {accBlock, region_options},
        {accCompInst, region_options},
        {accDirectInst, region_options},
        {accinlinedBlock, region_options},
        {accinlinedinnerBlock, region_options},
        {accGenerate, region_options},
        {accIfGenerate, region_options},
#ifdef accElsifGenerate
        {accElsifGenerate, region_options},
#endif
#ifdef accElseGenerate
        {accElseGenerate, region_options},
#endif
#ifdef accCaseGenerate
        {accCaseGenerate, region_options},
#endif
#ifdef accCaseOTHERSGenerate
        {accCaseOTHERSGenerate, region_options},
#endif
        {accForGenerate, region_options},
        {accConfiguration, region_options},

        {accSignal, signal_options},
        {accSignalBit, signal_options},
        {accSignalSubComposite, signal_options},
        {accAliasSignal, signal_options},

        {accVariable, variable_options},
        {accGeneric, variable_options},
        {accGenericConstant, variable_options},
        {accAliasConstant, variable_options},
        {accAliasGeneric, variable_options},
        {accAliasVariable, variable_options},
        {accVHDLConstant, variable_options},
    };
}();

FliIterator::FliIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
    : GpiIterator(impl, hdl),
      m_vars(),
      m_sigs(),
      m_regs(),
      m_currentHandles(NULL) {
    FliObj *fli_obj = dynamic_cast<FliObj *>(m_parent);
    int type = fli_obj->get_acc_full_type();

    LOG_DEBUG("fli_iterator::Create iterator for %s of type %d:%s",
              m_parent->get_fullname().c_str(), type, acc_fetch_type_str(type));

    try {
        selected = &iterate_over.at(type);
    } catch (std::out_of_range const &) {
        LOG_WARN("FLI: Implementation does not know how to iterate over %s(%d)",
                 acc_fetch_type_str(type), type);
        selected = nullptr;
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin(); one2many != selected->end();
         one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY &&
            *one2many != FliIterator::OTM_REGIONS) {
            LOG_DEBUG("fli_iterator OneToMany=%d skipped for GPI_GENARRAY type",
                      *one2many);
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

        if (m_iterator != m_currentHandles->end()) break;

        LOG_DEBUG("fli_iterator OneToMany=%d returned NULL", *one2many);
    }

    if (m_iterator == m_currentHandles->end()) {
        LOG_DEBUG(
            "fli_iterator return NULL for all relationships on %s (%d) kind:%s",
            m_parent->get_name_str(), type, acc_fetch_type_str(type));
        selected = NULL;
        return;
    }

    LOG_DEBUG("Created iterator working from scope %d", *one2many);
}

GpiIterator::Status FliIterator::next_handle(std::string &name, GpiObjHdl **hdl,
                                             void **raw_hdl) {
    HANDLE obj;
    GpiObjHdl *new_obj;

    if (!selected) return GpiIterator::END;

    gpi_objtype obj_type = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try next one until a new object is found
     */
    do {
        obj = NULL;

        if (m_iterator != m_currentHandles->end()) {
            obj = *m_iterator++;

            /* For GPI_GENARRAY, only allow the generate statements through that
             * match the name of the generate block.
             */
            if (obj_type == GPI_GENARRAY) {
                if (acc_fetch_fulltype(obj) == accForGenerate) {
                    std::string rgn_name =
                        mti_GetRegionName(static_cast<mtiRegionIdT>(obj));
                    if (!FliImpl::compare_generate_labels(rgn_name,
                                                          parent_name)) {
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
            LOG_DEBUG(
                "No more valid handles in the current OneToMany=%d iterator",
                *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != FliIterator::OTM_REGIONS) {
            LOG_DEBUG("fli_iterator OneToMany=%d skipped for GPI_GENARRAY type",
                      *one2many);
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
    PLI_INT32 accType;
    PLI_INT32 accFullType;
    switch (*one2many) {
        case FliIterator::OTM_CONSTANTS:
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            c_name = mti_GetVarName(static_cast<mtiVariableIdT>(obj));
            accFullType = accType =
                mti_GetVarKind(static_cast<mtiVariableIdT>(obj));
            break;
        case FliIterator::OTM_SIGNALS:
            c_name = mti_GetSignalName(static_cast<mtiSignalIdT>(obj));
            accType = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            c_name = mti_GetSignalNameIndirect(static_cast<mtiSignalIdT>(obj),
                                               NULL, 0);
            accType = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        case FliIterator::OTM_REGIONS:
            c_name = mti_GetRegionName(static_cast<mtiRegionIdT>(obj));
            accType = acc_fetch_type(obj);
            accFullType = acc_fetch_fulltype(obj);
            break;
        default:
            c_name = NULL;
            accType = 0;
            accFullType = 0;
            LOG_WARN("Unhandled OneToMany Type (%d)", *one2many);
    }

    if (!c_name) {
        if (!VS_TYPE_IS_VHDL(accFullType)) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and
     * create the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region
     * object. Otherwise a list would be required and checked while iterating
     */
    if (*one2many == FliIterator::OTM_REGIONS && obj_type != GPI_GENARRAY &&
        accFullType == accForGenerate) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.find_last_of("(");

        if (found != std::string::npos && found != 0) {
            FliObj *fli_obj = dynamic_cast<FliObj *>(m_parent);

            name = idx_str.substr(0, found);
            obj = m_parent->get_handle<HANDLE>();
            accType = fli_obj->get_acc_type();
            accFullType = fli_obj->get_acc_full_type();
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
                name = name.substr(found + 1);
            }
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "/" + name;
        }
    } else {
        fq_name += "/" + name;
    }

    FliImpl *fli_impl = reinterpret_cast<FliImpl *>(m_impl);
    new_obj = fli_impl->create_gpi_obj_from_handle(obj, name, fq_name, accType,
                                                   accFullType);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else {
        return GpiIterator::NOT_NATIVE;
    }
}

void FliIterator::populate_handle_list(FliIterator::OneToMany childType) {
    switch (childType) {
        case FliIterator::OTM_CONSTANTS: {
            mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
            mtiVariableIdT id;

            for (id = mti_FirstVarByRegion(parent); id; id = mti_NextVar()) {
                if (id) {
                    m_vars.push_back(id);
                }
            }
        } break;
        case FliIterator::OTM_SIGNALS: {
            mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
            mtiSignalIdT id;

            for (id = mti_FirstSignal(parent); id; id = mti_NextSignal()) {
                if (id) {
                    m_sigs.push_back(id);
                }
            }
        } break;
        case FliIterator::OTM_REGIONS: {
            mtiRegionIdT parent = m_parent->get_handle<mtiRegionIdT>();
            mtiRegionIdT id;

            for (id = mti_FirstLowerRegion(parent); id;
                 id = mti_NextRegion(id)) {
                if (id) {
                    m_regs.push_back(id);
                }
            }
        } break;
        case FliIterator::OTM_SIGNAL_SUB_ELEMENTS:
            if (m_parent->get_type() == GPI_STRUCTURE) {
                mtiSignalIdT parent = m_parent->get_handle<mtiSignalIdT>();

                mtiTypeIdT type = mti_GetSignalType(parent);
                mtiSignalIdT *ids = mti_GetSignalSubelements(parent, NULL);

                LOG_DEBUG("GPI_STRUCTURE: %d fields", mti_TickLength(type));
                for (int i = 0; i < mti_TickLength(type); i++) {
                    m_sigs.push_back(ids[i]);
                }
                mti_VsimFree(ids);
            } else if (m_parent->get_indexable()) {
                FliValueObjHdl *fli_obj =
                    reinterpret_cast<FliValueObjHdl *>(m_parent);

                int left = m_parent->get_range_left();
                int right = m_parent->get_range_right();

                if (left > right) {
                    for (int i = left; i >= right; i--) {
                        m_sigs.push_back(
                            static_cast<mtiSignalIdT>(fli_obj->get_sub_hdl(i)));
                    }
                } else {
                    for (int i = left; i <= right; i++) {
                        m_sigs.push_back(
                            static_cast<mtiSignalIdT>(fli_obj->get_sub_hdl(i)));
                    }
                }
            }
            break;
        case FliIterator::OTM_VARIABLE_SUB_ELEMENTS:
            if (m_parent->get_type() == GPI_STRUCTURE) {
                mtiVariableIdT parent = m_parent->get_handle<mtiVariableIdT>();

                mtiTypeIdT type = mti_GetVarType(parent);
                mtiVariableIdT *ids = mti_GetVarSubelements(parent, NULL);

                LOG_DEBUG("GPI_STRUCTURE: %d fields", mti_TickLength(type));
                for (int i = 0; i < mti_TickLength(type); i++) {
                    m_vars.push_back(ids[i]);
                }

                mti_VsimFree(ids);
            } else if (m_parent->get_indexable()) {
                FliValueObjHdl *fli_obj =
                    reinterpret_cast<FliValueObjHdl *>(m_parent);

                int left = m_parent->get_range_left();
                int right = m_parent->get_range_right();

                if (left > right) {
                    for (int i = left; i >= right; i--) {
                        m_vars.push_back(static_cast<mtiVariableIdT>(
                            fli_obj->get_sub_hdl(i)));
                    }
                } else {
                    for (int i = left; i <= right; i++) {
                        m_vars.push_back(static_cast<mtiVariableIdT>(
                            fli_obj->get_sub_hdl(i)));
                    }
                }
            }
            break;
        default:
            LOG_WARN("Unhandled OneToMany Type (%d)", childType);
    }
}

static std::vector<std::string> get_argv() {
    /* Necessary to implement PLUSARGS
       There is no function available on the FLI to obtain argc+argv directly
       from the simulator. To work around this we use the TCL interpreter that
       ships with Questa, some TCL commands, and the TCL variable `argv` to
       obtain the simulator argc+argv.
    */
    std::vector<std::string> argv;

    // obtain a reference to TCL interpreter
    Tcl_Interp *interp = reinterpret_cast<Tcl_Interp *>(mti_Interp());

    // get argv TCL variable
    auto err = mti_Cmd("return -level 0 $argv") != TCL_OK;
    // LCOV_EXCL_START
    if (err) {
        const char *errmsg = Tcl_GetStringResult(interp);
        LOG_WARN("Failed to get reference to argv: %s", errmsg);
        Tcl_ResetResult(interp);
        return argv;
    }
    // LCOV_EXCL_STOP
    Tcl_Obj *result = Tcl_GetObjResult(interp);
    Tcl_IncrRefCount(result);
    Tcl_ResetResult(interp);

    // split TCL list into length and element array
    int argc;
    Tcl_Obj **tcl_argv;
    err = Tcl_ListObjGetElements(interp, result, &argc, &tcl_argv) != TCL_OK;
    // LCOV_EXCL_START
    if (err) {
        const char *errmsg = Tcl_GetStringResult(interp);
        LOG_WARN("Failed to get argv elements: %s", errmsg);
        Tcl_DecrRefCount(result);
        Tcl_ResetResult(interp);
        return argv;
    }
    // LCOV_EXCL_STOP
    Tcl_ResetResult(interp);

    // get each argv arg and copy into internal storage
    for (int i = 0; i < argc; i++) {
        const char *arg = Tcl_GetString(tcl_argv[i]);
        argv.push_back(arg);
    }
    Tcl_DecrRefCount(result);

    return argv;
}

static int startup_callback(void *) {
    std::vector<std::string> const argv_storage = get_argv();
    std::vector<const char *> argv_cstr;
    for (const auto &arg : argv_storage) {
        argv_cstr.push_back(arg.c_str());
    }
    int argc = static_cast<int>(argv_storage.size());
    const char **argv = argv_cstr.data();

    gpi_embed_init(argc, argv);

    return 0;
}

static int shutdown_callback(void *) {
    gpi_embed_end();
    return 0;
}

void FliImpl::main() noexcept {
    auto startup_cb = new FliStartupCbHdl(this);
    auto err = startup_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VHPI: Unable to register startup callback! Simulation will end.");
        delete startup_cb;
        exit(1);
    }
    // LCOV_EXCL_STOP
    startup_cb->set_cb_info(startup_callback, nullptr);

    auto shutdown_cb = new FliShutdownCbHdl(this);
    err = shutdown_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VHPI: Unable to register shutdown callback! Simulation will end.");
        startup_cb->remove();
        delete shutdown_cb;
        exit(1);
    }
    // LCOV_EXCL_STOP
    shutdown_cb->set_cb_info(shutdown_callback, nullptr);
    m_sim_finish_cb = shutdown_cb;

    gpi_register_impl(this);
    gpi_entry_point();
}

static void register_impl() {
    auto fli_table = new FliImpl("FLI");
    gpi_register_impl(fli_table);
}

extern "C" {
COCOTBFLI_EXPORT void cocotb_init() {
    auto fli_table = new FliImpl("FLI");
    fli_table->main();
}
}

GPI_ENTRY_POINT(cocotbfli, register_impl);
