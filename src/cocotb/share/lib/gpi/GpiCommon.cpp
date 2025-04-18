// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <cocotb_utils.h>
#include <sys/types.h>

#include <algorithm>
#include <map>
#include <string>
#include <vector>

#include "gpi.h"
#include "gpi_priv.h"

using namespace std;

static vector<GpiImplInterface *> registered_impls;

#ifdef SINGLETON_HANDLES

class GpiHandleStore {
  public:
    GpiObjHdl *check_and_store(GpiObjHdl *hdl) {
        std::map<std::string, GpiObjHdl *>::iterator it;

        const std::string &name = hdl->get_fullname();

        LOG_DEBUG("Checking %s exists", name.c_str());

        it = handle_map.find(name);
        if (it == handle_map.end()) {
            handle_map[name] = hdl;
            return hdl;
        } else {
            LOG_DEBUG("Found duplicate %s", name.c_str());

            delete hdl;
            return it->second;
        }
    }

    uint64_t handle_count() { return handle_map.size(); }

    void clear() {
        std::map<std::string, GpiObjHdl *>::iterator it;

        // Delete the object handles before clearing the map
        for (it = handle_map.begin(); it != handle_map.end(); it++) {
            delete (it->second);
        }
        handle_map.clear();
    }

  private:
    std::map<std::string, GpiObjHdl *> handle_map;
};

static GpiHandleStore unique_handles;

#define CHECK_AND_STORE(_x) unique_handles.check_and_store(_x)
#define CLEAR_STORE() unique_handles.clear()

#else

#define CHECK_AND_STORE(_x) _x
#define CLEAR_STORE() (void)0  // No-op

#endif

static bool sim_ending = false;

static size_t gpi_print_registered_impl() {
    vector<GpiImplInterface *>::iterator iter;
    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        LOG_INFO("%s registered", (*iter)->get_name_c());
    }
    return registered_impls.size();
}

int gpi_register_impl(GpiImplInterface *func_tbl) {
    vector<GpiImplInterface *>::iterator iter;
    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        if ((*iter)->get_name_s() == func_tbl->get_name_s()) {
            LOG_WARN("%s already registered, check GPI_EXTRA",
                     func_tbl->get_name_c());
            return -1;
        }
    }
    registered_impls.push_back(func_tbl);
    return 0;
}

bool gpi_has_registered_impl() { return registered_impls.size() > 0; }

void gpi_embed_init(int argc, char const *const *argv) {
    if (embed_sim_init(argc, argv)) {
        gpi_embed_end();
    }
}

void gpi_embed_end() {
    embed_sim_event("Simulator shut down prematurely");
    gpi_sim_end();
}

void gpi_sim_end() {
    if (!sim_ending) {
        registered_impls[0]->sim_end();
        sim_ending = true;
    }
}

void gpi_cleanup(void) {
    CLEAR_STORE();
    embed_sim_cleanup();
}

static void gpi_load_libs(std::vector<std::string> to_load) {
    std::vector<std::string>::iterator iter;

    for (iter = to_load.begin(); iter != to_load.end(); iter++) {
        std::string arg = *iter;

        auto const idx = arg.rfind(
            ':');  // find from right since path could contain colons (Windows)
        if (idx == std::string::npos) {
            // no colon in the string
            printf("cocotb: Error parsing GPI_EXTRA %s\n", arg.c_str());
            exit(1);
        }

        std::string const lib_name = arg.substr(0, idx);
        std::string const func_name = arg.substr(idx + 1, std::string::npos);

        void *lib_handle = utils_dyn_open(lib_name.c_str());
        if (!lib_handle) {
            printf("cocotb: Error loading shared library %s\n",
                   lib_name.c_str());
            exit(1);
        }

        void *entry_point = utils_dyn_sym(lib_handle, func_name.c_str());
        if (!entry_point) {
            char const *fmt =
                "cocotb: Unable to find entry point %s for shared library "
                "%s\n%s";
            char const *msg =
                "        Perhaps you meant to use `,` instead of `:` to "
                "separate library names, as this changed in cocotb 1.4?\n";
            printf(fmt, func_name.c_str(), lib_name.c_str(), msg);
            exit(1);
        }

        layer_entry_func new_lib_entry = (layer_entry_func)entry_point;
        new_lib_entry();
    }
}

