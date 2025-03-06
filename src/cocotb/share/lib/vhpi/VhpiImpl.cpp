// Copyright cocotb contributors
// Copyright (c) 2014, 2018 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "VhpiImpl.h"

#include <stdlib.h>

#include <cassert>
#include <cmath>
#include <cstring>

#include "_vendor/vhpi/vhpi_user.h"
#include "gpi_logging.h"
#include "vhpi_user_ext.h"

#ifdef NVC
#include <algorithm>
#endif

#define CASE_STR(_X) \
    case _X:         \
        return #_X

const char *VhpiImpl::format_to_string(int format) {
    switch (format) {
        CASE_STR(vhpiBinStrVal);
        CASE_STR(vhpiOctStrVal);
        CASE_STR(vhpiDecStrVal);
        CASE_STR(vhpiHexStrVal);
        CASE_STR(vhpiEnumVal);
        CASE_STR(vhpiSmallEnumVal);
        CASE_STR(vhpiIntVal);
        CASE_STR(vhpiLogicVal);
        CASE_STR(vhpiRealVal);
        CASE_STR(vhpiStrVal);
        CASE_STR(vhpiCharVal);
        CASE_STR(vhpiTimeVal);
        CASE_STR(vhpiPhysVal);
        CASE_STR(vhpiObjTypeVal);
        CASE_STR(vhpiPtrVal);
        CASE_STR(vhpiEnumVecVal);
        CASE_STR(vhpiRawDataVal);

        default:
            return "unknown";
    }
}

const char *VhpiImpl::reason_to_string(int reason) {
    switch (reason) {
        CASE_STR(vhpiCbValueChange);
        CASE_STR(vhpiCbStartOfNextCycle);
        CASE_STR(vhpiCbStartOfPostponed);
        CASE_STR(vhpiCbEndOfTimeStep);
        CASE_STR(vhpiCbNextTimeStep);
        CASE_STR(vhpiCbAfterDelay);
        CASE_STR(vhpiCbStartOfSimulation);
        CASE_STR(vhpiCbEndOfSimulation);
        CASE_STR(vhpiCbEndOfProcesses);
        CASE_STR(vhpiCbLastKnownDeltaCycle);

        default:
            return "unknown";
    }
}

#undef CASE_STR

void VhpiImpl::get_sim_time(uint32_t *high, uint32_t *low) {
    vhpiTimeT vhpi_time_s;
    vhpi_get_time(&vhpi_time_s, NULL);
    check_vhpi_error();
    *high = vhpi_time_s.high;
    *low = vhpi_time_s.low;
}

static int32_t log10int(uint64_t v) {
    int32_t i = -1;
    do {
        v /= 10;
        i += 1;
    } while (v);
    return i;
}

void VhpiImpl::get_sim_precision(int32_t *precision) {
    /* The value returned is in number of femtoseconds */
    vhpiPhysT prec = vhpi_get_phys(vhpiResolutionLimitP, NULL);
    uint64_t femtoseconds = ((uint64_t)prec.high << 32) | prec.low;
    *precision = log10int(femtoseconds) - 15;
}

const char *VhpiImpl::get_simulator_product() {
    if (m_product.empty()) {
        vhpiHandleT tool = vhpi_handle(vhpiTool, NULL);
        if (tool) {
            m_product = vhpi_get_str(vhpiNameP, tool);
            vhpi_release_handle(tool);
        } else {
            m_product = "UNKNOWN";
        }
    }
    return m_product.c_str();
}

const char *VhpiImpl::get_simulator_version() {
    if (m_version.empty()) {
        vhpiHandleT tool = vhpi_handle(vhpiTool, NULL);
        if (tool) {
            m_version = vhpi_get_str(vhpiToolVersionP, tool);
            vhpi_release_handle(tool);
        } else {
            m_version = "UNKNOWN";
        }
    }
    return m_version.c_str();
}

// Determine whether a VHPI object type is a constant or not
bool is_const(vhpiHandleT hdl) {
    vhpiHandleT tmp = hdl;

    /* Need to walk the prefix's back to the original handle to get a type
     * that is not vhpiSelectedNameK or vhpiIndexedNameK
     */
    do {
        vhpiIntT vhpitype = vhpi_get(vhpiKindP, tmp);
        if (vhpiConstDeclK == vhpitype || vhpiGenericDeclK == vhpitype)
            return true;
    } while ((tmp = vhpi_handle(vhpiPrefix, tmp)) != NULL);

    return false;
}

