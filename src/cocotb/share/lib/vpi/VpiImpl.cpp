// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "VpiImpl.h"

#include "_vendor/vpi/vpi_user.h"
#include "gpi.h"
#include "gpi_logging.h"
#include "vpi_user_ext.h"

#define CASE_STR(_X) \
    case _X:         \
        return #_X

const char *VpiImpl::reason_to_string(int reason) {
    switch (reason) {
        CASE_STR(cbValueChange);
        CASE_STR(cbAtStartOfSimTime);
        CASE_STR(cbReadWriteSynch);
        CASE_STR(cbReadOnlySynch);
        CASE_STR(cbNextSimTime);
        CASE_STR(cbAfterDelay);
        CASE_STR(cbStartOfSimulation);
        CASE_STR(cbEndOfSimulation);

        default:
            return "unknown";
    }
}

#undef CASE_STR

void VpiImpl::get_sim_time(uint32_t *high, uint32_t *low) {
    s_vpi_time vpi_time_s;
    vpi_time_s.type = vpiSimTime;  // vpiSimTime;
    vpi_get_time(NULL, &vpi_time_s);
    check_vpi_error();
    *high = vpi_time_s.high;
    *low = vpi_time_s.low;
}

void VpiImpl::get_sim_precision(int32_t *precision) {
    *precision = vpi_get(vpiTimePrecision, NULL);
}

const char *VpiImpl::get_simulator_product() {
    if (m_product.empty() && m_version.empty()) {
        s_vpi_vlog_info info;
        if (!vpi_get_vlog_info(&info)) {
            LOG_WARN("Could not obtain info about the simulator");
            m_product = "UNKNOWN";
            m_version = "UNKNOWN";
        } else {
            m_product = info.product;
            m_version = info.version;
        }
    }
    return m_product.c_str();
}

const char *VpiImpl::get_simulator_version() {
    get_simulator_product();
    return m_version.c_str();
}

static gpi_objtype to_gpi_objtype(int32_t vpitype, int num_elements = 0,
                                  bool is_vector = false) {
    switch (vpitype) {
        case vpiNet:
        case vpiNetBit:
        case vpiBitVar:
        case vpiReg:
        case vpiRegBit:
        case vpiMemoryWord:
        case vpiPackedArrayVar:
        case vpiPackedArrayNet:
            if (is_vector || num_elements > 1) {
                return GPI_LOGIC_ARRAY;
            } else {
                return GPI_LOGIC;
            }
            break;

        case vpiRealNet:
        case vpiRealVar:
            return GPI_REAL;

        case vpiInterfaceArray:
        case vpiRegArray:
        case vpiNetArray:
        case vpiGenScopeArray:
        case vpiMemory:
            return GPI_ARRAY;

        case vpiEnumNet:
        case vpiEnumVar:
            return GPI_ENUM;

        case vpiIntVar:
        case vpiIntegerVar:
        case vpiIntegerNet:
            return GPI_INTEGER;

        case vpiStructVar:
        case vpiStructNet:
        case vpiUnionVar:
        case vpiUnionNet:
            return GPI_STRUCTURE;

        case vpiInterface:
        case vpiModule:
        case vpiPort:
        case vpiGate:
        case vpiSwitch:
        case vpiPrimTerm:
        case vpiGenScope:
            return GPI_MODULE;

        case vpiPackage:
            return GPI_PACKAGE;

        case vpiStringVar:
            return GPI_STRING;

        default:
            LOG_DEBUG("Unable to map VPI type %d onto GPI type", vpitype);
            return GPI_UNKNOWN;
    }
}

static gpi_objtype const_type_to_gpi_objtype(int32_t const_type) {
    // Most simulators only return vpiDecConst or vpiBinaryConst
    switch (const_type) {
#ifdef IUS
        case vpiUndefined:
            LOG_WARN(
                "VPI: Xcelium reports undefined parameters as vpiUndefined, "
                "guessing this is a logic vector");
            return GPI_LOGIC_ARRAY;
#endif
        case vpiDecConst:
        case vpiBinaryConst:
        case vpiOctConst:
        case vpiHexConst:
        case vpiIntConst:
            return GPI_LOGIC_ARRAY;
        case vpiRealConst:
            return GPI_REAL;
        case vpiStringConst:
            return GPI_STRING;
        // case vpiTimeConst:  // Not implemented
        default:
            LOG_WARN(
                "Unable to map vpiConst type %d onto GPI type, "
                "guessing this is a logic vector",
                const_type);
            return GPI_LOGIC_ARRAY;
    }
}

