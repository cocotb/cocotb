/******************************************************************************
 * Copyright (c) 2013, 2018 Potential Ventures Ltd
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *    * Redistributions of source code must retain the above copyright
 *      notice, this list of conditions and the following disclaimer.
 *    * Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *    * Neither the name of Potential Ventures Ltd,
 *       SolarFlare Communications Inc nor the
 *      names of its contributors may be used to endorse or promote products
 *      derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE dGOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#ifndef COCOTB_GPI_PRIV_H_
#define COCOTB_GPI_PRIV_H_

#include <exports.h>
#ifdef GPI_EXPORTS
#define GPI_EXPORT COCOTB_EXPORT
#else
#define GPI_EXPORT COCOTB_IMPORT
#endif

#include <embed.h>
#include <gpi.h>

#include <map>
#include <string>
#include <vector>

typedef enum gpi_cb_state {
    GPI_FREE = 0,
    GPI_PRIMED = 1,
    GPI_CALL = 2,
    GPI_DELETE = 4,
} gpi_cb_state_e;

class GpiCbHdl;
class GpiImplInterface;
class GpiIterator;
class GpiCbHdl;

/* Base GPI class others are derived from */
class GPI_EXPORT GpiHdl {
  public:
    GpiHdl(GpiImplInterface *impl, void *hdl = NULL)
        : m_impl(impl), m_obj_hdl(hdl) {}
    virtual ~GpiHdl() = default;

    template <typename T>
    T get_handle() const {
        return static_cast<T>(m_obj_hdl);
    }

  private:
    GpiHdl() {}  // Disable default constructor

  public:
    GpiImplInterface *m_impl;                   // VPI/VHPI/FLI routines
    bool is_this_impl(GpiImplInterface *impl);  // Is the passed interface the
                                                // one this object uses?

  protected:
    void *m_obj_hdl;
};

/* GPI object handle, maps to a simulation object */
// An object is any item in the hierarchy
// Provides methods for iterating through children or finding by name
// Initial object is returned by call to GpiImplInterface::get_root_handle()
// Subsequent operations to get children go through this handle.
// GpiObjHdl::get_handle_by_name/get_handle_by_index are really factories
// that construct an object derived from GpiSignalObjHdl or GpiObjHdl
class GPI_EXPORT GpiObjHdl : public GpiHdl {
  public:
    GpiObjHdl(GpiImplInterface *impl, void *hdl = nullptr,
              gpi_objtype_t objtype = GPI_UNKNOWN, bool is_const = false)
        : GpiHdl(impl, hdl), m_type(objtype), m_const(is_const) {}

    virtual ~GpiObjHdl() = default;

    virtual const char *get_name_str();
    virtual const char *get_fullname_str();
    virtual const char *get_type_str();
    gpi_objtype_t get_type() { return m_type; };
    bool get_const() { return m_const; };
    int get_num_elems() {
        LOG_DEBUG("%s has %d elements", m_name.c_str(), m_num_elems);
        return m_num_elems;
    }
    int get_range_left() { return m_range_left; }
    int get_range_right() { return m_range_right; }
    int get_indexable() { return m_indexable; }

    const std::string &get_name();
    const std::string &get_fullname();

    virtual const char *get_definition_name() {
        return m_definition_name.c_str();
    };
    virtual const char *get_definition_file() {
        return m_definition_file.c_str();
    };

    bool is_native_impl(GpiImplInterface *impl);
    virtual int initialise(std::string &name, std::string &full_name);

  protected:
    int m_num_elems = 0;
    bool m_indexable = false;
    int m_range_left = -1;
    int m_range_right = -1;
    std::string m_name;
    std::string m_fullname = "unknown";

    std::string m_definition_name;
    std::string m_definition_file;

    gpi_objtype_t m_type;
    bool m_const;
};

/* GPI Signal object handle, maps to a simulation object */
//
// Identical to an object but adds additional methods for getting/setting the
// value of the signal (which doesn't apply to non signal items in the hierarchy
class GPI_EXPORT GpiSignalObjHdl : public GpiObjHdl {
  public:
    using GpiObjHdl::GpiObjHdl;

    virtual ~GpiSignalObjHdl() = default;
    // Provide public access to the implementation (composition vs inheritance)
    virtual const char *get_signal_value_binstr() = 0;
    virtual const char *get_signal_value_str() = 0;
    virtual double get_signal_value_real() = 0;
    virtual long get_signal_value_long() = 0;

    int m_length = 0;

    virtual int set_signal_value(const int32_t value,
                                 gpi_set_action_t action) = 0;
    virtual int set_signal_value(const double value,
                                 gpi_set_action_t action) = 0;
    virtual int set_signal_value_str(std::string &value,
                                     gpi_set_action_t action) = 0;
    virtual int set_signal_value_binstr(std::string &value,
                                        gpi_set_action_t action) = 0;
    // virtual GpiCbHdl monitor_value(bool rising_edge) = 0; this was for the
    // triggers
    // but the explicit ones are probably better