bool is_enum_logic(vhpiHandleT hdl) {
    const char *type = vhpi_get_str(vhpiNameP, hdl);

    if (0 == strncmp(type, "BIT", sizeof("BIT") - 1) ||
        0 == strncmp(type, "STD_ULOGIC", sizeof("STD_ULOGIC") - 1) ||
        0 == strncmp(type, "STD_LOGIC", sizeof("STD_LOGIC") - 1)) {
        return true;
    } else {
        vhpiIntT num_enum = vhpi_get(vhpiNumLiteralsP, hdl);

        if (2 == num_enum) {
            vhpiHandleT it = vhpi_iterator(vhpiEnumLiterals, hdl);
            if (it != NULL) {
                const char *enums_1[2] = {
                    "0", "1"};  // Aldec does not return the single quotes
                const char *enums_2[2] = {"'0'", "'1'"};
                vhpiHandleT enum_hdl;
                int cnt = 0;

                while ((enum_hdl = vhpi_scan(it)) != NULL) {
                    const char *etype = vhpi_get_str(vhpiStrValP, enum_hdl);
                    if (1 < cnt || (0 != strncmp(etype, enums_1[cnt],
                                                 strlen(enums_1[cnt])) &&
                                    0 != strncmp(etype, enums_2[cnt],
                                                 strlen(enums_2[cnt])))) {
                        vhpi_release_handle(it);
                        return false;
                    }
                    ++cnt;
                }
                return true;
            }
        } else if (9 == num_enum) {
            vhpiHandleT it = vhpi_iterator(vhpiEnumLiterals, hdl);
            if (it != NULL) {
                const char *enums_1[9] = {
                    "U", "X", "0", "1", "Z",
                    "W", "L", "H", "-"};  // Aldec does not return the single
                                          // quotes
                const char *enums_2[9] = {"'U'", "'X'", "'0'", "'1'", "'Z'",
                                          "'W'", "'L'", "'H'", "'-'"};
                vhpiHandleT enum_hdl;
                int cnt = 0;

                while ((enum_hdl = vhpi_scan(it)) != NULL) {
                    const char *etype = vhpi_get_str(vhpiStrValP, enum_hdl);
                    if (8 < cnt || (0 != strncmp(etype, enums_1[cnt],
                                                 strlen(enums_1[cnt])) &&
                                    0 != strncmp(etype, enums_2[cnt],
                                                 strlen(enums_2[cnt])))) {
                        vhpi_release_handle(it);
                        return false;
                    }
                    ++cnt;
                }
                return true;
            }
        }
    }

    return false;
}

bool is_enum_char(vhpiHandleT hdl) {
    const vhpiIntT NUM_ENUMS_IN_CHAR_TYPE = 256;

    const char *type = vhpi_get_str(vhpiNameP, hdl);

    if (0 == strncmp(type, "CHARACTER", sizeof("STD_ULOGIC") - 1)) {
        return true;
    } else {
        return (vhpi_get(vhpiNumLiteralsP, hdl) == NUM_ENUMS_IN_CHAR_TYPE);
    }
}

bool is_enum_boolean(vhpiHandleT hdl) {
    const char *type = vhpi_get_str(vhpiNameP, hdl);

    if (0 == strncmp(type, "BOOLEAN", sizeof("BOOLEAN") - 1)) {
        return true;
    } else {
        vhpiIntT num_enum = vhpi_get(vhpiNumLiteralsP, hdl);

        if (2 == num_enum) {
            vhpiHandleT it = vhpi_iterator(vhpiEnumLiterals, hdl);
            if (it != NULL) {
                vhpiHandleT enum_hdl;
                int cnt = 0;

                while ((enum_hdl = vhpi_scan(it)) != NULL) {
                    const char *etype = vhpi_get_str(vhpiStrValP, enum_hdl);
                    if (((0 == cnt &&
                          0 != strncmp(etype, "FALSE", strlen("FALSE"))) &&
                         (0 == cnt &&
                          0 != strncmp(etype, "false", strlen("false")))) ||
                        ((1 == cnt &&
                          0 != strncmp(etype, "TRUE", strlen("TRUE"))) &&
                         (1 == cnt &&
                          0 != strncmp(etype, "true", strlen("true")))) ||
                        2 <= cnt) {
                        vhpi_release_handle(it);
                        return false;
                    }
                    ++cnt;
                }
                return true;
            }
        }
    }

    return false;
}

static bool compare_names(const std::string &a, const std::string &b) {
#ifdef NVC
    /* NVC does not properly implement the CaseName property and returns
       Names instead (nickg/nvc#723). */
    return a.size() == b.size() &&
           equal(a.begin(), a.end(), b.begin(), [](char x, char y) {
               return std::toupper(x) == std::toupper(y);
           });
#else
    return a == b;
#endif
}