GpiObjHdl *VpiImpl::create_gpi_obj_from_handle(vpiHandle new_hdl,
                                               const std::string &name,
                                               const std::string &fq_name) {
    int32_t type;
    GpiObjHdl *new_obj = NULL;
    if (vpiUnknown == (type = vpi_get(vpiType, new_hdl))) {
        LOG_DEBUG("vpiUnknown returned from vpi_get(vpiType, ...)");
        return NULL;
    }

    /* What sort of instance is this ?*/
    switch (type) {
        case vpiNet:
        case vpiNetBit:
        case vpiBitVar:
        case vpiReg:
        case vpiRegBit:
        case vpiEnumNet:
        case vpiEnumVar:
        case vpiIntVar:
        case vpiIntegerVar:
        case vpiIntegerNet:
        case vpiPackedArrayVar:
        case vpiPackedArrayNet:
        case vpiRealVar:
        case vpiRealNet:
        case vpiStringVar:
        case vpiMemoryWord:
        case vpiInterconnectNet: {
            const auto is_vector = vpi_get(vpiVector, new_hdl);
            const auto num_elements = vpi_get(vpiSize, new_hdl);
            new_obj = new VpiSignalObjHdl(
                this, new_hdl, to_gpi_objtype(type, num_elements, is_vector),
                false);
            break;
        }
        case vpiParameter:
        case vpiConstant: {
            auto const_type = vpi_get(vpiConstType, new_hdl);
            new_obj = new VpiSignalObjHdl(
                this, new_hdl, const_type_to_gpi_objtype(const_type), true);
            break;
        }
        case vpiRegArray:
        case vpiNetArray:
        case vpiInterfaceArray:
        case vpiMemory:
        case vpiInterconnectArray: {
            const auto is_vector = vpi_get(vpiVector, new_hdl);
            const auto num_elements = vpi_get(vpiSize, new_hdl);
            new_obj = new VpiArrayObjHdl(
                this, new_hdl, to_gpi_objtype(type, num_elements, is_vector));
            break;
        }
        case vpiStructVar:
        case vpiStructNet:
        case vpiUnionVar:
        case vpiUnionNet: {
            auto is_vector = false;
            if (vpi_get(vpiPacked, new_hdl)) {
                LOG_DEBUG("VPI: Found packed struct/union data type");
                new_obj = new VpiSignalObjHdl(this, new_hdl,
                                              GPI_PACKED_STRUCTURE, false);
                break;
            } else if (vpi_get(vpiVector, new_hdl)) {
                is_vector = true;
            }
            const auto num_elements = vpi_get(vpiSize, new_hdl);
            new_obj = new VpiObjHdl(
                this, new_hdl, to_gpi_objtype(type, num_elements, is_vector));
            break;
        }
        case vpiModule:
        case vpiInterface:
        case vpiPort:
        case vpiGate:
        case vpiSwitch:
        case vpiPrimTerm:
        case vpiGenScope:
        case vpiGenScopeArray: {
            std::string hdl_name = vpi_get_str(vpiName, new_hdl);

            if (hdl_name != name) {
                LOG_DEBUG("Found pseudo-region %s (hdl_name=%s but name=%s)",
                          fq_name.c_str(), hdl_name.c_str(), name.c_str());
                new_obj = new VpiObjHdl(this, new_hdl, GPI_GENARRAY);
            } else {
                new_obj = new VpiObjHdl(this, new_hdl, to_gpi_objtype(type));
            }
            break;
        }
        default:
            /* We should only print a warning here if the type is really
               Verilog, It could be VHDL as some simulators allow querying of
               both languages via the same handle
               */
            const char *type_name = vpi_get_str(vpiType, new_hdl);
            std::string unknown = "vpiUnknown";
            if (type_name && (unknown != type_name)) {
                LOG_WARN("VPI: Not able to map type %s(%d) to object.",
                         type_name, type);
            } else {
                LOG_WARN("VPI: Simulator does not know this type (%d) via VPI",
                         type);
            }
            return NULL;
    }

    new_obj->initialise(name, fq_name);

    LOG_DEBUG("VPI: Created GPI object from type %s(%d)",
              vpi_get_str(vpiType, new_hdl), type);

    return new_obj;
}