    virtual GpiCbHdl *value_change_cb(int edge) = 0;
};

/* GPI Callback handle */
// To set a callback it needs the signal to do this on,
// vpiHandle/vhpiHandleT for instance. The
class GPI_EXPORT GpiCbHdl : public GpiHdl {
  public:
    GpiCbHdl(GpiImplInterface *impl) : GpiHdl(impl) {}

    // Pure virtual functions for derived classes
    virtual int arm_callback() = 0;  // Register with simulator
    virtual int run_callback();      // Entry point from simulator
    virtual int
    cleanup_callback() = 0;  // Cleanup the callback, arm can be called after

    // Set the data to be used for run callback, separate to arm_callback so
    // data can be re-used
    int set_user_data(int (*gpi_function)(const void *), const void *data);
    const void *get_user_data();

    void set_call_state(gpi_cb_state_e new_state);
    gpi_cb_state_e get_call_state();

    virtual ~GpiCbHdl();

  protected:
    int (*gpi_function)(const void *) = nullptr;  // GPI function to callback
    const void *m_cb_data = nullptr;  // GPI data supplied to "gpi_function"
    gpi_cb_state_e m_state =
        GPI_FREE;  // GPI state of the callback through its cycle
};

class GPI_EXPORT GpiValueCbHdl : public virtual GpiCbHdl {
  public:
    GpiValueCbHdl(GpiImplInterface *impl, GpiSignalObjHdl *signal, int edge);
    int run_callback() override;

  protected:
    std::string required_value;
    GpiSignalObjHdl *m_signal;
};

class GPI_EXPORT GpiIterator : public GpiHdl {
  public:
    enum Status {
        NATIVE,          // Fully resolved object was created
        NATIVE_NO_NAME,  // Native object was found but unable to fully create
        NOT_NATIVE,      // Non-native object was found but we did get a name
        NOT_NATIVE_NO_NAME,  // Non-native object was found without a name
        END
    };

    GpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl)
        : GpiHdl(impl), m_parent(hdl) {}
    virtual ~GpiIterator() = default;

    virtual Status next_handle(std::string &name, GpiObjHdl **hdl, void **) {
        name = "";
        *hdl = NULL;
        return GpiIterator::END;
    }

    GpiObjHdl *get_parent() { return m_parent; }

  protected:
    GpiObjHdl *m_parent;
};

class GPI_EXPORT GpiImplInterface {
  public:
    GpiImplInterface(const std::string &name) : m_name(name) {}
    const char *get_name_c();
    const std::string &get_name_s();
    virtual ~GpiImplInterface() = default;

    /* Sim related */
    virtual void sim_end() = 0;
    virtual void get_sim_time(uint32_t *high, uint32_t *low) = 0;
    virtual void get_sim_precision(int32_t *precision) = 0;
    virtual const char *get_simulator_product() = 0;
    virtual const char *get_simulator_version() = 0;

    /* Hierarchy related */
    virtual GpiObjHdl *native_check_create(std::string &name,
                                           GpiObjHdl *parent) = 0;
    virtual GpiObjHdl *native_check_create(int32_t index,
                                           GpiObjHdl *parent) = 0;
    virtual GpiObjHdl *native_check_create(void *raw_hdl,
                                           GpiObjHdl *parent) = 0;
    virtual GpiObjHdl *get_root_handle(const char *name) = 0;
    virtual GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                        gpi_iterator_sel_t type) = 0;

    /* Callback related, these may (will) return the same handle */
    virtual GpiCbHdl *register_timed_callback(uint64_t time) = 0;
    virtual GpiCbHdl *register_readonly_callback() = 0;
    virtual GpiCbHdl *register_nexttime_callback() = 0;
    virtual GpiCbHdl *register_readwrite_callback() = 0;
    virtual int deregister_callback(GpiCbHdl *obj_hdl) = 0;

    /* Method to provide strings from operation types */
    virtual const char *reason_to_string(int reason) = 0;

  private:
    std::string m_name;

  protected:
    std::string m_product;
    std::string m_version;
};

/* Called from implementation layers back up the stack */
GPI_EXPORT int gpi_register_impl(GpiImplInterface *func_tbl);

GPI_EXPORT void gpi_embed_init(int argc, char const *const *argv);
GPI_EXPORT void gpi_embed_end();
GPI_EXPORT void gpi_entry_point();
GPI_EXPORT void gpi_to_user();
GPI_EXPORT void gpi_to_simulator();

typedef void (*layer_entry_func)();

/* Use this macro in an implementation layer to define an entry point */
#define GPI_ENTRY_POINT(NAME, func)                     \
    extern "C" {                                        \
    COCOTB_EXPORT void NAME##_entry_point() { func(); } \
    }

#endif /* COCOTB_GPI_PRIV_H_ */