GpiObjHdl *VhpiImpl::create_gpi_obj_from_handle(vhpiHandleT new_hdl,
                                                const std::string &name,
                                                const std::string &fq_name) {
    vhpiIntT type;
    gpi_objtype gpi_type;
    GpiObjHdl *new_obj = NULL;

    if (vhpiVerilog == (type = vhpi_get(vhpiKindP, new_hdl))) {
        LOG_DEBUG("VHPI: vhpiVerilog returned from vhpi_get(vhpiType, ...)");
        return NULL;
    }

    /* We need to delve further here to determine how to later set
       the values of an object */
    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, new_hdl);

    if (base_hdl == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, new_hdl);

        if (st_hdl != NULL) {
            base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    vhpiHandleT query_hdl = (base_hdl != NULL) ? base_hdl : new_hdl;

    vhpiIntT base_type = vhpi_get(vhpiKindP, query_hdl);
    switch (base_type) {
        case vhpiArrayTypeDeclK: {
            vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, query_hdl);

            if (num_dim > 1) {
                LOG_DEBUG("VHPI: Detected a MULTI-DIMENSIONAL ARRAY type %s",
                          fq_name.c_str());
                gpi_type = GPI_ARRAY;
            } else {
                vhpiHandleT elem_base_type_hdl = NULL;
                vhpiIntT elem_base_type = 0;

                vhpiHandleT elem_sub_type_hdl =
                    vhpi_handle(vhpiElemType, query_hdl);
                /* vhpiElemType is not supported in all simulators. */
                if (!elem_sub_type_hdl) {
                    elem_sub_type_hdl = vhpi_handle(vhpiElemSubtype, query_hdl);
                }

                if (elem_sub_type_hdl != NULL) {
                    elem_base_type_hdl =
                        vhpi_handle(vhpiBaseType, elem_sub_type_hdl);
                    if (elem_base_type_hdl == NULL) {
                        elem_base_type_hdl = elem_sub_type_hdl;
                    } else {
                        vhpi_release_handle(elem_sub_type_hdl);
                    }
                }

                if (elem_base_type_hdl != NULL) {
                    elem_base_type = vhpi_get(vhpiKindP, elem_base_type_hdl);
                    if (elem_base_type == vhpiEnumTypeDeclK) {
                        if (is_enum_logic(elem_base_type_hdl)) {
                            LOG_DEBUG("VHPI: Detected a LOGIC VECTOR type %s",
                                      fq_name.c_str());
                            gpi_type = GPI_LOGIC_ARRAY;
                        } else if (is_enum_char(elem_base_type_hdl)) {
                            LOG_DEBUG("VHPI: Detected a STRING type %s",
                                      fq_name.c_str());
                            gpi_type = GPI_STRING;
                        } else {
                            LOG_DEBUG(
                                "VHPI: Detected a NON-LOGIC ENUM VECTOR type "
                                "%s",
                                fq_name.c_str());
                            gpi_type = GPI_ARRAY;
                        }
                    } else {
                        LOG_DEBUG("VHPI: Detected a NON-ENUM VECTOR type %s",
                                  fq_name.c_str());
                        gpi_type = GPI_ARRAY;
                    }
                } else {
                    LOG_ERROR(
                        "VHPI: Unable to determine the Array Element Base Type "
                        "for %s.  Defaulting to GPI_ARRAY.",
                        vhpi_get_str(vhpiFullCaseNameP, new_hdl));
                    gpi_type = GPI_ARRAY;
                }
            }
            break;
        }

        case vhpiEnumTypeDeclK: {
            if (is_enum_logic(query_hdl)) {
                LOG_DEBUG("VHPI: Detected a LOGIC type %s", fq_name.c_str());
                gpi_type = GPI_LOGIC;
            } else if (is_enum_char(query_hdl)) {
                LOG_DEBUG("VHPI: Detected a CHAR type %s", fq_name.c_str());
                gpi_type = GPI_INTEGER;
            } else if (is_enum_boolean(query_hdl)) {
                LOG_DEBUG("VHPI: Detected a BOOLEAN/INTEGER type %s",
                          fq_name.c_str());
                gpi_type = GPI_INTEGER;
            } else {
                LOG_DEBUG("VHPI: Detected an ENUM type %s", fq_name.c_str());
                gpi_type = GPI_ENUM;
            }
            break;
        }

        case vhpiIntTypeDeclK: {
            LOG_DEBUG("VHPI: Detected an INT type %s", fq_name.c_str());
            gpi_type = GPI_INTEGER;
            break;
        }

        case vhpiFloatTypeDeclK: {
            LOG_DEBUG("VHPI: Detected a REAL type %s", fq_name.c_str());
            gpi_type = GPI_REAL;
            break;
        }

        case vhpiRecordTypeDeclK: {
            LOG_DEBUG("VHPI: Detected a STRUCTURE type %s", fq_name.c_str());
            gpi_type = GPI_STRUCTURE;
            break;
        }

        case vhpiProcessStmtK:
        case vhpiSimpleSigAssignStmtK:
        case vhpiCondSigAssignStmtK:
        case vhpiSelectSigAssignStmtK: {
            gpi_type = GPI_MODULE;
            break;
        }

        case vhpiRootInstK:
        case vhpiIfGenerateK:
        case vhpiForGenerateK:
        case vhpiBlockStmtK:
        case vhpiCompInstStmtK: {
            std::string hdl_name = vhpi_get_str(vhpiCaseNameP, new_hdl);

            if (base_type == vhpiRootInstK && !compare_names(hdl_name, name)) {
                vhpiHandleT arch = vhpi_handle(vhpiDesignUnit, new_hdl);

                if (NULL != arch) {
                    vhpiHandleT prim = vhpi_handle(vhpiPrimaryUnit, arch);

                    if (NULL != prim) {
                        hdl_name = vhpi_get_str(vhpiCaseNameP, prim);
                    }
                }
            }

            if (!compare_names(name, hdl_name)) {
                LOG_DEBUG("VHPI: Found pseudo-region %s", fq_name.c_str());
                gpi_type = GPI_GENARRAY;
            } else {
                gpi_type = GPI_MODULE;
            }
            break;
        }

        default: {
            vhpiIntT is_static = vhpi_get(vhpiStaticnessP, query_hdl);

            /* Non locally static objects are not accessible for read/write
               so we create this as a GpiObjType
            */
            if (is_static == vhpiGloballyStatic) {
                gpi_type = GPI_MODULE;
                break;
            }

            LOG_ERROR("VHPI: Not able to map type (%s) %u to object",
                      vhpi_get_str(vhpiKindStrP, query_hdl), type);
            new_obj = NULL;
            goto out;
        }
    }

    LOG_DEBUG("VHPI: Creating %s of type %d (%s)",
              vhpi_get_str(vhpiFullCaseNameP, new_hdl), gpi_type,
              vhpi_get_str(vhpiKindStrP, query_hdl));

    switch (gpi_type) {
        case GPI_ARRAY: {
            new_obj = new VhpiArrayObjHdl(this, new_hdl, gpi_type);
            break;
        }
        case GPI_GENARRAY:
        case GPI_MODULE:
        case GPI_STRUCTURE:
        case GPI_PACKAGE: {
            new_obj = new VhpiObjHdl(this, new_hdl, gpi_type);
            break;
        }
        case GPI_LOGIC:
        case GPI_LOGIC_ARRAY: {
            new_obj = new VhpiLogicSignalObjHdl(this, new_hdl, gpi_type,
                                                is_const(new_hdl));
            break;
        }
        default: {
            new_obj = new VhpiSignalObjHdl(this, new_hdl, gpi_type,
                                           is_const(new_hdl));
            break;
        }
    }

    if (new_obj->initialise(name, fq_name)) {
        delete new_obj;
        new_obj = NULL;
    }

