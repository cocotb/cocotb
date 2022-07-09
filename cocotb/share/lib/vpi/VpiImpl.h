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
 *    * Neither the name of Potential Ventures Ltd
 *      names of its contributors may be used to endorse or promote products
 *      derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 ******************************************************************************/

#ifndef COCOTB_VPI_IMPL_H_
#define COCOTB_VPI_IMPL_H_

#include <exports.h>
#ifdef COCOTBVPI_EXPORTS
#define COCOTBVPI_EXPORT COCOTB_EXPORT
#else
#define COCOTBVPI_EXPORT COCOTB_IMPORT
#endif

#include <map>
#include <vector>

#include "../gpi/gpi_priv.h"
#include "_vendor/vpi/sv_vpi_user.h"
#include "vpi_user_ext.h"

// Should be run after every VPI call to check error status
static inline int __check_vpi_error(const char *file, const char *func,
                                    long line) {
    int level = 0;
#if VPI_CHECKING
    s_vpi_error_info info;
    enum gpi_log_levels loglevel;

    memset(&info, 0, sizeof(info));
    level = vpi_chk_error(&info);
    if (info.code == 0 && level == 0) return 0;

    switch (level) {
        case vpiNotice:
            loglevel = GPIInfo;
            break;
        case vpiWarning:
            loglevel = GPIWarning;
            break;
        case vpiError:
            loglevel = GPIError;
            break;
        case vpiSystem:
        case vpiInternal:
            loglevel = GPICritical;
            break;
        default:
            loglevel = GPIWarning;
    }

    gpi_log("gpi", loglevel, file, func, line, "VPI error");
    gpi_log("gpi", loglevel, info.file, info.product, info.line, info.message);

#endif
    return level;
}

#define check_vpi_error()                                \
    do {                                                 \
        __check_vpi_error(__FILE__, __func__, __LINE__); \
    } while (0)

class VpiReadwriteCbHdl;
class VpiNextPhaseCbHdl;
class VpiReadOnlyCbHdl;

class VpiCbHdl : public virtual GpiCbHdl {
  public:
    VpiCbHdl(GpiImplInterface *impl);

    int arm_callback() override;
    int cleanup_callback() override;

  protected:
    s_cb_data cb_data;
    s_vpi_time vpi_time;
};

class VpiSignalObjHdl;

class VpiValueCbHdl : public VpiCbHdl, public GpiValueCbHdl {
  public:
    VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig, int edge);
    int cleanup_callback() override;

  private:
    s_vpi_value m_vpi_value;
};

class VpiCommonCbHdl : public VpiCbHdl, public GpiCommonCbHdl {
  public:
    VpiCommonCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), VpiCbHdl(impl), GpiCommonCbHdl(impl) {}
};

class VpiTimedCbHdl : public VpiCommonCbHdl {
  public:
    VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time);
    int cleanup_callback() override;
};

class VpiReadOnlyCbHdl : public VpiCommonCbHdl {
  public:
    VpiReadOnlyCbHdl(GpiImplInterface *impl);
};

class VpiNextPhaseCbHdl : public VpiCommonCbHdl {
  public:
    VpiNextPhaseCbHdl(GpiImplInterface *impl);
};

class VpiReadWriteCbHdl : public VpiCommonCbHdl {
  public:
    VpiReadWriteCbHdl(GpiImplInterface *impl);
};

class VpiStartupCbHdl : public VpiCbHdl {
  public:
    VpiStartupCbHdl(GpiImplInterface *impl);
    int run_callback() override;
    int cleanup_callback() override {
        /* Too many sims get upset with this so we override to do nothing */
        return 0;
    }
};

class VpiShutdownCbHdl : public VpiCbHdl {
  public:
    VpiShutdownCbHdl(GpiImplInterface *impl);
    int run_callback() override;
    int cleanup_callback() override {
        /* Too many sims get upset with this so we override to do nothing */
        return 0;
    }
};

class VpiArrayObjHdl : public GpiObjHdl {
  public:
    VpiArrayObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype_t objtype)
        : GpiObjHdl(impl, hdl, objtype) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VpiObjHdl : public GpiObjHdl {
  public:
    VpiObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype_t objtype)
        : GpiObjHdl(impl, hdl, objtype) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VpiSignalObjHdl : public GpiSignalObjHdl {
  public:
    VpiSignalObjHdl(GpiImplInterface *impl, vpiHandle hdl,
                    gpi_objtype_t objtype, bool is_const)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const),
          m_rising_cb(impl, this, GPI_RISING),
          m_falling_cb(impl, this, GPI_FALLING),
          m_either_cb(impl, this, GPI_FALLING | GPI_RISING) {}

    const char *get_signal_value_binstr() override;
    const char *get_signal_value_str() override;
    double get_signal_value_real() override;
    long get_signal_value_long() override;

    int set_signal_value(const int32_t value, gpi_set_action_t action) override;
    int set_signal_value(const double value, gpi_set_action_t action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action_t action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action_t action) override;

    /* Value change callback accessor */
    int initialise(const std::string &name,
                   const std::string &fq_name) override;
    GpiCbHdl *register_value_change_callback(int edge, int (*function)(void *),
                                             void *cb_data) override;

  private:
    int set_signal_value(s_vpi_value value, gpi_set_action_t action);

    VpiValueCbHdl m_rising_cb;
    VpiValueCbHdl m_falling_cb;
    VpiValueCbHdl m_either_cb;
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
            LOG_WARN("vpi_iterate returned NULL for type %d for object %s(%d)",
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

class VpiImpl : public GpiImplInterface {
  public:
    VpiImpl(const std::string &name)
        : GpiImplInterface(name),
          m_read_write(this),
          m_next_phase(this),
          m_read_only(this) {}

    /* Sim related */
    void sim_end(void) override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierarchy related */
    GpiObjHdl *get_root_handle(const char *name) override;
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                gpi_iterator_sel_t type) override;
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
    int deregister_callback(GpiCbHdl *obj_hdl) override;
    GpiObjHdl *native_check_create(const std::string &name,
                                   GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(int32_t index, GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(void *raw_hdl, GpiObjHdl *parent) override;
    const char *reason_to_string(int reason) override;
    GpiObjHdl *create_gpi_obj_from_handle(vpiHandle new_hdl,
                                          const std::string &name,
                                          const std::string &fq_name);

  private:
    /* Singleton callbacks */
    VpiReadWriteCbHdl m_read_write;
    VpiNextPhaseCbHdl m_next_phase;
    VpiReadOnlyCbHdl m_read_only;
};

#endif /*COCOTB_VPI_IMPL_H_  */
