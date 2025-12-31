// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cinttypes>  // fixed-size int types and format strings
#include <stdexcept>

#include "../logging.hpp"
#include "./VhpiImpl.hpp"
#include "_vendor/vhpi/vhpi_user.h"

decltype(VhpiIterator::iterate_over) VhpiIterator::iterate_over = [] {
    /* for reused lists */
    std::initializer_list<vhpiOneToManyT> root_options = {
        vhpiInternalRegions,
        vhpiSigDecls,
        vhpiVarDecls,
        vhpiPortDecls,
        vhpiGenericDecls,
        vhpiConstDecls,
        //    vhpiIndexedNames,
        vhpiCompInstStmts,
        vhpiBlockStmts,
    };
    std::initializer_list<vhpiOneToManyT> sig_options = {
        vhpiIndexedNames,
        vhpiSelectedNames,
    };
    std::initializer_list<vhpiOneToManyT> simplesig_options = {
        vhpiDecls,
        vhpiInternalRegions,
        vhpiSensitivitys,
        vhpiStmts,
    };
    std::initializer_list<vhpiOneToManyT> gen_options = {
        vhpiDecls,      vhpiInternalRegions, vhpiSigDecls,   vhpiVarDecls,
        vhpiConstDecls, vhpiCompInstStmts,   vhpiBlockStmts,
    };

    return decltype(VhpiIterator::iterate_over){
        {vhpiRootInstK, root_options},
        {vhpiCompInstStmtK, root_options},

        {vhpiGenericDeclK, sig_options},
        {vhpiSigDeclK, sig_options},
        {vhpiSelectedNameK, sig_options},
        {vhpiIndexedNameK, sig_options},
        {vhpiPortDeclK, sig_options},

        {vhpiCondSigAssignStmtK, simplesig_options},
        {vhpiSimpleSigAssignStmtK, simplesig_options},
        {vhpiSelectSigAssignStmtK, simplesig_options},

        {vhpiForGenerateK, gen_options},
        {vhpiIfGenerateK, gen_options},
        {vhpiBlockStmtK, gen_options},

        {vhpiConstDeclK,
         {
             vhpiAttrSpecs,
             vhpiIndexedNames,
             vhpiSelectedNames,
         }},
    };
}();

VhpiIterator::VhpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
    : GpiIterator(impl, hdl), m_iterator(NULL), m_iter_obj(NULL) {
    vhpiHandleT iterator;
    vhpiHandleT vhpi_hdl = m_parent->get_handle<vhpiHandleT>();

    vhpiClassKindT type = (vhpiClassKindT)vhpi_get(vhpiKindP, vhpi_hdl);
    try {
        selected = &iterate_over.at(type);
    } catch (std::out_of_range const &) {
        LOG_WARN(
            "VHPI: Implementation does not know how to iterate over %s(%d)",
            vhpi_get_str(vhpiKindStrP, vhpi_hdl), type);
        selected = nullptr;
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin(); one2many != selected->end();
         one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY &&
            *one2many != vhpiInternalRegions) {
            LOG_DEBUG(
                "VHPI: vhpi_iterator vhpiOneToManyT=%d skipped for "
                "GPI_GENARRAY type",
                *one2many);
            continue;
        }

        iterator = vhpi_iterator(*one2many, vhpi_hdl);

        if (iterator) break;

        LOG_DEBUG("VHPI: vhpi_iterate vhpiOneToManyT=%d returned NULL",
                  *one2many);
    }

    if (NULL == iterator) {
        LOG_DEBUG(
            "VHPI: vhpi_iterate return NULL for all relationships on %s (%d) "
            "kind:%s",
            vhpi_get_str(vhpiCaseNameP, vhpi_hdl), type,
            vhpi_get_str(vhpiKindStrP, vhpi_hdl));
        selected = NULL;
        return;
    }

    LOG_DEBUG("VHPI: Created iterator working from scope %d (%s)",
              vhpi_get(vhpiKindP, vhpi_hdl),
              vhpi_get_str(vhpiKindStrP, vhpi_hdl));

    /* On some simulators (Aldec) vhpiRootInstK is a null level of hierarchy.
     * We check that something is going to come back, if not, we try the level
     * down.
     */
    m_iter_obj = vhpi_hdl;
    m_iterator = iterator;
}

VhpiIterator::~VhpiIterator() {
    if (m_iterator) vhpi_release_handle(m_iterator);
}

#define VHPI_TYPE_MIN (1000)

