// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "./VhpiImpl.hpp"
#include "_vendor/vhpi/vhpi_user.h"

VhpiArrayObjHdl::~VhpiArrayObjHdl() {
    LOG_DEBUG("VHPI: Releasing VhpiArrayObjHdl handle for %s at %p",
              get_fullname_str(), (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

VhpiObjHdl::~VhpiObjHdl() {
    /* Don't release handles for pseudo-regions, as they borrow the handle of
     * the containing region */
    if (m_type != GPI_GENARRAY) {
        LOG_DEBUG("VHPI: Releasing VhpiObjHdl handle for %s at %p",
                  get_fullname_str(), (void *)get_handle<vhpiHandleT>());
        if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
    }
}

bool get_range(vhpiHandleT hdl, vhpiIntT dim, int *left, int *right,
               gpi_range_dir *dir) {
#ifdef IUS
    /* IUS/Xcelium does not appear to set the vhpiIsUnconstrainedP property. IUS
     * Docs say will return -1 if unconstrained, but with vhpiIntT being
     * unsigned, the value returned is below.
     */
    const vhpiIntT UNCONSTRAINED = 2147483647;
#endif

    bool error = true;

    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, hdl);

    if (base_hdl == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, hdl);

        if (st_hdl != NULL) {
            base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    if (base_hdl != NULL) {
        vhpiHandleT it = vhpi_iterator(vhpiConstraints, base_hdl);
        vhpiIntT curr_idx = 0;

        if (it != NULL) {
            vhpiHandleT constraint;
            while ((constraint = vhpi_scan(it)) != NULL) {
                if (curr_idx == dim) {
                    vhpi_release_handle(it);
                    vhpiIntT l_rng = vhpi_get(vhpiLeftBoundP, constraint);
                    vhpiIntT r_rng = vhpi_get(vhpiRightBoundP, constraint);
#ifdef IUS
                    if (l_rng != UNCONSTRAINED && r_rng != UNCONSTRAINED) {
#else
                    if (!vhpi_get(vhpiIsUnconstrainedP, constraint)) {
#endif
                        error = false;
                        *left = static_cast<int>(l_rng);
                        *right = static_cast<int>(r_rng);
#ifdef MODELSIM
                        /* Issue #4236: Questa's VHPI sets vhpiIsUpP incorrectly
                         * so we must rely on the values of `left` and `right`
                         * to infer direction.
                         */
                        if (*left < *right) {
#else
                        if (vhpi_get(vhpiIsUpP, constraint) == 1) {
#endif
                            *dir = GPI_RANGE_UP;
                        } else {
                            *dir = GPI_RANGE_DOWN;
                        }
                    }
                    break;
                }
                ++curr_idx;
            }
        }
        vhpi_release_handle(base_hdl);
    }

    if (error) {
        vhpiHandleT sub_type_hdl = vhpi_handle(vhpiSubtype, hdl);

        if (sub_type_hdl != NULL) {
            vhpiHandleT it = vhpi_iterator(vhpiConstraints, sub_type_hdl);
            vhpiIntT curr_idx = 0;

            if (it != NULL) {
                vhpiHandleT constraint;
                while ((constraint = vhpi_scan(it)) != NULL) {
                    if (curr_idx == dim) {
                        vhpi_release_handle(it);

                        /* IUS/Xcelium only sets the vhpiIsUnconstrainedP
                         * incorrectly on the base type */
                        if (!vhpi_get(vhpiIsUnconstrainedP, constraint)) {
                            error = false;
                            *left = static_cast<int>(
                                vhpi_get(vhpiLeftBoundP, constraint));
                            *right = static_cast<int>(
                                vhpi_get(vhpiRightBoundP, constraint));
#ifdef MODELSIM
                            /* Issue #4236: See above */
                            if (*left < *right) {
#else
                            if (vhpi_get(vhpiIsUpP, constraint) == 1) {
#endif
                                *dir = GPI_RANGE_UP;
                            } else {
                                *dir = GPI_RANGE_DOWN;
                            }
                        }
                        break;
                    }
                    ++curr_idx;
                }
            }
            vhpi_release_handle(sub_type_hdl);
        }
    }

    return error;
}

int VhpiArrayObjHdl::initialise(const std::string &name,
                                const std::string &fq_name) {
    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();

    m_indexable = true;

    vhpiHandleT type = vhpi_handle(vhpiBaseType, handle);

    if (type == NULL) {
        vhpiHandleT st_hdl = vhpi_handle(vhpiSubtype, handle);

        if (st_hdl != NULL) {
            type = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    if (NULL == type) {
        LOG_ERROR("VHPI: Unable to get vhpiBaseType for %s", fq_name.c_str());
        return -1;
    }

    vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, type);
    vhpiIntT dim_idx = 0;

    /* Need to determine which dimension constraint is needed */
    if (num_dim > 1) {
        std::string hdl_name = vhpi_get_str(vhpiCaseNameP, handle);

        if (hdl_name.length() < name.length()) {
            std::string pseudo_idx = name.substr(hdl_name.length());

            while (pseudo_idx.length() > 0) {
                std::size_t found = pseudo_idx.find_first_of(")");

                if (found != std::string::npos) {
                    ++dim_idx;
                    pseudo_idx = pseudo_idx.substr(found + 1);
                } else {
                    break;
                }
            }
        }
    }

    bool error =
        get_range(handle, dim_idx, &m_range_left, &m_range_right, &m_range_dir);

    if (error) {
        LOG_ERROR(
            "VHPI: Unable to obtain constraints for an indexable object %s.",
            fq_name.c_str());
        return -1;
    }

    if (m_range_dir == GPI_RANGE_DOWN) {
        m_num_elems = m_range_left - m_range_right + 1;
    } else {
        m_num_elems = m_range_right - m_range_left + 1;
    }
    if (m_num_elems < 0) {
        m_num_elems = 0;
    }

    return GpiObjHdl::initialise(name, fq_name);
}

int VhpiObjHdl::initialise(const std::string &name,
                           const std::string &fq_name) {
    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();
    if (handle != NULL && m_type != GPI_STRUCTURE) {
        vhpiHandleT du_handle = vhpi_handle(vhpiDesignUnit, handle);
        if (du_handle != NULL) {
            vhpiHandleT pu_handle = vhpi_handle(vhpiPrimaryUnit, du_handle);
            if (pu_handle != NULL) {
                const char *str;
                str = vhpi_get_str(vhpiNameP, pu_handle);
                if (str != NULL) m_definition_name = str;

                str = vhpi_get_str(vhpiFileNameP, pu_handle);
                if (str != NULL) m_definition_file = str;
            }
        }
    }

    return GpiObjHdl::initialise(name, fq_name);
}