GpiObjHdl *VpiImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent) {
    LOG_DEBUG("Trying to convert raw to VPI handle");

    vpiHandle new_hdl = (vpiHandle)raw_hdl;

    const char *c_name = vpi_get_str(vpiName, new_hdl);
    if (!c_name) {
        LOG_DEBUG("Unable to query name of passed in handle");
        return NULL;
    }

    std::string name = c_name;
    std::string fq_name =
        parent->get_fullname() + get_type_delimiter(parent) + name;

    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }
    return new_obj;
}

GpiObjHdl *VpiImpl::native_check_create(const std::string &name,
                                        GpiObjHdl *parent) {
    const vpiHandle parent_hdl = parent->get_handle<vpiHandle>();
    std::string fq_name =
        parent->get_fullname() + get_type_delimiter(parent) + name;

    vpiHandle new_hdl =
        vpi_handle_by_name(const_cast<char *>(fq_name.c_str()), NULL);

#ifdef IUS
    if (new_hdl != NULL && vpi_get(vpiType, new_hdl) == vpiGenScope) {
        // verify that this xcelium scope is valid, or else we segfault on the
        // invalid scope. Xcelium only returns vpiGenScope, no vpiGenScopeArray

        vpiHandle iter = vpi_iterate(vpiInternalScope, parent_hdl);
        bool is_valid = [&]() -> bool {
            for (auto rgn = vpi_scan(iter); rgn != NULL; rgn = vpi_scan(iter)) {
                if (VpiImpl::compare_generate_labels(vpi_get_str(vpiName, rgn),
                                                     name)) {
                    return true;
                }
            }
            return false;
        }();
        vpi_free_object(iter);

        if (!is_valid) {
            vpi_free_object(new_hdl);
            new_hdl = NULL;
        }
    }
#endif

// Xcelium will segfault on a scope that doesn't exist
#ifndef IUS
    /* Some simulators do not support vpiGenScopeArray, only vpiGenScope:
     * - Icarus Verilog
     * - Verilator
     * - Questa/Modelsim
     *
     * If handle is not found by name, look for a generate block with
     * a matching prefix.
     *     For Example:
     *         genvar idx;
     *         generate
     *             for (idx = 0; idx < 5; idx = idx + 1) begin
     *                 ...
     *             end
     *         endgenerate
     *
     *     genblk1      => vpiGenScopeArray (not found)
     *     genblk1[0]   => vpiGenScope
     *     ...
     *     genblk1[4]   => vpiGenScope
     *
     *     genblk1 is not found directly, but if genblk1[n] is found,
     *     genblk1 must exist, so create the pseudo-region object for it.
     */
    if (new_hdl == NULL) {
        LOG_DEBUG(
            "Unable to find '%s' through vpi_handle_by_name, looking for "
            "matching generate scope array using fallback",
            fq_name.c_str());

        vpiHandle iter = vpi_iterate(vpiInternalScope, parent_hdl);
        if (iter != NULL) {
            for (auto rgn = vpi_scan(iter); rgn != NULL; rgn = vpi_scan(iter)) {
                auto rgn_type = vpi_get(vpiType, rgn);
                if (rgn_type == vpiGenScope || rgn_type == vpiModule) {
                    std::string rgn_name = vpi_get_str(vpiName, rgn);
                    if (VpiImpl::compare_generate_labels(rgn_name, name)) {
                        new_hdl = parent_hdl;
                        vpi_free_object(iter);
                        break;
                    }
                }
            }
        }
    }
#endif

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to find '%s'", fq_name.c_str());
        return NULL;
    }

    /* Generate Loops have inconsistent behavior across vpi tools.  A "name"
     * without an index, i.e. dut.loop vs dut.loop[0], will find a handle to
     * vpiGenScopeArray, but not all tools support iterating over the
     * vpiGenScopeArray.  We don't want to create a GpiObjHdl to this type of
     * vpiHandle.
     *
     * If this unique case is hit, we need to create the Pseudo-region, with the
     * handle being equivalent to the parent handle.
     */
    if (vpi_get(vpiType, new_hdl) == vpiGenScopeArray) {
        vpi_free_object(new_hdl);

        new_hdl = parent_hdl;
    }

    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to create object '%s'", fq_name.c_str());
        return NULL;
    }
    return new_obj;
}