GpiIterator::Status VhpiIterator::next_handle(std::string &name,
                                              GpiObjHdl **hdl, void **raw_hdl) {
    vhpiHandleT obj;
    GpiObjHdl *new_obj;

    if (!selected) return GpiIterator::END;

    gpi_objtype obj_type = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try the next one until a new object is found.
     */
    do {
        obj = NULL;

        if (m_iterator) {
            obj = vhpi_scan(m_iterator);

            /* For GPI_GENARRAY, only allow the generate statements through that
             * match the name of the generate block.
             */
            if (obj != NULL && obj_type == GPI_GENARRAY) {
                if (vhpi_get(vhpiKindP, obj) == vhpiForGenerateK) {
                    std::string rgn_name = vhpi_get_str(vhpiCaseNameP, obj);
                    if (!VhpiImpl::compare_generate_labels(rgn_name,
                                                           parent_name)) {
                        obj = NULL;
                        continue;
                    }
                } else {
                    obj = NULL;
                    continue;
                }
            }

            if (obj != NULL &&
                (vhpiProcessStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiCondSigAssignStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiSimpleSigAssignStmtK == vhpi_get(vhpiKindP, obj) ||
                 vhpiSelectSigAssignStmtK == vhpi_get(vhpiKindP, obj))) {
                LOG_DEBUG("VHPI: Skipping %s (%s)",
                          vhpi_get_str(vhpiFullNameP, obj),
                          vhpi_get_str(vhpiKindStrP, obj));
                obj = NULL;
                continue;
            }

            if (obj != NULL) {
                LOG_DEBUG("VHPI: Found an item %s",
                          vhpi_get_str(vhpiFullNameP, obj));
                break;
            } else {
                LOG_DEBUG("VHPI: vhpi_scan on vhpiOneToManyT=%d returned NULL",
                          *one2many);
            }

            LOG_DEBUG("VHPI: End of vhpiOneToManyT=%d iteration", *one2many);
            m_iterator = NULL;
        } else {
            LOG_DEBUG("VHPI: No valid vhpiOneToManyT=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != vhpiInternalRegions) {
            LOG_DEBUG(
                "VHPI: vhpi_iterator vhpiOneToManyT=%d skipped for "
                "GPI_GENARRAY type",
                *one2many);
            continue;
        }

        m_iterator = vhpi_iterator(*one2many, m_iter_obj);

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("VHPI: No more children, all relationships have been tested");
        return GpiIterator::END;
    }

    const char *c_name = vhpi_get_str(vhpiCaseNameP, obj);
    if (!c_name) {
        vhpiIntT type = vhpi_get(vhpiKindP, obj);

        if (type < VHPI_TYPE_MIN) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG(
            "VHPI: Unable to get the name for this object of type " PRIu32,
            type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and
     * create the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region
     * object. Otherwise a list would be required and checked while iterating
     */
    if (*one2many == vhpiInternalRegions && obj_type != GPI_GENARRAY &&
        vhpi_get(vhpiKindP, obj) == vhpiForGenerateK) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.rfind(GEN_IDX_SEP_LHS);

        if (found != std::string::npos && found != 0) {
            name = idx_str.substr(0, found);
            obj = m_parent->get_handle<vhpiHandleT>();
        } else {
            LOG_WARN("VHPI: Unhandled Generate Loop Format - %s", name.c_str());
            name = c_name;
        }
    } else {
        name = c_name;
    }

    LOG_DEBUG("VHPI: vhpi_scan found %s (%d) kind:%s name:%s", name.c_str(),
              vhpi_get(vhpiKindP, obj), vhpi_get_str(vhpiKindStrP, obj),
              vhpi_get_str(vhpiCaseNameP, obj));

    /* We try and create a handle internally, if this is not possible we
       return and GPI will try other implementations with the name
       */
    std::string fq_name = m_parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else if (obj_type == GPI_GENARRAY) {
        std::size_t found = name.rfind(GEN_IDX_SEP_LHS);

        if (found != std::string::npos) {
            fq_name += name.substr(found);
        } else {
            LOG_WARN("VHPI: Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else if (obj_type == GPI_STRUCTURE) {
        std::size_t found = name.rfind(".");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
            name = name.substr(found + 1);
        } else {
            LOG_WARN("VHPI: Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else {
        fq_name += "." + name;
    }
    VhpiImpl *vhpi_impl = reinterpret_cast<VhpiImpl *>(m_impl);
    new_obj = vhpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}
