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

#include <map>
#include <vector>

#include "../gpi/gpi_priv.h"
#include "_vendor/vhpi/vhpi_user.h"
#include "exports.h"
#include "gpi.h"

#ifdef COCOTBVHPI_EXPORTS
#define COCOTBVHPI_EXPORT COCOTB_EXPORT
#else
#define COCOTBVHPI_EXPORT COCOTB_IMPORT
#endif

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
    enum gpi_log_level loglevel;
    err_occurred = vhpi_check_error(&info);
    if (!err_occurred) return 0;

    switch (info.severity) {
        case vhpiNote:
            loglevel = GPI_INFO;
            break;
        case vhpiWarning:
            loglevel = GPI_WARNING;
            break;
        case vhpiError:
            loglevel = GPI_ERROR;
            break;
        case vhpiFailure:
        case vhpiSystem:
        case vhpiInternal:
            loglevel = GPI_CRITICAL;
            break;
        default:
            loglevel = GPI_INFO;
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

class VhpiCbHdl : public GpiCbHdl {
  public:
    VhpiCbHdl(GpiImplInterface *impl);

    int arm() override;
    int remove() override;
    int run() override;

  protected:
    vhpiCbDataT cb_data;
    vhpiTimeT vhpi_time;
    bool m_removed = false;
};

class VhpiSignalObjHdl;

class VhpiValueCbHdl : public VhpiCbHdl {
  public:
    VhpiValueCbHdl(GpiImplInterface *impl, VhpiSignalObjHdl *sig,
                   gpi_edge edge);
    int run() override;

  private:
    GpiSignalObjHdl *m_signal;
    gpi_edge m_edge;
};

class VhpiTimedCbHdl : public VhpiCbHdl {
  public:
    VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time);
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

    // Too many sims get upset trying to remove startup callbacks so we just
    // don't try. TODO Is this still accurate?

    int run() override {
        if (!m_removed) {
            m_cb_func(m_cb_data);
        }
        delete this;
        return 0;
    }

    int remove() override {
        m_removed = true;
        return 0;
    }
};

class VhpiShutdownCbHdl : public VhpiCbHdl {
  public:
    VhpiShutdownCbHdl(GpiImplInterface *impl);

    // Too many sims get upset trying to remove startup callbacks so we just
    // don't try. TODO Is this still accurate?

    int run() override {
        if (!m_removed) {
            m_cb_func(m_cb_data);
        }
        delete this;
        return 0;
    }

    int remove() override {
        m_removed = true;
        return 0;
    }
};

class VhpiReadWriteCbHdl : public VhpiCbHdl {
  public:
    VhpiReadWriteCbHdl(GpiImplInterface *impl);
};

class VhpiArrayObjHdl : public GpiObjHdl {
  public:
    VhpiArrayObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                    gpi_objtype objtype)
        : GpiObjHdl(impl, hdl, objtype) {}
    ~VhpiArrayObjHdl() override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VhpiObjHdl : public GpiObjHdl {
  public:
    VhpiObjHdl(GpiImplInterface *impl, vhpiHandleT hdl, gpi_objtype objtype)
        : GpiObjHdl(impl, hdl, objtype) {}
    ~VhpiObjHdl() override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class VhpiSignalObjHdl : public GpiSignalObjHdl {
  public:
    VhpiSignalObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                     gpi_objtype objtype, bool is_const)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const) {}
    ~VhpiSignalObjHdl() override;

    const char *get_signal_value_binstr() override;
    const char *get_signal_value_str() override;
    double get_signal_value_real() override;
    long get_signal_value_long() override;

    using GpiSignalObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action action) override;
    int set_signal_value(double value, gpi_set_action action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action action) override;

    /* Value change callback accessor */
    int initialise(const std::string &name,
                   const std::string &fq_name) override;
    GpiCbHdl *register_value_change_callback(gpi_edge edge,
                                             int (*function)(void *),
                                             void *cb_data) override;

  protected:
    vhpiEnumT chr2vhpi(char value);
    vhpiValueT m_value;
    vhpiValueT m_binvalue;
};

class VhpiLogicSignalObjHdl : public VhpiSignalObjHdl {
  public:
    VhpiLogicSignalObjHdl(GpiImplInterface *impl, vhpiHandleT hdl,
                          gpi_objtype objtype, bool is_const)
        : VhpiSignalObjHdl(impl, hdl, objtype, is_const) {}

    using GpiSignalObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action action) override;

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
    VhpiImpl(const std::string &name) : GpiImplInterface(name) {}

    /* Sim related */
    void sim_end() override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierachy related */
    GpiObjHdl *get_root_handle(const char *name) override;
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                gpi_iterator_sel type) override;

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
    const char *format_to_string(int format);

    GpiObjHdl *create_gpi_obj_from_handle(vhpiHandleT new_hdl,
                                          const std::string &name,
                                          const std::string &fq_name);

    static bool compare_generate_labels(const std::string &a,
                                        const std::string &b);

    /** Entry point for the simulator.
     *
     * Called if this GpiImpl will act as the main simulator entry point.
     * Registers simulator startup and shutdown callbacks, and controls the
     * behavior gpi_sim_end.
     */
    void main() noexcept;

  private:
    // We store the shutdown callback handle here so sim_end() can remove() it
    // if it's called.
    VhpiShutdownCbHdl *m_sim_finish_cb;
};

#endif /*COCOTB_VHPI_IMPL_H_  */
