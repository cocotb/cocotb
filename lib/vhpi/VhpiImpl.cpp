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
*    * Neither the name of Potential Ventures Ltd not the
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

#include "VhpiImpl.h"
#include <cmath>
#include <algorithm>
#include <stdlib.h>

extern "C" {
static VhpiCbHdl *sim_init_cb;
static VhpiCbHdl *sim_finish_cb;
static VhpiImpl  *vhpi_table;
}

#define CASE_STR(_X) \
    case _X: return #_X

const char * VhpiImpl::format_to_string(int format)
{
    switch (format) {
        CASE_STR(vhpiBinStrVal);
        CASE_STR(vhpiOctStrVal);
        CASE_STR(vhpiDecStrVal);
        CASE_STR(vhpiHexStrVal);
        CASE_STR(vhpiEnumVal);
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

        default: return "unknown";
    }
}

const char *VhpiImpl::reason_to_string(int reason)
{
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

        default: return "unknown";
    }
}

#undef CASE_STR

void VhpiImpl::get_sim_time(uint32_t *high, uint32_t *low)
{
    vhpiTimeT vhpi_time_s;
    vhpi_get_time(&vhpi_time_s, NULL);
    check_vhpi_error();
    *high = vhpi_time_s.high;
    *low = vhpi_time_s.low;
}

void VhpiImpl::get_sim_precision(int32_t *precision)
{
    /* The value returned is in number of femtoseconds */
    vhpiPhysT prec = vhpi_get_phys(vhpiResolutionLimitP, NULL);
    uint64_t femtoseconds = ((uint64_t)prec.high << 32) | prec.low;
    double base = 1e-15 * femtoseconds;
    *precision = (int32_t)log10(base);
}

// Determine whether a VHPI object type is a constant or not
bool is_const(vhpiHandleT hdl)
{
    vhpiHandleT tmp = hdl;

    /* Need to walk the prefix's back to the original handle to get a type
     * that is not vhpiSelectedNameK or vhpiIndexedNameK
     */
    do {
        vhpiIntT vhpitype = vhpi_get(vhpiKindP, tmp);
        if (vhpiConstDeclK == vhpitype || vhpiGenericDeclK == vhpitype)
            return true;
    } while ((tmp = vhpi_handle(vhpiPrefix,tmp)) != NULL);

    return false;
}