void gpi_entry_point() {
    const char *log_level = getenv("GPI_LOG_LEVEL");
    if (log_level) {
        static const std::map<std::string, int> log_level_str_table = {
            {"CRITICAL", GPI_CRITICAL}, {"ERROR", GPI_ERROR},
            {"WARNING", GPI_WARNING},   {"INFO", GPI_INFO},
            {"DEBUG", GPI_DEBUG},       {"TRACE", GPI_TRACE}};
        auto it = log_level_str_table.find(log_level);
        if (it != log_level_str_table.end()) {
            gpi_native_logger_set_level(it->second);
        } else {
            // LCOV_EXCL_START
            LOG_ERROR("Invalid log level: %s", log_level);
            // LCOV_EXCL_STOP
        }
    }

    /* Lets look at what other libs we were asked to load too */
    char *lib_env = getenv("GPI_EXTRA");

    if (lib_env) {
        std::string lib_list = lib_env;
        std::string const delim = ",";
        std::vector<std::string> to_load;

        size_t e_pos = 0;
        while (std::string::npos != (e_pos = lib_list.find(delim))) {
            std::string lib = lib_list.substr(0, e_pos);
            lib_list.erase(0, e_pos + delim.length());

            to_load.push_back(lib);
        }
        if (lib_list.length()) {
            to_load.push_back(lib_list);
        }

        gpi_load_libs(to_load);
    }

    /* Finally embed Python */
    embed_init_python();
    gpi_print_registered_impl();
}

void gpi_get_sim_time(uint32_t *high, uint32_t *low) {
    registered_impls[0]->get_sim_time(high, low);
}

void gpi_get_sim_precision(int32_t *precision) {
    /* We clamp to sensible values here, 1e-15 min and 1e3 max */
    int32_t val;
    registered_impls[0]->get_sim_precision(&val);
    if (val > 2) val = 2;

    if (val < -15) val = -15;

    *precision = val;
}

const char *gpi_get_simulator_product() {
    return registered_impls[0]->get_simulator_product();
}

const char *gpi_get_simulator_version() {
    return registered_impls[0]->get_simulator_version();
}

gpi_sim_hdl gpi_get_root_handle(const char *name) {
    /* May need to look over all the implementations that are registered
       to find this handle */
    vector<GpiImplInterface *>::iterator iter;

    GpiObjHdl *hdl = NULL;

    LOG_DEBUG("Looking for root handle '%s' over %d implementations", name,
              registered_impls.size());

    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        if ((hdl = (*iter)->get_root_handle(name))) {
            LOG_DEBUG("Got a Root handle (%s) back from %s",
                      hdl->get_name_str(), (*iter)->get_name_c());
            break;
        }
    }

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_ERROR("No root handle found");
        return hdl;
    }
}

static GpiObjHdl *gpi_get_handle_by_name_(GpiObjHdl *parent,
                                          const std::string &name,
                                          GpiImplInterface *skip_impl) {
    LOG_DEBUG("Searching for %s", name.c_str());

    // check parent impl *first* if it's not skipped
    if (!skip_impl || (skip_impl != parent->m_impl)) {
        auto hdl = parent->m_impl->native_check_create(name, parent);
        if (hdl) {
            return CHECK_AND_STORE(hdl);
        }
    }

    // iterate over all registered impls to see if we can get the signal
    for (auto iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        // check if impl is skipped
        if (skip_impl && (skip_impl == (*iter))) {
            LOG_DEBUG("Skipping %s implementation", (*iter)->get_name_c());
            continue;
        }

        // already checked parent implementation
        if ((*iter) == parent->m_impl) {
            LOG_DEBUG("Already checked %s implementation",
                      (*iter)->get_name_c());
            continue;
        }

        LOG_DEBUG("Checking if %s is native through implementation %s",
                  name.c_str(), (*iter)->get_name_c());

        /* If the current interface is not the same as the one that we
           are going to query then append the name we are looking for to
           the parent, such as <parent>.name. This is so that its entity can
           be seen discovered even if the parents implementation is not the same
           as the one that we are querying through */

        auto hdl = (*iter)->native_check_create(name, parent);
        if (hdl) {
            LOG_DEBUG("Found %s via %s", name.c_str(), (*iter)->get_name_c());
            return CHECK_AND_STORE(hdl);
        }
    }

    return NULL;
}

static GpiObjHdl *gpi_get_handle_by_raw(GpiObjHdl *parent, void *raw_hdl,
                                        GpiImplInterface *skip_impl) {
    vector<GpiImplInterface *>::iterator iter;

    GpiObjHdl *hdl = NULL;

    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        if (skip_impl && (skip_impl == (*iter))) {
            LOG_DEBUG("Skipping %s implementation", (*iter)->get_name_c());
            continue;
        }

        if ((hdl = (*iter)->native_check_create(raw_hdl, parent))) {
            LOG_DEBUG("Found %s via %s", hdl->get_name_str(),
                      (*iter)->get_name_c());
            break;
        }
    }

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_WARN(
            "Failed to convert a raw handle to valid object via any registered "
            "implementation");
        return hdl;
    }
}