GpiObjHdl *VpiImpl::native_check_create(int32_t index, GpiObjHdl *parent) {
    vpiHandle vpi_hdl = parent->get_handle<vpiHandle>();
    vpiHandle new_hdl = NULL;

    char buff[14];  // needs to be large enough to hold -2^31 to 2^31-1 in
                    // string form ('['+'-'10+']'+'\0')

    gpi_objtype obj_type = parent->get_type();

    if (obj_type == GPI_GENARRAY) {
        snprintf(buff, 14, "[%d]", index);

        LOG_DEBUG(
            "Native check create for index %d of parent '%s' (pseudo-region)",
            index, parent->get_name_str());

        std::string idx = buff;
        std::string hdl_name = parent->get_fullname() + idx;
        std::vector<char> writable(hdl_name.begin(), hdl_name.end());
        writable.push_back('\0');

        new_hdl = vpi_handle_by_name(&writable[0], NULL);
    } else if (obj_type == GPI_LOGIC || obj_type == GPI_LOGIC_ARRAY ||
               obj_type == GPI_ARRAY || obj_type == GPI_STRING) {
        new_hdl = vpi_handle_by_index(vpi_hdl, index);

        /* vpi_handle_by_index() doesn't work for all simulators when dealing
         * with a two-dimensional array. For example: wire [7:0] sig_t4
         * [0:1][0:2];
         *
         *    Assume vpi_hdl is for "sig_t4":
         *       vpi_handle_by_index(vpi_hdl, 0);   // Returns a handle to
         * sig_t4[0] for IUS, but NULL on Questa
         *
         *    Questa only works when both indices are provided, i.e. will need a
         * pseudo-handle to behave like the first index.
         */
        if (new_hdl == NULL) {
            int left = parent->get_range_left();
            int right = parent->get_range_right();
            bool ascending = parent->get_range_dir() == GPI_RANGE_UP;

            LOG_DEBUG(
                "Unable to find handle through vpi_handle_by_index(), "
                "attempting second method");

            if ((ascending && (index < left || index > right)) ||
                (!ascending && (index > left || index < right))) {
                LOG_ERROR(
                    "Invalid Index - Index %d is not in the range of [%d:%d]",
                    index, left, right);
                return NULL;
            }

            /* Get the number of constraints to determine if the index will
             * result in a pseudo-handle or should be found */
            vpiHandle p_hdl = parent->get_handle<vpiHandle>();
            vpiHandle it = vpi_iterate(vpiRange, p_hdl);
            int constraint_cnt = 0;
            if (it != NULL) {
                while (vpi_scan(it) != NULL) {
                    ++constraint_cnt;
                }
            } else {
                constraint_cnt = 1;
            }

            std::string act_hdl_name = vpi_get_str(vpiName, p_hdl);

            /* Removing the act_hdl_name from the parent->get_name() will leave
             * the pseudo-indices */
            if (act_hdl_name.length() < parent->get_name().length()) {
                std::string idx_str =
                    parent->get_name().substr(act_hdl_name.length());

                while (idx_str.length() > 0) {
                    std::size_t found = idx_str.find_first_of("]");

                    if (found != std::string::npos) {
                        --constraint_cnt;
                        idx_str = idx_str.substr(found + 1);
                    } else {
                        break;
                    }
                }
            }

            snprintf(buff, 14, "[%d]", index);

            std::string idx = buff;
            std::string hdl_name = parent->get_fullname() + idx;

            std::vector<char> writable(hdl_name.begin(), hdl_name.end());
            writable.push_back('\0');

            new_hdl = vpi_handle_by_name(&writable[0], NULL);

            /* Create a pseudo-handle if not the last index into a
             * multi-dimensional array */
            if (new_hdl == NULL && constraint_cnt > 1) {
                new_hdl = p_hdl;
            }
        }
    } else {
        LOG_ERROR(
            "VPI: Parent of type %s must be of type GPI_GENARRAY, "
            "GPI_LOGIC, GPI_LOGIC, GPI_ARRAY, or GPI_STRING to have an index.",
            parent->get_type_str());
        return NULL;
    }

    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to vpi_get_handle_by_index %s[%d]",
                  parent->get_name_str(), index);
        return NULL;
    }

    snprintf(buff, 14, "[%d]", index);

    std::string idx = buff;
    std::string name = parent->get_name() + idx;
    std::string fq_name = parent->get_fullname() + idx;
    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vpi_free_object(new_hdl);
        LOG_DEBUG("Unable to fetch object below entity (%s) at index (%d)",
                  parent->get_name_str(), index);
        return NULL;
    }
    return new_obj;
}