bool is_enum_logic(vhpiHandleT hdl) {
    const char *type = vhpi_get_str(vhpiNameP, hdl);

    if (0 == strncmp(type, "BIT"       , sizeof("BIT")-1)        ||
        0 == strncmp(type, "STD_ULOGIC", sizeof("STD_ULOGIC")-1) ||
        0 == strncmp(type, "STD_LOGIC" , sizeof("STD_LOGIC")-1)) {
        return true;
    } else {
        vhpiIntT num_enum = vhpi_get(vhpiNumLiteralsP, hdl);

        if (2 == num_enum) {
            vhpiHandleT it = vhpi_iterator(vhpiEnumLiterals, hdl);
            if (it != NULL) {
                const char *enums_1[2] = { "0",   "1"}; //Aldec does not return the single quotes
                const char *enums_2[2] = {"'0'", "'1'"};
                vhpiHandleT enum_hdl;
                int cnt = 0;

                while ((enum_hdl = vhpi_scan(it)) != NULL) {
                    const char *etype = vhpi_get_str(vhpiStrValP, enum_hdl);
                    if (1 < cnt                                                    ||
                        (0 != strncmp(etype, enums_1[cnt], strlen(enums_1[cnt]))  &&
                         0 != strncmp(etype, enums_2[cnt], strlen(enums_2[cnt])))) {
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
                const char *enums_1[9] = { "U",   "X",   "0",   "1",   "Z",   "W",   "L",   "H",   "-"}; //Aldec does not return the single quotes
                const char *enums_2[9] = {"'U'", "'X'", "'0'", "'1'", "'Z'", "'W'", "'L'", "'H'", "'-'"};
                vhpiHandleT enum_hdl;
                int cnt = 0;

                while ((enum_hdl = vhpi_scan(it)) != NULL) {
                    const char *etype = vhpi_get_str(vhpiStrValP, enum_hdl);
                    if (8 < cnt                                                    ||
                        (0 != strncmp(etype, enums_1[cnt], strlen(enums_1[cnt]))  &&
                         0 != strncmp(etype, enums_2[cnt], strlen(enums_2[cnt])))) {
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

    if (0 == strncmp(type, "CHARACTER", sizeof("STD_ULOGIC")-1)) {
        return true;
    } else {
        return (vhpi_get(vhpiNumLiteralsP, hdl) == NUM_ENUMS_IN_CHAR_TYPE);
    }
}

bool is_enum_boolean(vhpiHandleT hdl) {
    const char *type = vhpi_get_str(vhpiNameP, hdl);

    if (0 == strncmp(type, "BOOLEAN", sizeof("BOOLEAN")-1)) {
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
                    if (((0 == cnt && 0 != strncmp(etype, "FALSE", strlen("FALSE")))  &&
                         (0 == cnt && 0 != strncmp(etype, "false", strlen("false")))) ||
                        ((1 == cnt && 0 != strncmp(etype, "TRUE" , strlen("TRUE")))   &&
                         (1 == cnt && 0 != strncmp(etype, "true" , strlen("true"))))  ||
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

GpiObjHdl *VhpiImpl::create_gpi_obj_from_handle(vhpiHandleT new_hdl,
                                                std::string &name,
                                                std::string &fq_name)
{
    vhpiIntT type;
    gpi_objtype_t gpi_type;
    GpiObjHdl *new_obj = NULL;

    if (vhpiVerilog == (type = vhpi_get(vhpiKindP, new_hdl))) {
        LOG_DEBUG("vhpiVerilog returned from vhpi_get(vhpiType, ...)")
        return NULL;
    }

    /* We need to delve further here to detemine how to later set
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
    vhpiIntT is_static = vhpi_get(vhpiStaticnessP, query_hdl);

    /* Non locally static objects are not accessible for read/write
       so we create this as a GpiObjType
    */
    if (is_static == vhpiGloballyStatic) {
        gpi_type   = GPI_MODULE;
        goto create;
    }

    switch (base_type) {
        case vhpiArrayTypeDeclK: {
            vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, query_hdl);

            if (num_dim > 1) {
                LOG_DEBUG("Detected a MULTI-DIMENSIONAL ARRAY type %s", fq_name.c_str());
                gpi_type   = GPI_ARRAY;
            } else {
                vhpiHandleT elem_base_type_hdl = NULL;
                vhpiIntT elem_base_type        = 0;

                /* vhpiElemSubtype is deprecated.  Should be using vhpiElemType, but not supported in all simulators. */
                vhpiHandleT elem_sub_type_hdl  = vhpi_handle(vhpiElemSubtype, query_hdl);

                if (elem_sub_type_hdl != NULL) {
                    elem_base_type_hdl = vhpi_handle(vhpiBaseType, elem_sub_type_hdl);
                    vhpi_release_handle(elem_sub_type_hdl);
                }

                if (elem_base_type_hdl != NULL) {
                    elem_base_type    = vhpi_get(vhpiKindP, elem_base_type_hdl);
                    if (elem_base_type == vhpiEnumTypeDeclK) {
                        if (is_enum_logic(elem_base_type_hdl)) {
                            LOG_DEBUG("Detected a LOGIC VECTOR type %s", fq_name.c_str());
                            gpi_type   = GPI_REGISTER;
                        } else if (is_enum_char(elem_base_type_hdl)) {
                            LOG_DEBUG("Detected a STRING type %s", fq_name.c_str());
                            gpi_type   = GPI_STRING;
                        } else {
                            LOG_DEBUG("Detected a NON-LOGIC ENUM VECTOR type %s", fq_name.c_str());
                            gpi_type   = GPI_ARRAY;
                        }
                    } else {
                        LOG_DEBUG("Detected a NON-ENUM VECTOR type %s", fq_name.c_str());
                        gpi_type   = GPI_ARRAY;
                    }
                } else {
                    LOG_ERROR("Unable to determine the Array Element Base Type for %s.  Defaulting to GPI_ARRAY.", vhpi_get_str(vhpiFullCaseNameP, new_hdl));
                    gpi_type   = GPI_ARRAY;
                }
            }
            break;
        }

        case vhpiEnumTypeDeclK: {
            if (is_enum_logic(query_hdl)) {
                LOG_DEBUG("Detected a LOGIC type %s", fq_name.c_str());
                gpi_type   = GPI_REGISTER;
            } else if (is_enum_char(query_hdl)) {
                LOG_DEBUG("Detected a CHAR type %s", fq_name.c_str());
                gpi_type   = GPI_INTEGER;
            } else if (is_enum_boolean(query_hdl)) {
                LOG_DEBUG("Detected a BOOLEAN/INTEGER type %s", fq_name.c_str());
                gpi_type   = GPI_INTEGER;
            } else {
                LOG_DEBUG("Detected an ENUM type %s", fq_name.c_str());
                gpi_type   = GPI_ENUM;
            }
            break;
        }

        case vhpiIntTypeDeclK: {
            LOG_DEBUG("Detected an INT type %s", fq_name.c_str());
            gpi_type = GPI_INTEGER;
            break;
        }

        case vhpiFloatTypeDeclK: {
            LOG_DEBUG("Detected a REAL type %s", fq_name.c_str());
            gpi_type = GPI_REAL;
            break;
        }

        case vhpiRecordTypeDeclK: {
            LOG_DEBUG("Detected a STRUCTURE type %s", fq_name.c_str());
            gpi_type   = GPI_STRUCTURE;
            break;
        }

        case vhpiProcessStmtK:
        case vhpiSimpleSigAssignStmtK:
        case vhpiCondSigAssignStmtK:
        case vhpiSelectSigAssignStmtK: {
            gpi_type   = GPI_MODULE;
            break;
        }

        case vhpiRootInstK:
        case vhpiIfGenerateK:
        case vhpiForGenerateK:
        case vhpiCompInstStmtK: {
            std::string hdl_name = vhpi_get_str(vhpiCaseNameP, new_hdl);

            if (base_type == vhpiRootInstK && hdl_name != name) {
                vhpiHandleT arch = vhpi_handle(vhpiDesignUnit, new_hdl);

                if (NULL != arch) {
                    vhpiHandleT prim = vhpi_handle(vhpiPrimaryUnit, arch);

                    if (NULL != prim) {
                        hdl_name = vhpi_get_str(vhpiCaseNameP, prim);
                    }
                }
            }

            if (name != hdl_name) {
                LOG_DEBUG("Found pseudo-region %s", fq_name.c_str());
                gpi_type = GPI_GENARRAY;
            } else {
                gpi_type = GPI_MODULE;
            }
            break;
        }

        default: {
            LOG_ERROR("Not able to map type (%s) %u to object",
                      vhpi_get_str(vhpiKindStrP, query_hdl), type);
            new_obj = NULL;
            goto out;
        }
    }

create:
    LOG_DEBUG("Creating %s of type %d (%s)",
              vhpi_get_str(vhpiFullCaseNameP, new_hdl),
              gpi_type,
              vhpi_get_str(vhpiKindStrP, query_hdl));

    if (gpi_type != GPI_ARRAY && gpi_type != GPI_GENARRAY && gpi_type != GPI_MODULE && gpi_type != GPI_STRUCTURE) {
        if (gpi_type == GPI_REGISTER)
            new_obj = new VhpiLogicSignalObjHdl(this, new_hdl, gpi_type, is_const(new_hdl));
        else
            new_obj = new VhpiSignalObjHdl(this, new_hdl, gpi_type, is_const(new_hdl));
    } else if (gpi_type == GPI_ARRAY) {
        new_obj = new VhpiArrayObjHdl(this, new_hdl, gpi_type);
    } else {
        new_obj = new GpiObjHdl(this, new_hdl, gpi_type);
    }

    if (new_obj->initialise(name, fq_name)) {
        delete new_obj;
        new_obj = NULL;
    }

out:
    if (base_hdl != NULL)
        vhpi_release_handle(base_hdl);

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(void *raw_hdl, GpiObjHdl *parent)
{
    LOG_DEBUG("Trying to convert raw to VHPI handle");

    vhpiHandleT new_hdl = (vhpiHandleT)raw_hdl;

    std::string fq_name = parent->get_fullname();
    const char *c_name = vhpi_get_str(vhpiCaseNameP, new_hdl);
    if (!c_name) {
        LOG_DEBUG("Unable to query name of passed in handle");
        return NULL;
    }

    std::string name = c_name;

    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(std::string &name, GpiObjHdl *parent)
{
    vhpiHandleT vhpi_hdl  = parent->get_handle<vhpiHandleT>();

    vhpiHandleT new_hdl;
    std::string fq_name = parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }
    std::vector<char> writable(fq_name.begin(), fq_name.end());
    writable.push_back('\0');

    new_hdl = vhpi_handle_by_name(&writable[0], NULL);

    if (new_hdl == NULL && parent->get_type() == GPI_STRUCTURE) {
        /* vhpi_handle_by_name() doesn't always work for records, specificaly records in generics */
        vhpiHandleT iter = vhpi_iterator(vhpiSelectedNames, vhpi_hdl);
        if (iter != NULL) {
            while ((new_hdl = vhpi_scan(iter)) != NULL) {
                std::string selected_name = vhpi_get_str(vhpiCaseNameP, new_hdl);
                std::size_t found = selected_name.find_last_of(".");

                if (found != std::string::npos) {
                    selected_name = selected_name.substr(found+1);
                }

                if (selected_name == name) {
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
                    if (rgn_name.compare(0,name.length(),name) == 0) {
                        new_hdl = vhpi_hdl;
                        vhpi_release_handle(iter);
                        break;
                    }
                }
            }
        }
        if (new_hdl == NULL) {
            LOG_DEBUG("Unable to query vhpi_handle_by_name %s", fq_name.c_str());
            return NULL;
        }
    }

    /* Generate Loops have inconsistent behavior across vhpi.  A "name"
     * without an index, i.e. dut.loop vs dut.loop(0), may or may not map to 
     * to the start index.  If it doesn't then it won't find anything.
     *
     * If this unique case is hit, we need to create the Pseudo-region, with the handle
     * being equivalent to the parent handle.
     */
    if (vhpi_get(vhpiKindP, new_hdl) == vhpiForGenerateK) {
        vhpi_release_handle(new_hdl);

        new_hdl = vhpi_hdl;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Unable to fetch object %s", fq_name.c_str());
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::native_check_create(int32_t index, GpiObjHdl *parent)
{
    vhpiHandleT vhpi_hdl  = parent->get_handle<vhpiHandleT>();
    std::string name      = parent->get_name();
    std::string fq_name   = parent->get_fullname();
    vhpiHandleT new_hdl   = NULL;
    char buff[14]; // needs to be large enough to hold -2^31 to 2^31-1 in string form ('(''-'10+'')'\0')

    gpi_objtype_t obj_type = parent->get_type();

    if (obj_type == GPI_GENARRAY) {
        LOG_DEBUG("Native check create for index %d of parent %s (pseudo-region)",
                  index,
                  parent->get_name_str());

        snprintf(buff, sizeof(buff), "%d", index);

        std::string idx_str = buff;
        name    += (GEN_IDX_SEP_LHS + idx_str + GEN_IDX_SEP_RHS);
        fq_name += (GEN_IDX_SEP_LHS + idx_str + GEN_IDX_SEP_RHS);

        std::vector<char> writable(fq_name.begin(), fq_name.end());
        writable.push_back('\0');

        new_hdl = vhpi_handle_by_name(&writable[0], NULL);
    } else if (obj_type == GPI_REGISTER || obj_type == GPI_ARRAY || obj_type == GPI_STRING) {
        LOG_DEBUG("Native check create for index %d of parent %s (%s)",
                  index,
                  parent->get_fullname_str(),
                  vhpi_get_str(vhpiKindStrP, vhpi_hdl));

        snprintf(buff, sizeof(buff), "(%d)", index);

        std::string idx_str = buff;
        name    += idx_str;
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
            LOG_ERROR("Unable to get the vhpiBaseType of %s", parent->get_fullname_str());
            return NULL;
        }

        vhpiIntT    num_dim  = vhpi_get(vhpiNumDimensionsP,base_hdl);
        uint32_t    idx      = 0;

        /* Need to translate the index into a zero-based flattened array index */
        if (num_dim > 1) {
            std::string hdl_name = vhpi_get_str(vhpiCaseNameP, vhpi_hdl);
            std::vector<int> indices;

            /* Need to determine how many indices have been received.  A valid handle will only
             * be found when all indices are received, otherwise need a pseudo-handle.
             *
             * When working with pseudo-handles:
             *              hdl_name:   sig_name
             *    parent->get_name():   sig_name(x)(y)...  where x,y,... are the indices to a multi-dimensional array.
             *            pseudo_idx:   (x)(y)...
             */
            if (hdl_name.length() < parent->get_name().length()) {
                std::string pseudo_idx = parent->get_name().substr(hdl_name.length());

                while (pseudo_idx.length() > 0) {
                    std::size_t found = pseudo_idx.find_first_of(")");

                    if (found != std::string::npos) {
                        indices.push_back(atoi(pseudo_idx.substr(1,found-1).c_str()));
                        pseudo_idx = pseudo_idx.substr(found+1);
                    } else {
                        break;
                    }
                }
            }

            indices.push_back(index);

            if (indices.size() == num_dim) {
#ifdef IUS
                /* IUS does not appear to set the vhpiIsUnconstrainedP property.  IUS Docs say will return
                 * -1 if unconstrained, but with vhpiIntT being unsigned, the value returned is below.
                 */
                const vhpiIntT UNCONSTRAINED = 2147483647;
#endif

                std::vector<vhpiHandleT> constraints;

                /* All necessary indices are available, need to iterate over dimension constraints to
                 * determine the index into the zero-based flattened array.
                 *
                 * Check the constraints on the base type first. (always works for Aldec, but not unconstrained types in IUS)
                 * If the base type fails, then try the sub-type.  (sub-type is listed as deprecated for Aldec)
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

                /* If all the dimensions were not obtained, try again with the sub-type handle */
                if (constraints.size() != num_dim) {
                    vhpiHandleT sub_hdl = vhpi_handle(vhpiSubtype, vhpi_hdl);;

                    constraints.clear();

                    if (sub_hdl != NULL) {
                        it = vhpi_iterator(vhpiConstraints, sub_hdl);

                        if (it != NULL) {
                            while ((constraint = vhpi_scan(it)) != NULL) {
                                /* IUS only sets the vhpiIsUnconstrainedP incorrectly on the base type */
                                if (vhpi_get(vhpiIsUnconstrainedP, constraint)) {
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
                        constraint  = constraints.back();

                        vhpiIntT left  = vhpi_get(vhpiLeftBoundP, constraint);
                        vhpiIntT right = vhpi_get(vhpiRightBoundP, constraint);
                        vhpiIntT len   = 0;

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
                    LOG_ERROR("Unable to access all constraints for %s", parent->get_fullname_str());
                    return NULL;
                }

            } else {
                new_hdl = vhpi_hdl;  // Set to the parent handle to create the pseudo-handle
            }
        } else {
            int left  = parent->get_range_left();
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
                   try an iteration instead, spotty support for multi-dimensional arrays */

                vhpiHandleT iter = vhpi_iterator(vhpiIndexedNames, vhpi_hdl);
                if (iter != NULL) {
                    uint32_t curr_index = 0;
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
                LOG_DEBUG("Index (%d->%d) found %s (%s)", index, idx, vhpi_get_str(vhpiCaseNameP, new_hdl), vhpi_get_str(vhpiKindStrP, new_hdl));
            }
        }
    } else {
        LOG_ERROR("VHPI: Parent of type %s must be of type GPI_GENARRAY, GPI_REGISTER, GPI_ARRAY, or GPI_STRING to have an index.", parent->get_type_str());
        return NULL;
    }


    if (new_hdl == NULL) {
        LOG_DEBUG("Unable to query vhpi_handle_by_index %d", index);
        return NULL;
    }

    GpiObjHdl* new_obj = create_gpi_obj_from_handle(new_hdl, name, fq_name);
    if (new_obj == NULL) {
        vhpi_release_handle(new_hdl);
        LOG_DEBUG("Could not fetch object below entity (%s) at index (%d)",
                  parent->get_name_str(), index);
        return NULL;
    }

    return new_obj;
}

GpiObjHdl *VhpiImpl::get_root_handle(const char* name)
{
    vhpiHandleT root = NULL;
    vhpiHandleT arch = NULL;
    vhpiHandleT dut = NULL;
    std::string root_name;
    const char *found;

    root = vhpi_handle(vhpiRootInst, NULL);
    check_vhpi_error();

    if (!root) {
        LOG_ERROR("VHPI: Attempting to get the vhpiRootInst failed");
        return NULL;
    } else {
        LOG_DEBUG("VHPI: We have found root='%s'", vhpi_get_str(vhpiCaseNameP, root));
    }

    if (name) {
        if (NULL == (dut = vhpi_handle_by_name(name, NULL))) {
            LOG_DEBUG("VHPI: Unable to query by name");
            check_vhpi_error();
        }
    }

    if (!dut) {
        if (NULL == (arch = vhpi_handle(vhpiDesignUnit, root))) {
            LOG_DEBUG("VHPI: Unable to get vhpiDesignUnit via root");
            check_vhpi_error();
            return NULL;
        }

        if (NULL == (dut = vhpi_handle(vhpiPrimaryUnit, arch))) {
            LOG_DEBUG("VHPI: Unable to get vhpiPrimaryUnit via arch");
            check_vhpi_error();
            return NULL;
        }

        /* if this matches the name then it is what we want, but we
           use the handle two levels up as the dut as do not want an
           object of type vhpiEntityDeclK as the dut */

        found = vhpi_get_str(vhpiCaseNameP, dut);
        dut = root;

    } else {
        found = vhpi_get_str(vhpiCaseNameP, dut);
    }

    if (!dut) {
        LOG_ERROR("VHPI: Attempting to get the DUT handle failed");
        return NULL;
    }

    if (!found) {
        LOG_ERROR("VHPI: Unable to query name for DUT handle");
        return NULL;
    }

    if (name != NULL && strcmp(name, found)) {
        LOG_WARN("VHPI: DUT '%s' doesn't match requested toplevel %s", found, name);
        return NULL;
    }

    root_name = found;

    return create_gpi_obj_from_handle(dut, root_name, root_name);

}

GpiIterator *VhpiImpl::iterate_handle(GpiObjHdl *obj_hdl, gpi_iterator_sel_t type)
{
    GpiIterator *new_iter = NULL;

    switch (type) {
        case GPI_OBJECTS:
            new_iter = new VhpiIterator(this, obj_hdl);
            break;
        default:
            LOG_WARN("Other iterator types not implemented yet");
            break;
    }
    return new_iter;
}

GpiCbHdl *VhpiImpl::register_timed_callback(uint64_t time_ps)
{
    VhpiTimedCbHdl *hdl = new VhpiTimedCbHdl(this, time_ps);

    if (hdl->arm_callback()) {
        delete(hdl);
        hdl = NULL;
    }

    return hdl;
}

GpiCbHdl *VhpiImpl::register_readwrite_callback(void)
{
    if (m_read_write.arm_callback())
        return NULL;

    return &m_read_write;
}

GpiCbHdl *VhpiImpl::register_readonly_callback(void)
{
    if (m_read_only.arm_callback())
        return NULL;

    return &m_read_only;
}

GpiCbHdl *VhpiImpl::register_nexttime_callback(void)
{
    if (m_next_phase.arm_callback())
        return NULL;

    return &m_next_phase;
}

int VhpiImpl::deregister_callback(GpiCbHdl *gpi_hdl)
{
    gpi_hdl->cleanup_callback();
    return 0;
}

void VhpiImpl::sim_end(void)
{
    sim_finish_cb->set_call_state(GPI_DELETE);
    vhpi_control(vhpiFinish);
    check_vhpi_error();
}

extern "C" {

// Main entry point for callbacks from simulator
void handle_vhpi_callback(const vhpiCbDataT *cb_data)
{
    VhpiCbHdl *cb_hdl = (VhpiCbHdl*)cb_data->user_data;

    if (!cb_hdl)
        LOG_CRITICAL("VHPI: Callback data corrupted");

    gpi_cb_state_e old_state = cb_hdl->get_call_state();

    if (old_state == GPI_PRIMED) {

        cb_hdl->set_call_state(GPI_CALL);
        cb_hdl->run_callback();

        gpi_cb_state_e new_state = cb_hdl->get_call_state();

        /* We have re-primed in the handler */
        if (new_state != GPI_PRIMED)
            if (cb_hdl->cleanup_callback()) {
                delete cb_hdl;
            }

    }

    return;
};

static void register_initial_callback(void)
{
    FENTER
    sim_init_cb = new VhpiStartupCbHdl(vhpi_table);
    sim_init_cb->arm_callback();
    FEXIT
}

static void register_final_callback(void)
{
    FENTER
    sim_finish_cb = new VhpiShutdownCbHdl(vhpi_table);
    sim_finish_cb->arm_callback();
    FEXIT
}

static void register_embed(void)
{
    vhpi_table = new VhpiImpl("VHPI");
    gpi_register_impl(vhpi_table);
    gpi_load_extra_libs();
}

// pre-defined VHPI registration table
void (*vhpi_startup_routines[])(void) = {
    register_embed,
    register_initial_callback,
    register_final_callback,
    0
};

// For non-VPI compliant applications that cannot find vlog_startup_routines
void vhpi_startup_routines_bootstrap(void) {
    void (*routine)(void);
    int i;
    routine = vhpi_startup_routines[0];
    for (i = 0, routine = vhpi_startup_routines[i];
         routine;
         routine = vhpi_startup_routines[++i]) {
        routine();
    }
}

}

GPI_ENTRY_POINT(vhpi, register_embed)
