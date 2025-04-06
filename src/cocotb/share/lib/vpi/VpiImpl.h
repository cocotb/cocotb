// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_VPI_IMPL_H_
#define COCOTB_VPI_IMPL_H_

#include <cstring>
#include <map>
#include <vector>

#include "../gpi/gpi_priv.h"
#include "_vendor/vpi/sv_vpi_user.h"
#include "exports.h"
#include "gpi.h"
#include "gpi_logging.h"

#ifdef COCOTBVPI_EXPORTS
#define COCOTBVPI_EXPORT COCOTB_EXPORT
#else
#define COCOTBVPI_EXPORT COCOTB_IMPORT
#endif

// TODO Move the check_vpi_error stuff into another file

// Should be run after every VPI call to check error status
static inline void __check_vpi_error(const char *file, const char *func,
                                     long line) {
    if (gpi_log_filtered("gpi", GPI_DEBUG)) {
        return;
    }

    int level = 0;
    s_vpi_error_info info;
    enum gpi_log_level loglevel;

    memset(&info, 0, sizeof(info));
    level = vpi_chk_error(&info);
    if (info.code == 0 && level == 0) {
        return;
    }

    switch (level) {
        case vpiNotice:
            loglevel = GPI_INFO;
            break;
        case vpiWarning:
            loglevel = GPI_WARNING;
            break;
        case vpiError:
            loglevel = GPI_ERROR;
            break;
        case vpiSystem:
        case vpiInternal:
            loglevel = GPI_CRITICAL;
            break;
        default:
            loglevel = GPI_WARNING;
    }

    LOG_EXPLICIT("gpi", GPI_DEBUG, file, func, line,
                 "VPI Internal Error: %s @ %s:%d: %s",
                 gpi_log_level_to_str(loglevel), info.file, info.line,
                 info.message);
}

#define check_vpi_error()                                \
    do {                                                 \
        __check_vpi_error(__FILE__, __func__, __LINE__); \
    } while (0)

class VpiCbHdl : public GpiCbHdl {
  public:
    VpiCbHdl(GpiImplInterface *impl);

    int arm() override;
    int remove() override;
    int run() override;

  protected:
    s_cb_data cb_data;
    s_vpi_time vpi_time;
    bool m_removed = false;
};

class VpiSignalObjHdl;

class VpiValueCbHdl : public VpiCbHdl {
  public:
    VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig, gpi_edge edge);
    int run() override;

  private:
    s_vpi_value m_vpi_value;
    GpiSignalObjHdl *m_signal;
    gpi_edge m_edge;
};

class VpiTimedCbHdl : public VpiCbHdl {
  public:
    VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time);
};

class VpiReadOnlyCbHdl : public VpiCbHdl {
  public:
    VpiReadOnlyCbHdl(GpiImplInterface *impl);
};

class VpiNextPhaseCbHdl : public VpiCbHdl {
  public:
    VpiNextPhaseCbHdl(GpiImplInterface *impl);
};

class VpiReadWriteCbHdl : public VpiCbHdl {
  public:
    VpiReadWriteCbHdl(GpiImplInterface *impl);
};

class VpiStartupCbHdl : public VpiCbHdl {
  public:
    VpiStartupCbHdl(GpiImplInterface *impl);

    // Too many sims get upset trying to remove startup callbacks so we just
    // don't try. TODO Is this still accurate?

    int run() override {
        int res = 0;
        if (!m_removed) {
            res = m_cb_func(m_cb_data);
        }
        delete this;
        return res;
    }

    int remove() override {
        m_removed = true;
        return 0;
    }
};

class VpiShutdownCbHdl : public VpiCbHdl {
  public:
    VpiShutdownCbHdl(GpiImplInterface *impl);

    // Too many sims get upset trying to remove startup callbacks so we just
    // don't try. TODO Is this still accurate?

    int run() override {
        int res = 0;
        if (!m_removed) {
            res = m_cb_func(m_cb_data);
        }
        delete this;
        return res;
    }

    int remove() override {
        m_removed = true;
        return 0;
    }
};

class VpiArrayObjHdl : public GpiObjHdl {
  public:
    VpiArrayObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype objtype)
        : GpiObjHdl(impl, hdl, objtype) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VpiObjHdl : public GpiObjHdl {
  public:
    VpiObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype objtype)
        : GpiObjHdl(impl, hdl, objtype) {}

    const char *get_definition_name() override;
    const char *get_definition_file() override;
};

