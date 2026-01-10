// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <gpi.h>
#include <sys/types.h>

#include <algorithm>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "./gpi_priv.hpp"
#include "./logging.hpp"

using namespace std;

static vector<GpiImplInterface *> registered_impls;
static vector<std::pair<int (*)(void *, int, char const *const *), void *>>
    start_of_sim_time_cbs;
static vector<std::pair<void (*)(void *), void *>> end_of_sim_time_cbs;
static vector<std::pair<void (*)(void *), void *>> finalize_cbs;

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

static bool gpi_finalizing = false;

static size_t gpi_print_registered_impl() {
    vector<GpiImplInterface *>::iterator iter;
    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        LOG_INFO("GPI: %s support registered", (*iter)->get_name_c());
    }
    return registered_impls.size();
}

int gpi_register_impl(GpiImplInterface *func_tbl) {
    vector<GpiImplInterface *>::iterator iter;
    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        if ((*iter)->get_name_s() == func_tbl->get_name_s()) {
            LOG_WARN("GPI: %s support already registered, check GPI_EXTRA",
                     func_tbl->get_name_c());
            return -1;
        }
    }
    registered_impls.push_back(func_tbl);
    return 0;
}

bool gpi_has_registered_impl() { return registered_impls.size() > 0; }

void gpi_start_of_sim_time(int argc, char const *const *argv) {
    for (auto &cb_info : start_of_sim_time_cbs) {
        // start_of_sime_time should never fail, this should be moved to
        // gpi_load_users, as should the (argc,argv)
        LOG_TRACE("[ GPI Start Sim ] => User Start callback");
        int error = cb_info.first(cb_info.second, argc, argv);
        LOG_TRACE("User Start callback => [ GPI Start Sim ]");
        if (error) {
            gpi_end_of_sim_time();
        }
    }
}

void gpi_end_of_sim_time() {
    for (auto &cb_info : end_of_sim_time_cbs) {
        LOG_TRACE("[ GPI End Sim ] => User End callback");
        cb_info.first(cb_info.second);
        LOG_TRACE("User End callback => [ GPI End Sim ]");
    }
    // always request simulation termination at end_of_sim_time
    gpi_finish();
}

void gpi_finish() {
    if (!gpi_finalizing) {
        registered_impls[0]->sim_end();
        gpi_finalizing = true;
    }
}

void gpi_finalize(void) {
    CLEAR_STORE();
    for (auto it = finalize_cbs.rbegin(); it != finalize_cbs.rend(); it++) {
        LOG_TRACE("[ GPI Finalize ] => User Finalize callback");
        it->first(it->second);
        LOG_TRACE("User Finalize callback => [ GPI Finalize ]");
    }
}

void gpi_check_cleanup(void) {
    if (gpi_finalizing) {
        gpi_finalize();
    }
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
        LOG_TRACE("[ GPI Init ] => Impl Init (%s)", arg.c_str());
        new_lib_entry();
        LOG_TRACE("Impl Init => [ GPI Init ]");
    }
}

static int gpi_load_users() {
    auto users = getenv("GPI_USERS");
    if (!users) {
        LOG_ERROR("No GPI_USERS specified, exiting...");
        return -1;
    }
    // I would have loved to use istringstream and getline, but it causes a
    // compilation issue when compiling with newer GCCs against C++11.
    std::string users_str = users;
    std::string::size_type start_idx = 0;
    bool done = false;
    while (!done) {
        auto next_delim = users_str.find(';', start_idx);
        if (next_delim == std::string::npos) {
            done = true;
            next_delim = users_str.length();
        }
        auto user = users_str.substr(start_idx, next_delim - start_idx);
        start_idx = next_delim + 1;

        auto split_idx = user.rfind(',');

        std::string lib_name;
        std::string func_name;
        if (split_idx == std::string::npos) {
            lib_name = std::move(user);
        } else {
            lib_name = user.substr(0, split_idx);
            func_name = user.substr(split_idx + 1, std::string::npos);
        }

        void *lib_handle = utils_dyn_open(lib_name.c_str());
        if (!lib_handle) {
            LOG_ERROR("Error loading library '%s'", lib_name.c_str());
            gpi_finish();
            return -1;
        }

        if (split_idx != std::string::npos) {
            void *func_handle = utils_dyn_sym(lib_handle, func_name.c_str());
            if (!func_handle) {
                LOG_ERROR(
                    "Error getting entry func '%s' from loaded library '%s'",
                    func_name.c_str(), lib_name.c_str());
                gpi_finish();
                return -1;
            }

            LOG_INFO("Running entry func '%s' from loaded library '%s'",
                     func_name.c_str(), lib_name.c_str());

            auto entry_func = (void (*)(void))func_handle;
            LOG_TRACE("[ GPI Init ] => User Init (%s:%s)", lib_name.c_str(),
                      func_name.c_str());
            entry_func();
            LOG_TRACE("User Init => [ GPI Init ]");
        } else {
            LOG_INFO("Loaded entry library: '%s'", lib_name.c_str());
        }
    }

    return 0;
}