GpiObjHdl *VpiImpl::get_root_handle(const char *name) {
    vpiHandle root;
    vpiHandle iterator;
    GpiObjHdl *rv;
    std::string root_name;

    // vpi_iterate with a ref of NULL returns the top level module
    iterator = vpi_iterate(vpiModule, NULL);
    check_vpi_error();
    if (!iterator) {
        LOG_INFO("Nothing visible via VPI");
        return NULL;
    }

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {
        if (to_gpi_objtype(vpi_get(vpiType, root)) != GPI_MODULE) continue;

        // prevents finding virtual classes (which Xcelium puts at the top-level
        // scope) when looking for objects with get_root_handle.
        const char *obj_name = vpi_get_str(vpiFullName, root);
        if ((!name && obj_name[0] != '\\') || (name && !strcmp(name, obj_name)))
            break;
    }

    if (!root) {
        check_vpi_error();
        goto error;
    }

    // Need to free the iterator if it didn't return NULL
    if (iterator && !vpi_free_object(iterator)) {
        LOG_WARN("VPI: Attempting to free root iterator failed!");
        check_vpi_error();
    }

    root_name = vpi_get_str(vpiFullName, root);
    rv = new GpiObjHdl(this, root, to_gpi_objtype(vpi_get(vpiType, root)));
    rv->initialise(root_name, root_name);

    return rv;

error:

    LOG_ERROR("VPI: Couldn't find root handle %s", name);

    iterator = vpi_iterate(vpiModule, NULL);

    for (root = vpi_scan(iterator); root != NULL; root = vpi_scan(iterator)) {
        LOG_ERROR("VPI: Toplevel instances: %s != %s...", name,
                  vpi_get_str(vpiFullName, root));

        if (name == NULL || !strcmp(name, vpi_get_str(vpiFullName, root)))
            break;
    }

    return NULL;
}

GpiIterator *VpiImpl::iterate_handle(GpiObjHdl *obj_hdl,
                                     gpi_iterator_sel type) {
    GpiIterator *new_iter = NULL;
    switch (type) {
        case GPI_OBJECTS:
            new_iter = new VpiIterator(this, obj_hdl);
            break;
        case GPI_DRIVERS:
            new_iter = new VpiSingleIterator(this, obj_hdl, vpiDriver);
            break;
        case GPI_LOADS:
            new_iter = new VpiSingleIterator(this, obj_hdl, vpiLoad);
            break;
        case GPI_PACKAGE_SCOPES:
            new_iter = new VpiPackageIterator(this);
            break;
        default:
            LOG_WARN("Other iterator types not implemented yet");
            break;
    }
    return new_iter;
}