class VpiSignalObjHdl : public GpiSignalObjHdl {
  public:
    VpiSignalObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype objtype,
                    bool is_const)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const) {}

    const char *get_signal_value_binstr() override;
    const char *get_signal_value_str() override;
    double get_signal_value_real() override;
    long get_signal_value_long() override;

    int set_signal_value(const int32_t value, gpi_set_action action) override;
    int set_signal_value(const double value, gpi_set_action action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action action) override;

    /* Value change callback accessor */
    int initialise(const std::string &name,
                   const std::string &fq_name) override;
    GpiCbHdl *register_value_change_callback(gpi_edge edge,
                                             int (*function)(void *),
                                             void *cb_data) override;

  private:
    int set_signal_value(s_vpi_value value, gpi_set_action action);
};

class VpiIterator : public GpiIterator {
  public:
    VpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl);

    ~VpiIterator() override;

    Status next_handle(std::string &name, GpiObjHdl **hdl,
                       void **raw_hdl) override;

  private:
    vpiHandle m_iterator;
    static std::map<int32_t, std::vector<int32_t>>
        iterate_over;               /* Possible mappings */
    std::vector<int32_t> *selected; /* Mapping currently in use */
    std::vector<int32_t>::iterator one2many;
};

// Base class for simple iterator that only iterates over a single type
class VpiSingleIterator : public GpiIterator {
  public:
    VpiSingleIterator(GpiImplInterface *impl, GpiObjHdl *hdl, int32_t vpitype)
        : GpiIterator(impl, hdl)

    {
        vpiHandle vpi_hdl = m_parent->get_handle<vpiHandle>();
        m_iterator = vpi_iterate(vpitype, vpi_hdl);
        if (NULL == m_iterator) {
            LOG_DEBUG("vpi_iterate returned NULL for type %d for object %s(%d)",
                      vpitype, vpi_get_str(vpiType, vpi_hdl),
                      vpi_get(vpiType, vpi_hdl));
            return;
        }
    }

    Status next_handle(std::string &name, GpiObjHdl **hdl,
                       void **raw_hdl) override;

  protected:
    vpiHandle m_iterator = nullptr;
};

class VpiPackageIterator : public GpiIterator {
  public:
    VpiPackageIterator(GpiImplInterface *impl)
        : GpiIterator(impl, nullptr)

    {
        // Questa doesn't support iteration over vpiPackage but everything
        // supports vpiInstance which is a superset
        m_iterator = vpi_iterate(vpiInstance, nullptr);
        if (NULL == m_iterator) {
            LOG_WARN(
                "vpi_iterate returned NULL for type vpiInstance for object "
                "NULL");
            return;
        }
    }

    Status next_handle(std::string &name, GpiObjHdl **hdl,
                       void **raw_hdl) override;

  private:
    vpiHandle m_iterator = nullptr;
};

class VpiImpl : public GpiImplInterface {
  public:
    VpiImpl(const std::string &name) : GpiImplInterface(name) {}

    /* Sim related */
    void sim_end(void) override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierarchy related */
    GpiObjHdl *get_root_handle(const char *name) override;
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                gpi_iterator_sel type) override;
    GpiObjHdl *next_handle(GpiIterator *iter);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time, int (*function)(void *),
                                      void *cb_data) override;
    GpiCbHdl *register_readonly_callback(int (*function)(void *),
                                         void *cb_data) override;
    GpiCbHdl *register_nexttime_callback(int (*function)(void *),
                                         void *cb_data) override;
    GpiCbHdl *register_readwrite_callback(int (*function)(void *),
                                          void *cb_data) override;
    GpiObjHdl *native_check_create(const std::string &name,
                                   GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(int32_t index, GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(void *raw_hdl, GpiObjHdl *parent) override;
    const char *reason_to_string(int reason) override;
    GpiObjHdl *create_gpi_obj_from_handle(vpiHandle new_hdl,
                                          const std::string &name,
                                          const std::string &fq_name);

    static bool compare_generate_labels(const std::string &a,
                                        const std::string &b);

    const char *get_type_delimiter(GpiObjHdl *obj_hdl);

    void main() noexcept;

  private:
    // We store the shutdown callback handle here so sim_end() can remove() it
    // if it's called.
    VpiShutdownCbHdl *m_sim_finish_cb;
};

#endif /*COCOTB_VPI_IMPL_H_  */
