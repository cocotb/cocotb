// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "../logging.hpp"
#include "./VhpiImpl.hpp"
#include "_vendor/vhpi/vhpi_user.h"

VhpiArrayObjHdl::~VhpiArrayObjHdl() {
    /* Pseudo-handles into multi-dimensional arrays borrow the handle of the
     * real array object and must not release it. */
    if (!m_owns_handle) return;
    LOG_DEBUG("VHPI: Releasing VhpiArrayObjHdl handle for %s at %p",
              get_fullname_str(), (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

VhpiObjHdl::~VhpiObjHdl() {
    /* Pseudo-regions borrow the handle of the containing region and must not
     * release it. */
    if (!m_owns_handle) return;
    LOG_DEBUG("VHPI: Releasing VhpiObjHdl handle for %s at %p",
              get_fullname_str(), (void *)get_handle<vhpiHandleT>());
    if (vhpi_release_handle(get_handle<vhpiHandleT>())) check_vhpi_error();
}

/* Get a handle to the subtype of an object (vhpiType), or NULL. */
static vhpiHandleT get_type_handle(vhpiHandleT hdl) {
#ifdef IUS
    /* Xcelium does not implement the vhpiType relation, only the deprecated
     * vhpiSubtype relation. */
    return vhpi_handle(vhpiSubtype, hdl);
#else
    return vhpi_handle(vhpiType, hdl);
#endif
}

vhpiHandleT get_constrained_type_handle(vhpiHandleT hdl) {
#if defined(IUS)
    /* For an object of a named constrained array type, the subtype Xcelium
     * returns has no constraints, but the base type is the named (constrained)
     * type. Xcelium provides the base type of indexed and selected names only
     * through their subtype, see get_base_type_handle(). */
    vhpiHandleT st_hdl = get_type_handle(hdl);
    if (st_hdl != NULL) {
        vhpiHandleT it = vhpi_iterator(vhpiConstraints, st_hdl);
        if (it != NULL) {
            vhpi_release_handle(it);
            return st_hdl;
        }
        vhpi_release_handle(st_hdl);
    }
    return get_base_type_handle(hdl);
#elif defined(ALDEC)
    /* Riviera-PRO does not implement the vhpiType relation for many objects,
     * e.g. ports, indexed names, and selected names, but returns the
     * (constrained) subtype of an object as its base type. */
    return vhpi_handle(vhpiBaseType, hdl);
#else
    return get_type_handle(hdl);
#endif
}

bool is_unconstrained(vhpiHandleT constraint) {
#ifdef IUS
    /* Xcelium sets the vhpiIsUnconstrainedP property of the constraints of
     * named constrained array types. Its documentation says that the bounds
     * are -1 if the range is unconstrained, which is the value below as
     * vhpiIntT is unsigned. */
    const vhpiIntT UNCONSTRAINED = 2147483647;
    return vhpi_get(vhpiLeftBoundP, constraint) == UNCONSTRAINED ||
           vhpi_get(vhpiRightBoundP, constraint) == UNCONSTRAINED;
#else
    return vhpi_get(vhpiIsUnconstrainedP, constraint);
#endif
}

vhpiHandleT get_base_type_handle(vhpiHandleT hdl) {
    vhpiHandleT base_hdl = vhpi_handle(vhpiBaseType, hdl);

    if (base_hdl == NULL) {
        vhpiHandleT st_hdl = get_type_handle(hdl);

        if (st_hdl != NULL) {
            base_hdl = vhpi_handle(vhpiBaseType, st_hdl);
            vhpi_release_handle(st_hdl);
        }
    }

    return base_hdl;
}

vhpiHandleT get_elem_type_handle(vhpiHandleT array_type) {
#ifdef IUS
    /* Xcelium does not implement the vhpiElemType relation, only the
     * deprecated vhpiElemSubtype relation. */
    return vhpi_handle(vhpiElemSubtype, array_type);
#else
    return vhpi_handle(vhpiElemType, array_type);
#endif
}

bool get_range(vhpiHandleT hdl, vhpiIntT dim, int *left, int *right,
               gpi_range_dir *dir) {
    /* The index ranges of an array object are the index constraints of its
     * subtype. Its base type is an unconstrained array type (IEEE 1076-2019
     * 5.3.2.1), whose index constraints are the index subtypes. */
    vhpiHandleT type_hdl = get_constrained_type_handle(hdl);
    if (type_hdl == NULL) {
        return true;
    }
    DEFER(vhpi_release_handle(type_hdl));

    vhpiHandleT it = vhpi_iterator(vhpiConstraints, type_hdl);
    if (it == NULL) {
        return true;
    }

    vhpiIntT curr_idx = 0;
    vhpiHandleT constraint;
    while ((constraint = vhpi_scan(it)) != NULL) {
        if (curr_idx++ != dim) {
            vhpi_release_handle(constraint);
            continue;
        }
        vhpi_release_handle(it);
        DEFER(vhpi_release_handle(constraint));

        if (is_unconstrained(constraint)) {
            return true;
        }

        *left = static_cast<int>(vhpi_get(vhpiLeftBoundP, constraint));
        *right = static_cast<int>(vhpi_get(vhpiRightBoundP, constraint));
#ifdef MODELSIM
        /* Issue #4236: Questa's VHPI sets vhpiIsUpP incorrectly so we must
         * rely on the values of `left` and `right` to infer direction.
         */
        if (*left < *right) {
#else
        if (vhpi_get(vhpiIsUpP, constraint) == 1) {
#endif
            *dir = GPI_RANGE_UP;
        } else {
            *dir = GPI_RANGE_DOWN;
        }
        return false;
    }

    /* vhpi_scan() has released the exhausted iterator. */
    return true;
}

int VhpiArrayObjHdl::initialise(const std::string &name,
                                const std::string &fq_name) {
    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();

    m_indexable = true;

    vhpiHandleT type = get_base_type_handle(handle);

    if (NULL == type) {
        LOG_ERROR("VHPI: Unable to get vhpiBaseType for %s", fq_name.c_str());
        return -1;
    }

    vhpiIntT num_dim = vhpi_get(vhpiNumDimensionsP, type);
    vhpi_release_handle(type);
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
                vhpi_release_handle(pu_handle);
            }
            vhpi_release_handle(du_handle);
        }
    }

    return GpiObjHdl::initialise(name, fq_name);
}
