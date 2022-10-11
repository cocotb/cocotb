/******************************************************************************
 * Copyright (c) 2013 Potential Ventures Ltd
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

#ifndef COCOTB_VHPI_IMPL_H_
#define COCOTB_VHPI_IMPL_H_

#include <exports.h>
#ifdef COCOTBVHPI_EXPORTS
#define COCOTBVHPI_EXPORT COCOTB_EXPORT
#else
#define COCOTBVHPI_EXPORT COCOTB_IMPORT
#endif

#include <vhpi_user_ext.h>

#include <map>
#include <vector>

#include "../gpi/gpi_priv.h"
#include "_vendor/vhpi/vhpi_user.h"

// Define Index separator
#ifdef ALDEC
// Aldec
#define GEN_IDX_SEP_LHS "__"
#define GEN_IDX_SEP_RHS ""
#else
// IUS/Xcelium and Questa
#define GEN_IDX_SEP_LHS "("
#define GEN_IDX_SEP_RHS ")"
#endif

// Should be run after every VHPI call to check error status
static inline int __check_vhpi_error(const char *file, const char *func,
                                     long line) {
    int err_occurred = 0;
#if VHPI_CHECKING
    vhpiErrorInfoT info;
    enum gpi_log_levels loglevel;
    err_occurred = vhpi_check_error(&info);
    if (!err_occurred) return 0;

    switch (info.severity) {
        case vhpiNote:
            loglevel = GPIInfo;
            break;
        case vhpiWarning:
            loglevel = GPIWarning;
            break;
        case vhpiError:
            loglevel = GPIError;
            break;
        case vhpiFailure:
        case vhpiSystem:
        case vhpiInternal:
            loglevel = GPICritical;
            break;
        default:
            loglevel = GPIInfo;
            break;
    }

    gpi_log("gpi", loglevel, file, func, line,
            "VHPI Error level %d: %s\nFILE %s:%d", info.severity, info.message,
            info.file, info.line);

#endif
    return err_occurred;
}

#define check_vhpi_error()                                \
    do {                                                  \
        __check_vhpi_error(__FILE__, __func__, __LINE__); \
    } while (0)

class VhpiCbHdl : public virtual GpiCbHdl {
  public:
    VhpiCbHdl(GpiImplInterface *impl);

    int arm_callback() override;
    int cleanup_callback() override;

  protected:
    vhpiCbDataT cb_data;
    vhpiTimeT vhpi_time;
};

class VhpiSignalObjHdl;

class VhpiValueCbHdl : public VhpiCbHdl, public GpiValueCbHdl {
  public:
    VhpiValueCbHdl(GpiImplInterface *impl, VhpiSignalObjHdl *sig, int edge);
    int cleanup_callback() override { return VhpiCbHdl::cleanup_callback(); }

  private:
    std::string initial_value;
};

class VhpiTimedCbHdl : public VhpiCbHdl {
  public:
    VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time);
    int cleanup_callback() override;
};

class VhpiReadOnlyCbHdl : public VhpiCbHdl {
  public:
    VhpiReadOnlyCbHdl(GpiImplInterface *impl);
};

class VhpiNextPhaseCbHdl : public VhpiCbHdl {
  public:
    VhpiNextPhaseCbHdl(GpiImplInterface *impl);
};

class VhpiStartupCbHdl : public VhpiCbHdl {
  public:
    VhpiStartupCbHdl(GpiImplInterface *impl);
    int run_callback() override;
    int cleanup_callback() override {
        /* Too many simulators get upset with this so we override to do nothing
         */
        return 0;
    }
};

class VhpiShutdownCbHdl : public VhpiCbHdl {
  public:
    VhpiShutdownCbHdl(GpiImplInterface *impl);
    int run_callback() override;
    int cleanup_callback() override {
        /* Too many simulators get upset with this so we override to do nothing
         */
        return 0;
    }
};