GpiCbHdl *VpiImpl::register_timed_callback(uint64_t time,
                                           int (*cb_func)(void *),
                                           void *cb_data) {
    auto cb_hdl = new VpiTimedCbHdl(this, time);
    auto err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        delete cb_hdl;
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *VpiImpl::register_readwrite_callback(int (*cb_func)(void *),
                                               void *cb_data) {
    auto cb_hdl = new VpiReadWriteCbHdl(this);
    auto err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        delete cb_hdl;
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *VpiImpl::register_readonly_callback(int (*cb_func)(void *),
                                              void *cb_data) {
    auto cb_hdl = new VpiReadOnlyCbHdl(this);
    auto err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        delete cb_hdl;
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

GpiCbHdl *VpiImpl::register_nexttime_callback(int (*cb_func)(void *),
                                              void *cb_data) {
    auto cb_hdl = new VpiNextPhaseCbHdl(this);
    auto err = cb_hdl->arm();
    // LCOV_EXCL_START
    if (err) {
        delete cb_hdl;
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb_hdl->set_cb_info(cb_func, cb_data);
    return cb_hdl;
}

// If the Python world wants things to shut down then unregister
// the callback for end of sim
void VpiImpl::sim_end() {
    m_sim_finish_cb->remove();
#ifdef ICARUS
    // Must skip checking return value on Icarus because their version of
    // vpi_control() returns void for some reason.
    vpi_control(vpiFinish, vpiDiagTimeLoc);
#else
    int ok = vpi_control(vpiFinish, vpiDiagTimeLoc);
    // LCOV_EXCL_START
    if (!ok) {
        LOG_DEBUG("VPI: Failed to end simulation");
        check_vpi_error();
    }
    // LCOV_EXCL_STOP
#endif
}

bool VpiImpl::compare_generate_labels(const std::string &a,
                                      const std::string &b) {
    /* Compare two generate labels for equality ignoring any suffixed index. */
    std::size_t a_idx = a.rfind("[");
    std::size_t b_idx = b.rfind("[");
    return a.substr(0, a_idx) == b.substr(0, b_idx);
}

const char *VpiImpl::get_type_delimiter(GpiObjHdl *obj_hdl) {
    return (obj_hdl->get_type() == GPI_PACKAGE) ? "" : ".";
}

static int startup_callback(void *) {
    s_vpi_vlog_info info;

    auto pass = vpi_get_vlog_info(&info);
    // LCOV_EXCL_START
    if (!pass) {
        LOG_ERROR("Unable to get argv and argc from simulator");
        info.argc = 0;
        info.argv = nullptr;
    }
    // LCOV_EXCL_STOP

    gpi_embed_init(info.argc, info.argv);

    return 0;
}

static int shutdown_callback(void *) {
    gpi_embed_end();
    return 0;
}

void VpiImpl::main() noexcept {
    auto startup_cb = new VpiStartupCbHdl(this);
    auto err = startup_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VPI: Unable to register startup callback! Simulation will end.");
        check_vpi_error();
        delete startup_cb;
        exit(1);
    }
    // LCOV_EXCL_STOP
    startup_cb->set_cb_info(startup_callback, nullptr);

    auto shutdown_cb = new VpiShutdownCbHdl(this);
    err = shutdown_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VPI: Unable to register shutdown callback! Simulation will end.");
        check_vpi_error();
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

static void vpi_main() {
#ifdef VCS
    // VCS loads the entry point both during compilation and again at
    // simulation. Only during simulation are most of the VPI routines
    // working. So we check if we are in compilation and exit early since we
    // don't need to do anything for compilation currently.
    s_vpi_vlog_info info;
    if (!vpi_get_vlog_info(&info)) {
        return;
    }
#endif
    auto vpi_table = new VpiImpl("VPI");
    vpi_table->main();
}

static void register_impl() {
    auto vpi_table = new VpiImpl("VPI");
    gpi_register_impl(vpi_table);
}

extern "C" {
COCOTBVPI_EXPORT void (*vlog_startup_routines[])() = {vpi_main, nullptr};

// For non-VPI compliant applications that cannot find vlog_startup_routines
// symbol
COCOTBVPI_EXPORT void vlog_startup_routines_bootstrap() { vpi_main(); }
}

GPI_ENTRY_POINT(cocotbvpi, register_impl)