gpi_sim_hdl gpi_get_handle_by_name(gpi_sim_hdl base, const char *name,
                                   gpi_discovery discovery_method = GPI_AUTO) {
    std::string s_name = name;
    GpiObjHdl *hdl = NULL;
    if (discovery_method == GPI_AUTO) {
        hdl = gpi_get_handle_by_name_(base, s_name, NULL);
        if (!hdl) {
            LOG_DEBUG(
                "Failed to find a handle named %s via any registered "
                "implementation",
                name);
        }
    } else if (discovery_method == GPI_NATIVE) {
        /* Explicitly does not try to cross language boundaries.
         * This can be useful when interfacing with
         * simulators that misbehave during (optional) signal discovery.
         */
        hdl = base->m_impl->native_check_create(name, base);
        if (!hdl) {
            LOG_DEBUG(
                "Failed to find a handle named %s via native implementation",
                name);
        }
    }
    return hdl;
}

gpi_sim_hdl gpi_get_handle_by_index(gpi_sim_hdl base, int32_t index) {
    GpiObjHdl *hdl = NULL;
    GpiImplInterface *intf = base->m_impl;

    /* Shouldn't need to iterate over interfaces because indexing into a handle
     * shouldn't cross the interface boundaries.
     *
     * NOTE: IUS's VPI interface returned valid VHDL handles, but then couldn't
     *       use the handle properly.
     */
    LOG_DEBUG("Checking if index %d native through implementation %s ", index,
              intf->get_name_c());
    hdl = intf->native_check_create(index, base);

    if (hdl)
        return CHECK_AND_STORE(hdl);
    else {
        LOG_WARN(
            "Failed to find a handle at index %d via any registered "
            "implementation",
            index);
        return hdl;
    }
}

gpi_iterator_hdl gpi_iterate(gpi_sim_hdl obj_hdl, gpi_iterator_sel type) {
    if (type == GPI_PACKAGE_SCOPES) {
        if (obj_hdl != NULL) {
            LOG_ERROR("Cannot iterate over package from non-NULL handles");
            return NULL;
        }

        vector<GpiImplInterface *>::iterator implIter;

        LOG_DEBUG("Looking for packages over %d implementations",
                  registered_impls.size());

        for (implIter = registered_impls.begin();
             implIter != registered_impls.end(); implIter++) {
            GpiIterator *iter =
                (*implIter)->iterate_handle(NULL, GPI_PACKAGE_SCOPES);
            if (iter != NULL) return iter;
        }
        return NULL;
    }

    GpiIterator *iter = obj_hdl->m_impl->iterate_handle(obj_hdl, type);
    if (!iter) {
        return NULL;
    }
    return iter;
}

gpi_sim_hdl gpi_next(gpi_iterator_hdl iter) {
    std::string name;
    GpiObjHdl *parent = iter->get_parent();

    while (true) {
        GpiObjHdl *next = NULL;
        void *raw_hdl = NULL;
        GpiIterator::Status ret = iter->next_handle(name, &next, &raw_hdl);

        switch (ret) {
            case GpiIterator::NATIVE:
                LOG_DEBUG("Create a native handle");
                return CHECK_AND_STORE(next);
            case GpiIterator::NATIVE_NO_NAME:
                LOG_DEBUG("Unable to fully setup handle, skipping");
                continue;
            case GpiIterator::NOT_NATIVE:
                LOG_DEBUG(
                    "Found a name but unable to create via native "
                    "implementation, trying others");
                next = gpi_get_handle_by_name_(parent, name, iter->m_impl);
                if (next) {
                    return next;
                }
                LOG_WARN(
                    "Unable to create %s via any registered implementation",
                    name.c_str());
                continue;
            case GpiIterator::NOT_NATIVE_NO_NAME:
                LOG_DEBUG(
                    "Found an object but not accessible via %s, trying others",
                    iter->m_impl->get_name_c());
                next = gpi_get_handle_by_raw(parent, raw_hdl, iter->m_impl);
                if (next) {
                    return next;
                }
                continue;
            case GpiIterator::END:
                LOG_DEBUG("Reached end of iterator");
                delete iter;
                return NULL;
        }
    }
}

const char *gpi_get_definition_name(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_definition_name();
}

const char *gpi_get_definition_file(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_definition_file();
}

static std::string g_binstr;

const char *gpi_get_signal_value_binstr(gpi_sim_hdl sig_hdl) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    g_binstr = obj_hdl->get_signal_value_binstr();
    std::transform(g_binstr.begin(), g_binstr.end(), g_binstr.begin(),
                   ::toupper);
    return g_binstr.c_str();
}

const char *gpi_get_signal_value_str(gpi_sim_hdl sig_hdl) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    return obj_hdl->get_signal_value_str();
}

double gpi_get_signal_value_real(gpi_sim_hdl sig_hdl) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    return obj_hdl->get_signal_value_real();
}