void gpi_entry_point() {
    LOG_TRACE("=> [ GPI Init ]");

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

    // Load users
    if (gpi_load_users()) {
        return;
    }

    gpi_print_registered_impl();

    LOG_TRACE("[ GPI Init ] =>");
}

GPI_EXPORT void gpi_init_logging_and_debug() {
    char *debug_env = getenv("GPI_DEBUG");
    if (debug_env) {
        std::string gpi_debug = debug_env;
        // If it's explicitly set to 0, don't enable
        if (gpi_debug != "0") {
            gpi_debug_enabled = 1;
        }
    }

    const char *log_level = getenv("GPI_LOG_LEVEL");
    if (log_level) {
        static const std::map<std::string, enum gpi_log_level>
            log_level_str_table = {
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

static GpiObjHdl *gpi_get_child_by_name(GpiObjHdl *parent,
                                        const std::string &name,
                                        GpiImplInterface *skip_impl) {
    LOG_DEBUG("Searching for %s", name.c_str());

    // check parent impl *first* if it's not skipped
    if (!skip_impl || (skip_impl != parent->m_impl)) {
        auto hdl = parent->m_impl->get_child_by_name(name, parent);
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

        auto hdl = (*iter)->get_child_by_name(name, parent);
        if (hdl) {
            LOG_DEBUG("Found %s via %s", name.c_str(), (*iter)->get_name_c());
            return CHECK_AND_STORE(hdl);
        }
    }

    return NULL;
}

static GpiObjHdl *gpi_get_child_from_handle(GpiObjHdl *parent, void *raw_hdl,
                                            GpiImplInterface *skip_impl) {
    vector<GpiImplInterface *>::iterator iter;

    GpiObjHdl *hdl = NULL;

    for (iter = registered_impls.begin(); iter != registered_impls.end();
         iter++) {
        if (skip_impl && (skip_impl == (*iter))) {
            LOG_DEBUG("Skipping %s implementation", (*iter)->get_name_c());
            continue;
        }

        if ((hdl = (*iter)->get_child_from_handle(raw_hdl, parent))) {
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
        hdl = gpi_get_child_by_name(base, s_name, NULL);
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
        hdl = base->m_impl->get_child_by_name(name, base);
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
    hdl = intf->get_child_by_index(index, base);

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
                next = gpi_get_child_by_name(parent, name, iter->m_impl);
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
                next = gpi_get_child_from_handle(parent, raw_hdl, iter->m_impl);
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

int gpi_is_signed(gpi_sim_hdl obj_hdl) { return obj_hdl->get_signed(); }

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

int gpi_register_start_of_sim_time_callback(int (*cb)(void *, int,
                                                      char const *const *),
                                            void *cb_data) {
    start_of_sim_time_cbs.push_back(std::make_pair(cb, cb_data));
    return 0;
}

int gpi_register_end_of_sim_time_callback(void (*cb)(void *), void *cb_data) {
    end_of_sim_time_cbs.push_back(std::make_pair(cb, cb_data));
    return 0;
}

int gpi_register_finalize_callback(void (*cb)(void *), void *cb_data) {
    finalize_cbs.push_back(std::make_pair(cb, cb_data));
    return 0;
}
