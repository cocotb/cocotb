// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <stdexcept>

#include "VpiImpl.h"
#include "vpi_user_ext.h"

decltype(VpiIterator::iterate_over) VpiIterator::iterate_over = [] {
    /* for reused lists */
    // clang-format off
    // vpiInstance is the base class for module, program, interface, etc.
    std::vector<int32_t> instance_options = {
        vpiNet,
        vpiNetArray,
        vpiReg,
        vpiRegArray,
    };
    std::vector<int32_t> module_options = {
        // vpiModule,            // Aldec SEGV on mixed language
        // vpiModuleArray,       // Aldec SEGV on mixed language
        vpiMemory,
        vpiIntegerVar,
        vpiRealVar,
        vpiRealNet,
        vpiStructVar,
        vpiStructNet,
        vpiVariables,
        vpiNamedEvent,
        vpiNamedEventArray,
        vpiParameter,
        vpiPrimitive,
        vpiPrimitiveArray,
        vpiInternalScope,
        // vpiInterface,         // Aldec SEGV on mixed language
        // vpiInterfaceArray,    // Aldec SEGV on mixed language
    };
    // clang-format on

    // append base class vpiInstance members
    module_options.insert(module_options.begin(), instance_options.begin(),
                          instance_options.end());

    std::vector<int32_t> struct_options = {
        vpiNet,
#ifndef IUS
        vpiNetArray,
#endif
        vpiReg,       vpiRegArray,       vpiMemory, vpiParameter,
        vpiPrimitive, vpiPrimitiveArray, vpiMember,
    };

    return decltype(VpiIterator::iterate_over){
        {vpiModule, module_options},
        {vpiInterface, instance_options},
        {vpiGenScope, module_options},

        {vpiStructVar, struct_options},
        {vpiStructNet, struct_options},

        {vpiNet,
         {
             vpiNetBit,
         }},
        {vpiNetArray,
         {
             vpiNet,
         }},
        {vpiRegArray,
         {
             vpiReg,
         }},
        {vpiMemory,
         {
             vpiMemoryWord,
         }},
        {vpiPackage,
         {
             vpiParameter,
         }},
    };
}();

VpiIterator::VpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
    : GpiIterator(impl, hdl), m_iterator(NULL) {
    vpiHandle iterator;
    vpiHandle vpi_hdl = m_parent->get_handle<vpiHandle>();

    int type = vpi_get(vpiType, vpi_hdl);

    try {
        selected = &iterate_over.at(type);
    } catch (std::out_of_range const &) {
        LOG_WARN("VPI: Implementation does not know how to iterate over %s(%d)",
                 vpi_get_str(vpiType, vpi_hdl), type);
        selected = nullptr;
        return;
    }

    for (one2many = selected->begin(); one2many != selected->end();
         one2many++) {
        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (m_parent->get_type() == GPI_GENARRAY &&
            *one2many != vpiInternalScope) {
            LOG_DEBUG(
                "vpi_iterator vpiOneToManyT=%d skipped for GPI_GENARRAY type",
                *one2many);
            continue;
        }

        iterator = vpi_iterate(*one2many, vpi_hdl);

        if (iterator) {
            break;
        }

        LOG_DEBUG("vpi_iterate type=%d returned NULL", *one2many);
    }

    if (NULL == iterator) {
        LOG_DEBUG(
            "vpi_iterate return NULL for all relationships on %s (%d) type:%s",
            vpi_get_str(vpiName, vpi_hdl), type, vpi_get_str(vpiType, vpi_hdl));
        selected = NULL;
        return;
    }

    LOG_DEBUG("Created iterator working from '%s' with type %s(%d)",
              vpi_get_str(vpiFullName, vpi_hdl), vpi_get_str(vpiType, vpi_hdl),
              type);

    m_iterator = iterator;
}

VpiIterator::~VpiIterator() {
    if (m_iterator) vpi_free_object(m_iterator);
}

#define VPI_TYPE_MAX (1000)