class VhpiReadwriteCbHdl : public VhpiCbHdl {
  public:
    VhpiReadwriteCbHdl(GpiImplInterface *impl);
};

class VhpiArrayObjHdl : public GpiObjHdl {
  public:
    VhpiArrayObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                    gpi_objtype_t objtype)
        : GpiObjHdl(impl, hdl, objtype) {}
    ~VhpiArrayObjHdl() override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VhpiObjHdl : public GpiObjHdl {
  public:
    VhpiObjHdl(GpiImplInterface *impl, vhpiHandleT hdl, gpi_objtype_t objtype)
        : GpiObjHdl(impl, hdl, objtype) {}
    ~VhpiObjHdl() override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VhpiSignalObjHdl : public GpiSignalObjHdl {
  public:
    VhpiSignalObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                     gpi_objtype_t objtype, bool is_const)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const),
          m_rising_cb(impl, this, GPI_RISING),
          m_falling_cb(impl, this, GPI_FALLING),
          m_either_cb(impl, this, GPI_FALLING | GPI_RISING) {}
    ~VhpiSignalObjHdl() override;

    const char *get_signal_value_binstr() override;
    const char *get_signal_value_str() override;
    double get_signal_value_real() override;
    long get_signal_value_long() override;

    using GpiSignalObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action_t action) override;
    int set_signal_value(double value, gpi_set_action_t action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action_t action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action_t action) override;

    /* Value change callback accessor */
    GpiCbHdl *value_change_cb(int edge) override;
    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  protected:
    vhpiEnumT chr2vhpi(char value);
    vhpiValueT m_value;
    vhpiValueT m_binvalue;
    VhpiValueCbHdl m_rising_cb;
    VhpiValueCbHdl m_falling_cb;
    VhpiValueCbHdl m_either_cb;
};

class VhpiLogicSignalObjHdl : public VhpiSignalObjHdl {
  public:
    VhpiLogicSignalObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                          gpi_objtype_t objtype, bool is_const)
        : VhpiSignalObjHdl(impl, hdl, objtype, is_const) {}

    using GpiSignalObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action_t action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VhpiIterator : public GpiIterator {
  public:
    VhpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl);

    ~VhpiIterator() override;

    Status next_handle(std::string &name, GpiObjHdl **hdl,
                       void **raw_hdl) override;

  private:
    vhpiHandleT m_iterator;
    vhpiHandleT m_iter_obj;
    static std::map<vhpiClassKindT, std::vector<vhpiOneToManyT>>
        iterate_over;                      /* Possible mappings */
    std::vector<vhpiOneToManyT> *selected; /* Mapping currently in use */
    std::vector<vhpiOneToManyT>::iterator one2many;
};

class VhpiImpl : public GpiImplInterface {
  public:
    VhpiImpl(const std::string &name)
        : GpiImplInterface(name),
          m_read_write(this),
          m_next_phase(this),
          m_read_only(this) {}

    /* Sim related */
    void sim_end() override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierachy related */
    GpiObjHdl *get_root_handle(const char *name) override;
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                gpi_iterator_sel_t type) override;

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time) override;
    GpiCbHdl *register_readonly_callback() override;
    GpiCbHdl *register_nexttime_callback() override;
    GpiCbHdl *register_readwrite_callback() override;
    int deregister_callback(GpiCbHdl *obj_hdl) override;
    GpiObjHdl *native_check_create(std::string &name,
                                   GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(int32_t index, GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(void *raw_hdl, GpiObjHdl *parent) override;

    const char *reason_to_string(int reason) override;
    const char *format_to_string(int format);

    GpiObjHdl *create_gpi_obj_from_handle(vhpiHandleT new_hdl,
                                          const std::string &name,
                                          const std::string &fq_name);

  private:
    VhpiReadwriteCbHdl m_read_write;
    VhpiNextPhaseCbHdl m_next_phase;
    VhpiReadOnlyCbHdl m_read_only;
};

#endif /*COCOTB_VHPI_IMPL_H_  */