long gpi_get_signal_value_long(gpi_sim_hdl sig_hdl) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    return obj_hdl->get_signal_value_long();
}

const char *gpi_get_signal_name_str(gpi_sim_hdl sig_hdl) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    return obj_hdl->get_name_str();
}

const char *gpi_get_signal_type_str(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_type_str();
}

gpi_objtype gpi_get_object_type(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_type();
}

int gpi_is_constant(gpi_sim_hdl obj_hdl) {
    if (obj_hdl->get_const()) return 1;
    return 0;
}

int gpi_is_indexable(gpi_sim_hdl obj_hdl) {
    if (obj_hdl->get_indexable()) return 1;
    return 0;
}

void gpi_set_signal_value_int(gpi_sim_hdl sig_hdl, int32_t value,
                              gpi_set_action action) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);

    obj_hdl->set_signal_value(value, action);
}

void gpi_set_signal_value_binstr(gpi_sim_hdl sig_hdl, const char *binstr,
                                 gpi_set_action action) {
    std::string value = binstr;
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    obj_hdl->set_signal_value_binstr(value, action);
}

void gpi_set_signal_value_str(gpi_sim_hdl sig_hdl, const char *str,
                              gpi_set_action action) {
    std::string value = str;
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    obj_hdl->set_signal_value_str(value, action);
}

void gpi_set_signal_value_real(gpi_sim_hdl sig_hdl, double value,
                               gpi_set_action action) {
    GpiSignalObjHdl *obj_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);
    obj_hdl->set_signal_value(value, action);
}

int gpi_get_num_elems(gpi_sim_hdl obj_hdl) { return obj_hdl->get_num_elems(); }

int gpi_get_range_left(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_range_left();
}

int gpi_get_range_right(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_range_right();
}

gpi_range_dir gpi_get_range_dir(gpi_sim_hdl obj_hdl) {
    return obj_hdl->get_range_dir();
}

gpi_cb_hdl gpi_register_value_change_callback(int (*gpi_function)(void *),
                                              void *gpi_cb_data,
                                              gpi_sim_hdl sig_hdl,
                                              gpi_edge edge) {
    GpiSignalObjHdl *signal_hdl = static_cast<GpiSignalObjHdl *>(sig_hdl);

    /* Do something based on int & GPI_RISING | GPI_FALLING */
    GpiCbHdl *gpi_hdl = signal_hdl->register_value_change_callback(
        edge, gpi_function, gpi_cb_data);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a value change callback");
        return NULL;
    } else {
        return gpi_hdl;
    }
}

gpi_cb_hdl gpi_register_timed_callback(int (*gpi_function)(void *),
                                       void *gpi_cb_data, uint64_t time) {
    // It should not matter which implementation we use for this so just pick
    // the first one
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_timed_callback(
        time, gpi_function, gpi_cb_data);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a timed callback");
        return NULL;
    } else {
        return gpi_hdl;
    }
}

gpi_cb_hdl gpi_register_readonly_callback(int (*gpi_function)(void *),
                                          void *gpi_cb_data) {
    // It should not matter which implementation we use for this so just pick
    // the first one
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_readonly_callback(
        gpi_function, gpi_cb_data);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readonly callback");
        return NULL;
    } else {
        return gpi_hdl;
    }
}

gpi_cb_hdl gpi_register_nexttime_callback(int (*gpi_function)(void *),
                                          void *gpi_cb_data) {
    // It should not matter which implementation we use for this so just pick
    // the first one
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_nexttime_callback(
        gpi_function, gpi_cb_data);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a nexttime callback");
        return NULL;
    } else {
        return gpi_hdl;
    }
}

gpi_cb_hdl gpi_register_readwrite_callback(int (*gpi_function)(void *),
                                           void *gpi_cb_data) {
    // It should not matter which implementation we use for this so just pick
    // the first one
    GpiCbHdl *gpi_hdl = registered_impls[0]->register_readwrite_callback(
        gpi_function, gpi_cb_data);
    if (!gpi_hdl) {
        LOG_ERROR("Failed to register a readwrite callback");
        return NULL;
    } else {
        return gpi_hdl;
    }
}

int gpi_remove_cb(gpi_cb_hdl cb_hdl) { return cb_hdl->remove(); }

void gpi_get_cb_info(gpi_cb_hdl cb_hdl, int (**cb_func)(void *),
                     void **cb_data) {
    cb_hdl->get_cb_info(cb_func, cb_data);
}

const char *GpiImplInterface::get_name_c() { return m_name.c_str(); }

const string &GpiImplInterface::get_name_s() { return m_name; }

void gpi_to_user() { LOG_TRACE("Passing control to GPI user"); }

void gpi_to_simulator() {
    if (sim_ending) {
        gpi_cleanup();
    }
    LOG_TRACE("Returning control to simulator");
}