GpiIterator::Status VpiSingleIterator::next_handle(std::string &name,
                                                   GpiObjHdl **hdl,
                                                   void **raw_hdl) {
    GpiObjHdl *new_obj;
    vpiHandle obj;

    if (NULL == m_iterator) return GpiIterator::END;

    obj = vpi_scan(m_iterator);
    if (NULL == obj) return GpiIterator::END;

    const char *c_name = vpi_get_str(vpiName, obj);
    if (!c_name) {
        int type = vpi_get(vpiType, obj);

        if (type >= VPI_TYPE_MAX) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG("Unable to get the name for this object of type %d", type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    std::string fq_name = c_name;

    LOG_DEBUG("vpi_scan found '%s = '%s'", name.c_str(), fq_name.c_str());

    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl *>(m_impl);
    new_obj = vpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}

GpiIterator::Status VpiPackageIterator::next_handle(std::string &,
                                                    GpiObjHdl **hdl, void **) {
    GpiObjHdl *new_obj;
    vpiHandle obj;

    if (NULL == m_iterator) return GpiIterator::END;

    // obj might not be a package since we are forced to iterate over all
    // vpiInstance due to a limitation in Questa so we keep searching until we
    // find one
    // Check that an object has a non-NULL name during iteration, and pass over
    // it if it does. This happens with xcelium.
    std::string name;
    while (true) {
        obj = vpi_scan(m_iterator);
        check_vpi_error();
        if (obj == nullptr) return GpiIterator::END;

        PLI_INT32 type = vpi_get(vpiType, obj);
        check_vpi_error();
        if (type == vpiPackage) {
            auto name_cstr = vpi_get_str(vpiName, obj);
            check_vpi_error();
            if (name_cstr != nullptr) {
                name = name_cstr;
                break;
            }
        }
    }

    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl *>(m_impl);
    std::string fq_name = vpi_get_str(vpiFullName, obj);
    LOG_DEBUG("VPI: package found '%s' = '%s'", name.c_str(), fq_name.c_str());
    // '::' may or may not be included in the package vpiFullName:
    std::string package_delim = "::";
    if (fq_name.compare(fq_name.length() - package_delim.length(),
                        package_delim.length(), package_delim)) {
        fq_name += "::";
    }
    new_obj = new VpiObjHdl(vpi_impl, obj, GPI_PACKAGE);
    new_obj->initialise(name, fq_name);
    *hdl = new_obj;
    return GpiIterator::NATIVE;
}

GpiIterator::Status VpiIterator::next_handle(std::string &name, GpiObjHdl **hdl,
                                             void **raw_hdl) {
    GpiObjHdl *new_obj;
    vpiHandle obj;
    vpiHandle iter_obj = m_parent->get_handle<vpiHandle>();

    if (!selected) return GpiIterator::END;

    gpi_objtype obj_type = m_parent->get_type();
    std::string parent_name = m_parent->get_name();

    do {
        obj = NULL;

        if (m_iterator) {
            obj = vpi_scan(m_iterator);

            /* For GPI_GENARRAY, only allow the generate statements through that
             * match the name of the generate block.
             */
            if (obj != NULL && obj_type == GPI_GENARRAY) {
                auto rgn_type = vpi_get(vpiType, obj);
                if (rgn_type == vpiGenScope || rgn_type == vpiModule) {
                    std::string rgn_name = vpi_get_str(vpiName, obj);
                    if (!VpiImpl::compare_generate_labels(rgn_name,
                                                          parent_name)) {
                        obj = NULL;
                        continue;
                    }
                } else {
                    obj = NULL;
                    continue;
                }
            }

            if (NULL == obj) {
                /* m_iterator will already be free'd internally here */
                m_iterator = NULL;
            } else {
                break;
            }

            LOG_DEBUG("End of type=%d iteration", *one2many);
        } else {
            LOG_DEBUG("No valid type=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }

        /* GPI_GENARRAY are pseudo-regions and all that should be searched for
         * are the sub-regions */
        if (obj_type == GPI_GENARRAY && *one2many != vpiInternalScope) {
            LOG_DEBUG(
                "vpi_iterator vpiOneToManyT=%d skipped for GPI_GENARRAY type",
                *one2many);
            continue;
        }

        m_iterator = vpi_iterate(*one2many, iter_obj);

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("No more children, all relationships tested");
        return GpiIterator::END;
    }

    /* Simulators vary here. Some will allow the name to be accessed
       across boundary. We can simply return this up and allow
       the object to be created. Others do not. In this case
       we see if the object is in our type range and if not
       return the raw_hdl up */

    const char *c_name = vpi_get_str(vpiName, obj);
    if (!c_name) {
        /* This may be another type */
        int type = vpi_get(vpiType, obj);

        if (type >= VPI_TYPE_MAX) {
            *raw_hdl = (void *)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG("Unable to get the name for this object of type %d", type);

        return GpiIterator::NATIVE_NO_NAME;
    }

    /*
     * If the parent is not a generate loop, then watch for generate handles and
     * create the pseudo-region.
     *
     * NOTE: Taking advantage of the "caching" to only create one pseudo-region
     * object. Otherwise a list would be required and checked while iterating
     */
    if (*one2many == vpiInternalScope && obj_type != GPI_GENARRAY &&
        vpi_get(vpiType, obj) == vpiGenScope) {
        std::string idx_str = c_name;
        std::size_t found = idx_str.rfind("[");

        if (found != std::string::npos && found != 0) {
            name = idx_str.substr(0, found);
            obj = m_parent->get_handle<vpiHandle>();
        } else {
            name = c_name;
        }
    } else {
        name = c_name;
    }

    /* We try and create a handle internally, if this is not possible we
       return and GPI will try other implementations with the name
       */

    std::string fq_name = m_parent->get_fullname();
    VpiImpl *vpi_impl = reinterpret_cast<VpiImpl *>(m_impl);

    if (obj_type == GPI_GENARRAY) {
        std::size_t found = name.rfind("[");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else if (obj_type == GPI_STRUCTURE) {
        std::size_t found = name.rfind(".");

        if (found != std::string::npos) {
            fq_name += name.substr(found);
            name = name.substr(found + 1);
        } else {
            LOG_WARN("Unhandled Sub-Element Format - %s", name.c_str());
            fq_name += "." + name;
        }
    } else {
        fq_name += vpi_impl->get_type_delimiter(m_parent) + name;
    }

    LOG_DEBUG("vpi_scan found '%s'", fq_name.c_str());
    new_obj = vpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    } else
        return GpiIterator::NOT_NATIVE;
}