out:
    if (base_hdl != NULL) vhpi_release_handle(base_hdl);

    return new_obj;
}

static std::string fully_qualified_name(const std::string &name,
                                        GpiObjHdl *parent) {
    std::string fq_name = parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }
#ifdef NVC
    /* Convert to a canonical form to avoid problems with case insensitivity. */
    std::transform(fq_name.begin(), fq_name.end(), fq_name.begin(), ::toupper);
#endif
    return fq_name;
}

GpiObjHdl *VhpiImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent) {
    LOG_DEBUG("VHPI: Trying to convert raw to VHPI handle");

    vhpiHandleT new_hdl = (vhpiHandleT)raw_hdl;

    const char *c_name = vhpi_get_str(vhpiCaseNameP, new_hdl);
    if (!c_name) {
        LOG_DEBUG("VHPI: Unable to query name of passed in handle");
        return NULL;
    }

    std::string name = c_name;
    std::string fq_name = fully_qualified_name(name, parent);

    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("VHPI: Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(const std::string &name,
                                         GpiObjHdl *parent) {
    vhpiHandleT vhpi_hdl = parent->get_handle<vhpiHandleT>();

    vhpiHandleT new_hdl;
    std::string fq_name = fully_qualified_name(name, parent);

    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    new_hdl = vhpi_handle_by_name(&writable[0], NULL);

    if (new_hdl == NULL && parent->get_type() == GPI_STRUCTURE) {
        /* vhpi_handle_by_name() doesn't always work for records, specifically
         * records in generics */
        vhpiHandleT iter = vhpi_iterator(vhpiSelectedNames, vhpi_hdl);
        if (iter != NULL) {
            while ((new_hdl = vhpi_scan(iter)) != NULL) {
                std::string selected_name =
                    vhpi_get_str(vhpiCaseNameP, new_hdl);
                std::size_t found = selected_name.find_last_of(".");

                if (found != std::string::npos) {
                    selected_name = selected_name.substr(found + 1);
                }

                if (compare_names(selected_name, name)) {
                    vhpi_release_handle(iter);
                    break;
                }
            }
        }
    } else if (new_hdl == NULL) {
        /* If not found, check to see if the name of a generate loop */
        vhpiHandleT iter = vhpi_iterator(vhpiInternalRegions, vhpi_hdl);

        if (iter != NULL) {
            vhpiHandleT rgn;
            for (rgn = vhpi_scan(iter); rgn != NULL; rgn = vhpi_scan(iter)) {
                if (vhpi_get(vhpiKindP, rgn) == vhpiForGenerateK) {
                    std::string rgn_name = vhpi_get_str(vhpiCaseNameP, rgn);
                    if (compare_generate_labels(rgn_name, name)) {
                        new_hdl = vhpi_hdl;
                        vhpi_release_handle(iter);
                        break;
                    }
                }
            }
        }
        if (new_hdl == NULL) {
            LOG_DEBUG("VHPI: Unable to query vhpi_handle_by_name %s",
                      fq_name.c_str());
            return NULL;
        }
    }

    /* Generate Loops have inconsistent behavior across VHPI.  A "name"
     * without an index, i.e. dut.loop vs dut.loop(0), may or may not map to
     * to the start index.  If it doesn't then it won't find anything.
     *
     * If this unique case is hit, we need to create the Pseudo-region, with the
     * handle being equivalent to the parent handle.
     */
    if (vhpi_get(vhpiKindP, new_hdl) == vhpiForGenerateK) {
        vhpi_release_handle(new_hdl);

        new_hdl = vhpi_hdl;
    }

    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("VHPI: Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(int32_t index, GpiObjHdl *parent) {
    vhpiHandleT vhpi_hdl = parent->get_handle<vhpiHandleT>();
    std::string name = parent->get_name();
    std::string fq_name = parent->get_fullname();
    vhpiHandleT new_hdl = NULL;
    char buff[14];  // needs to be large enough to hold -2^31 to 2^31-1 in
                    // string form ('(''-'10+'')'\0')

    gpi_objtype obj_type = parent->get_type();

    if (obj_type == GPI_GENARRAY) {
        LOG_DEBUG(
            "VHPI: Native check create for index %d of parent %s "
            "(pseudo-region)",
            index, parent->get_name_str());

        snprintf(buff, sizeof(buff), "%d", index);

        std::string idx_str = buff;
        name += (GEN_IDX_SEP_LHS + idx_str + GEN_IDX_SEP_RHS);
        fq_name += (GEN_IDX_SEP_LHS + idx_str + GEN_IDX_SEP_RHS);

        std::vector<char> writable(fq_name.begin(), fq_name.end());
        writable.push_back('\0');

        new_hdl = vhpi_handle_by_name(&writable[0], NULL);
    } else if (obj_type == GPI_LOGIC || obj_type == GPI_LOGIC_ARRAY ||
               obj_type == GPI_ARRAY || obj_type == GPI_STRING) {
        LOG_DEBUG("VHPI: Native check create for index %d of parent %s (%s)",
                  index, parent->get_fullname_str(),
                  vhpi_get_str(vhpiKindStrP, vhpi_hdl));

        snprintf(buff, sizeof(buff), "(%d)", index);

        std::string idx_str = buff;
        name += idx_str;
        fq_name += idx_str;

        vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, vhpi_hdl);

        if (base_hdl == NULL) {
            vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, vhpi_hdl);

            if (st_hdl != NULL) {
                base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
                vhpi_release_handle(st_hdl);
            }
        }

        if (base_hdl == NULL) {
            LOG_ERROR("VHPI: Unable to get the vhpiBaseType of %s",
                      parent->get_fullname_str());
            return NULL;
        }

        vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, base_hdl);
        int idx = 0;

        /* Need to translate the index into a zero-based flattened array index
         */
        if (num_dim > 1) {
            std::string hdl_name = vhpi_get_str(vhpiCaseNameP, vhpi_hdl);
            std::vector<int> indices;

            /* Need to determine how many indices have been received.  A valid
             * handle will only be found when all indices are received,
             * otherwise need a pseudo-handle.
             *
             * When working with pseudo-handles:
             *              hdl_name:   sig_name
             *    parent->get_name():   sig_name(x)(y)...  where x,y,... are the
             * indices to a multi-dimensional array. pseudo_idx:   (x)(y)...
             */
            if (hdl_name.length() < parent->get_name().length()) {
                std::string pseudo_idx =
                    parent->get_name().substr(hdl_name.length());

                while (pseudo_idx.length() > 0) {
                    std::size_t found = pseudo_idx.find_first_of(")");

                    if (found != std::string::npos) {
                        indices.push_back(
                            atoi(pseudo_idx.substr(1, found - 1).c_str()));
                        pseudo_idx = pseudo_idx.substr(found + 1);
                    } else {
                        break;
                    }
                }
            }

            indices.push_back(index);

            if (indices.size() == num_dim) {
#ifdef IUS
                /* IUS/Xcelium does not appear to set the vhpiIsUnconstrainedP
                 * property.  IUS Docs say it will return -1 if unconstrained,
                 * but with vhpiIntT being unsigned, the value returned is
                 * below.
                 */
                const vhpiIntT UNCONSTRAINED = 2147483647;
#endif

                std::vector<vhpiHandleT> constraints;

                /* All necessary indices are available, need to iterate over
                 * dimension constraints to determine the index into the
                 * zero-based flattened array.
                 *
                 * Check the constraints on the base type first. (always works
                 * for Aldec, but not unconstrained types in IUS/Xcelium) If the
                 * base type fails, then try the sub-type.  (sub-type is listed
                 * as deprecated for Aldec)
                 */
                vhpiHandleT it, constraint;

                it = vhpi_iterator(vhpiConstraints, base_hdl);

                if (it != NULL) {
                    while ((constraint = vhpi_scan(it)) != NULL) {
#ifdef IUS
                        vhpiIntT l_rng = vhpi_get(vhpiLeftBoundP, constraint);
                        vhpiIntT r_rng = vhpi_get(vhpiRightBoundP, constraint);
                        if (l_rng == UNCONSTRAINED || r_rng == UNCONSTRAINED) {
#else
                        if (vhpi_get(vhpiIsUnconstrainedP, constraint)) {
#endif
                            /* Bail and try the sub-type handle */
                            vhpi_release_handle(it);
                            break;
                        }
                        constraints.push_back(constraint);
                    }
                }

                /* If all the dimensions were not obtained, try again with the
                 * sub-type handle */
                if (constraints.size() != num_dim) {
                    vhpiHandleT sub_hdl = vhpi_handle(vhpiSubtype, vhpi_hdl);
                    ;

                    constraints.clear();

                    if (sub_hdl != NULL) {
                        it = vhpi_iterator(vhpiConstraints, sub_hdl);

                        if (it != NULL) {
                            while ((constraint = vhpi_scan(it)) != NULL) {
                                /* IUS/Xcelium only sets the
                                 * vhpiIsUnconstrainedP incorrectly on the base
                                 * type */
                                if (vhpi_get(vhpiIsUnconstrainedP,
                                             constraint)) {
                                    vhpi_release_handle(it);
                                    break;
                                }
                                constraints.push_back(constraint);
                            }
                        }
                    }
                }

                if (constraints.size() == num_dim) {
                    int scale = 1;

                    while (constraints.size() > 0) {
                        int raw_idx = indices.back();
                        constraint = constraints.back();

                        int left = static_cast<int>(
                            vhpi_get(vhpiLeftBoundP, constraint));
                        int right = static_cast<int>(
                            vhpi_get(vhpiRightBoundP, constraint));
                        int len = 0;

                        if (left > right) {
                            idx += (scale * (left - raw_idx));
                            len = left - right + 1;
                        } else {
                            idx += (scale * (raw_idx - left));
                            len = right - left + 1;
                        }
                        scale = scale * len;

                        indices.pop_back();
                        constraints.pop_back();
                    }
                } else {
                    LOG_ERROR("VHPI: Unable to access all constraints for %s",
                              parent->get_fullname_str());
                    return NULL;
                }

            } else {
                new_hdl = vhpi_hdl;  // Set to the parent handle to create the
                                     // pseudo-handle
            }
        } else {
            int left = parent->get_range_left();
            int right = parent->get_range_right();

            if (left > right) {
                idx = left - index;
            } else {
                idx = index - left;
            }
        }

        if (new_hdl == NULL) {
            new_hdl = vhpi_handle_by_index(vhpiIndexedNames, vhpi_hdl, idx);
            if (!new_hdl) {
                /* Support for the above seems poor, so if it did not work
                   try an iteration instead, spotty support for
                   multi-dimensional arrays */

                vhpiHandleT iter = vhpi_iterator(vhpiIndexedNames, vhpi_hdl);
                if (iter != NULL) {
                    int curr_index = 0;
                    while ((new_hdl = vhpi_scan(iter)) != NULL) {
                        if (idx == curr_index) {
                            vhpi_release_handle(iter);
                            break;
                        }
                        curr_index++;
                    }
                }
            }

            if (new_hdl != NULL) {
                LOG_DEBUG("VHPI: Index (%d->%d) found %s (%s)", index, idx,
                          vhpi_get_str(vhpiCaseNameP, new_hdl),
                          vhpi_get_str(vhpiKindStrP, new_hdl));
            }
        }
    } else {
        LOG_ERROR(
            "VHPI: Parent of type %s must be of type GPI_GENARRAY, "
            "GPI_LOGIC, GPI_ARRAY, or GPI_STRING to have an index.",
            parent->get_type_str());
        return NULL;
    }

    if (new_hdl == NULL) {
        LOG_DEBUG("VHPI: Unable to query vhpi_handle_by_index %d", index);
        return NULL;
    }

    GpiObjHdl *new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG(
            "VHPI: Could not fetch object below entity (%s) at index (%d)",
            parent->get_name_str(), index);
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::get_root_handle(const char *name) {
    vhpiHandleT root = vhpi_handle(vhpiRootInst, NULL);
    if (!root) {
        LOG_ERROR("VHPI: Attempting to get the vhpiRootInst failed");
        check_vhpi_error();
        return NULL;
    }

    // IEEE 1076-2019 Clause 19.4.3
    // For an object of class rootInst, the values of the Name and CaseName
    // properties are the simple name of the entity declaration whose
    // instantiation is represented by the object.
    std::string root_name = vhpi_get_str(vhpiCaseNameP, root);
    LOG_DEBUG("VHPI: We have found root='%s'", root_name.c_str());

    if (name && !compare_names(name, root_name)) {
        LOG_DEBUG(
            "VHPI: root name '%s' doesn't match requested name '%s'. Trying "
            "fallbacks",
            root_name.c_str(), name);
    } else {
        return create_gpi_obj_from_handle(root, root_name, root_name);
    }

    // Some simulators do not return the correct entity name for rootInst,
    // so implement fallbacks.

    // First, try to get the entity (primaryUnit) associated with the rootInst
    // and its name.
    vhpiHandleT arch = vhpi_handle(vhpiDesignUnit, root);
    if (!arch) {
        LOG_DEBUG(
            "VHPI: Unable to get vhpiDesignUnit (arch) from root handle. "
            "Trying handle lookup by name");
        check_vhpi_error();
    }

    vhpiHandleT entity = NULL;
    if (arch && !(entity = vhpi_handle(vhpiPrimaryUnit, arch))) {
        LOG_DEBUG(
            "VHPI: Unable to get vhpiPrimaryUnit (entity) from arch handle. "
            "Trying handle lookup by name");
        check_vhpi_error();
    }

    if (entity) {
        root_name = vhpi_get_str(vhpiCaseNameP, entity);

        // If this matches the name then it is what we want,
        // but we use the root handle two levels up as the DUT
        // because we do not want an object of type vhpiEntityDeclK as the DUT
        if (name && !compare_names(name, root_name)) {
            LOG_DEBUG(
                "VHPI: Root entity name '%s' doesn't match requested name "
                "'%s'. Trying handle lookup by name",
                root_name.c_str(), name);
        } else {
            return create_gpi_obj_from_handle(root, root_name, root_name);
        }
    }

    // Second, we search for the root handle by name
    if (!name) {
        // name should never be null here, but fail if it is.
        LOG_ERROR("VHPI: Couldn't find root handle");
        return NULL;
    }

    // Search using hierarchical path, which starts with ':',
    // to disambiguate with library information model objects
    // that have the same name as the rootInst entity.
    std::string search_name;
    if (name[0] != ':') {
        search_name = ":";
    }
    search_name += name;

    vhpiHandleT dut = vhpi_handle_by_name(search_name.c_str(), NULL);
    if (!dut) {
        LOG_DEBUG("VHPI: Unable to get root handle by name");
        check_vhpi_error();
    } else {
        root_name = vhpi_get_str(vhpiCaseNameP, dut);
        vhpiIntT dut_kind = vhpi_get(vhpiKindP, dut);
        std::string dut_kind_str = vhpi_get_str(vhpiKindStrP, dut);

        if (!compare_names(name, root_name)) {
            LOG_DEBUG(
                "VHPI: found root handle of type %s (%d) with name '%s' "
                "doesn't match requested name '%s'",
                dut_kind_str.c_str(), dut_kind, root_name.c_str(), name);
        } else {
            return create_gpi_obj_from_handle(dut, root_name, root_name);
        }
    }

    LOG_ERROR("VHPI: Couldn't find root handle '%s'", name);
    return NULL;
}

GpiIterator *VhpiImpl::iterate_handle(GpiObjHdl *obj_hdl,
                                      gpi_iterator_sel type) {
    GpiIterator *new_iter = NULL;

    switch (type) {
        case GPI_OBJECTS:
            new_iter = new VhpiIterator(this, obj_hdl);
            break;
        case GPI_DRIVERS:
            LOG_WARN("VHPI: Drivers iterator not implemented yet");
            break;
        case GPI_LOADS:
            LOG_WARN("VHPI: Loads iterator not implemented yet");
            break;
        default:
            LOG_WARN("VHPI: Other iterator types not implemented yet");
            break;
    }
    return new_iter;
}

GpiCbHdl *VhpiImpl::register_timed_callback(uint64_t time,
                                            int (*cb_func)(void *),
                                            void *cb_data) {
    auto *cb_hdl = new VhpiTimedCbHdl(this, time);

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

GpiCbHdl *VhpiImpl::register_readwrite_callback(int (*cb_func)(void *),
                                                void *cb_data) {
    auto *cb_hdl = new VhpiReadWriteCbHdl(this);

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

GpiCbHdl *VhpiImpl::register_readonly_callback(int (*cb_func)(void *),
                                               void *cb_data) {
    auto *cb_hdl = new VhpiReadOnlyCbHdl(this);

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

GpiCbHdl *VhpiImpl::register_nexttime_callback(int (*cb_func)(void *),
                                               void *cb_data) {
    auto *cb_hdl = new VhpiNextPhaseCbHdl(this);

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

void VhpiImpl::sim_end() {
    m_sim_finish_cb->remove();
    int err = vhpi_control(vhpiFinish, vhpiDiagTimeLoc);
    // LCOV_EXCL_START
    if (err) {
        LOG_DEBUG("VHPI: Failed to end simulation");
        check_vhpi_error();
    }
    // LCOV_EXCL_STOP
}

bool VhpiImpl::compare_generate_labels(const std::string &a,
                                       const std::string &b) {
    /* Compare two generate labels for equality ignoring any suffixed index. */
    std::size_t a_idx = a.rfind(GEN_IDX_SEP_LHS);
    std::size_t b_idx = b.rfind(GEN_IDX_SEP_LHS);
    return compare_names(a.substr(0, a_idx), b.substr(0, b_idx));
}

static int startup_callback(void *) {
    vhpiHandleT tool, argv_iter, argv_hdl;
    char **tool_argv = NULL;
    int tool_argc = 0;
    int i = 0;

    tool = vhpi_handle(vhpiTool, NULL);
    if (tool) {
        tool_argc = static_cast<int>(vhpi_get(vhpiArgcP, tool));
        tool_argv = new char *[tool_argc];
        assert(tool_argv);

        argv_iter = vhpi_iterator(vhpiArgvs, tool);
        if (argv_iter) {
            while ((argv_hdl = vhpi_scan(argv_iter))) {
                tool_argv[i] = const_cast<char *>(static_cast<const char *>(
                    vhpi_get_str(vhpiStrValP, argv_hdl)));
                i++;
            }
        }

        vhpi_release_handle(tool);
    }

    gpi_embed_init(tool_argc, tool_argv);
    delete[] tool_argv;

    return 0;
}

static int shutdown_callback(void *) {
    gpi_embed_end();
    return 0;
}

void VhpiImpl::main() noexcept {
    auto startup_cb = new VhpiStartupCbHdl(this);
    auto err = startup_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VHPI: Unable to register startup callback! Simulation will end.");
        check_vhpi_error();
        delete startup_cb;
        exit(1);
    }
    // LCOV_EXCL_STOP
    startup_cb->set_cb_info(startup_callback, nullptr);

    auto shutdown_cb = new VhpiShutdownCbHdl(this);
    err = shutdown_cb->arm();
    // LCOV_EXCL_START
    if (err) {
        LOG_CRITICAL(
            "VHPI: Unable to register shutdown callback! Simulation will end.");
        check_vhpi_error();
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

static void vhpi_main() {
    auto vhpi_table = new VhpiImpl("VHPI");
    vhpi_table->main();
}

static void register_impl() {
    auto vhpi_table = new VhpiImpl("VHPI");
    gpi_register_impl(vhpi_table);
}

// pre-defined VHPI registration table
extern "C" {
COCOTBVHPI_EXPORT void (*vhpi_startup_routines[])() = {vhpi_main, nullptr};

// For non-VHPI compliant applications that cannot find vhpi_startup_routines
COCOTBVHPI_EXPORT void vhpi_startup_routines_bootstrap() { vhpi_main(); }
}

GPI_ENTRY_POINT(cocotbvhpi, register_impl)
