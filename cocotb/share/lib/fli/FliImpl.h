/******************************************************************************
 * Copyright (c) 2014 Potential Ventures Ltd
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

#ifndef COCOTB_FLI_IMPL_H_
#define COCOTB_FLI_IMPL_H_

#include <exports.h>
#ifdef COCOTBFLI_EXPORTS
#define COCOTBFLI_EXPORT COCOTB_EXPORT
#else
#define COCOTBFLI_EXPORT COCOTB_IMPORT
#endif

#include <map>
#include <queue>

#include "../gpi/gpi_priv.h"
#include "_vendor/fli/mti.h"

extern "C" {
COCOTBFLI_EXPORT void cocotb_init();
void handle_fli_callback(void *data);
}

class FliImpl;
class FliSignalObjHdl;

// Callback handles

// In FLI some callbacks require us to register a process
// We use a subclass to track the process state related to the callback
class FliProcessCbHdl : public virtual GpiCbHdl {
  public:
    FliProcessCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), m_proc_hdl(NULL) {}

    int cleanup_callback() override;

  protected:
    mtiProcessIdT m_proc_hdl;
};

// One class of callbacks uses mti_Sensitize to react to a signal
class FliSignalCbHdl : public FliProcessCbHdl, public GpiValueCbHdl {
  public:
    FliSignalCbHdl(GpiImplInterface *impl, FliSignalObjHdl *sig_hdl, int edge);

    int arm_callback() override;
    int cleanup_callback() override {
        return FliProcessCbHdl::cleanup_callback();
    }

  private:
    mtiSignalIdT m_sig_hdl;
};

// All other callbacks are related to the simulation phasing
class FliSimPhaseCbHdl : public FliProcessCbHdl, public GpiCommonCbHdl {
  public:
    FliSimPhaseCbHdl(GpiImplInterface *impl, mtiProcessPriorityT priority)
        : GpiCbHdl(impl),
          FliProcessCbHdl(impl),
          GpiCommonCbHdl(impl),
          m_priority(priority) {}

    int arm_callback() override;

  protected:
    mtiProcessPriorityT m_priority;
};

// FIXME templates?
class FliReadWriteCbHdl : public FliSimPhaseCbHdl {
  public:
    FliReadWriteCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), FliSimPhaseCbHdl(impl, MTI_PROC_SYNCH) {}
};

class FliNextPhaseCbHdl : public FliSimPhaseCbHdl {
  public:
    FliNextPhaseCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), FliSimPhaseCbHdl(impl, MTI_PROC_IMMEDIATE) {}
};

class FliReadOnlyCbHdl : public FliSimPhaseCbHdl {
  public:
    FliReadOnlyCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), FliSimPhaseCbHdl(impl, MTI_PROC_POSTPONED) {}
};

class FliStartupCbHdl : public FliProcessCbHdl {
  public:
    FliStartupCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), FliProcessCbHdl(impl) {}

    int arm_callback() override;
    int run_callback() override;
};

class FliShutdownCbHdl : public FliProcessCbHdl {
  public:
    FliShutdownCbHdl(GpiImplInterface *impl)
        : GpiCbHdl(impl), FliProcessCbHdl(impl) {}

    int arm_callback() override;
    int run_callback() override;
};

class FliTimedCbHdl : public FliProcessCbHdl, public GpiCommonCbHdl {
  public:
    FliTimedCbHdl(GpiImplInterface *impl, uint64_t time);

    int arm_callback() override;
    void reset_time(uint64_t new_time) { m_time = new_time; }
    int cleanup_callback() override;

  private:
    uint64_t m_time;
};

// Object Handles
class FliObj {
  public:
    FliObj(int acc_type, int acc_full_type)
        : m_acc_type(acc_type), m_acc_full_type(acc_full_type) {}

    virtual ~FliObj() = default;

    int get_acc_type() { return m_acc_type; }
    int get_acc_full_type() { return m_acc_full_type; }

  protected:
    int m_acc_type;
    int m_acc_full_type;
};

class FliObjHdl : public GpiObjHdl, public FliObj {
  public:
    FliObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
              int acc_type, int acc_full_type, bool is_const = false)
        : GpiObjHdl(impl, hdl, objtype, is_const),
          FliObj(acc_type, acc_full_type) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class FliSignalObjHdl : public GpiSignalObjHdl, public FliObj {
  public:
    FliSignalObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                    bool is_const, int acc_type, int acc_full_type, bool is_var)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const),
          FliObj(acc_type, acc_full_type),
          m_is_var(is_var),
          m_rising_cb(impl, this, GPI_RISING),
          m_falling_cb(impl, this, GPI_FALLING),
          m_either_cb(impl, this, GPI_FALLING | GPI_RISING) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
    GpiCbHdl *register_value_change_callback(int edge, int (*function)(void *),
                                             void *cb_data) override;

    bool is_var() { return m_is_var; }

  protected:
    bool m_is_var;
    FliSignalCbHdl m_rising_cb;
    FliSignalCbHdl m_falling_cb;
    FliSignalCbHdl m_either_cb;
};

class FliValueObjHdl : public FliSignalObjHdl {
  public:
    FliValueObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                   bool is_const, int acc_type, int acc_full_type, bool is_var,
                   mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliSignalObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                          is_var),
          m_fli_type(typeKind),
          m_val_type(valType) {}

    ~FliValueObjHdl() override {
        if (m_val_buff != NULL) delete[] m_val_buff;
        if (m_sub_hdls != NULL) mti_VsimFree(m_sub_hdls);
    }

    const char *get_signal_value_binstr() override;
    const char *get_signal_value_str() override;
    double get_signal_value_real() override;
    long get_signal_value_long() override;

    int set_signal_value(int32_t value, gpi_set_action_t action) override;
    int set_signal_value(double value, gpi_set_action_t action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action_t action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action_t action) override;

    void *get_sub_hdl(int index);

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

    mtiTypeKindT get_fli_typekind() { return m_fli_type; }
    mtiTypeIdT get_fli_typeid() { return m_val_type; }

  protected:
    mtiTypeKindT m_fli_type;
    mtiTypeIdT m_val_type;
    char *m_val_buff = nullptr;
    void **m_sub_hdls = nullptr;
};

class FliEnumObjHdl : public FliValueObjHdl {
  public:
    FliEnumObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                  bool is_const, int acc_type, int acc_full_type, bool is_var,
                  mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    const char *get_signal_value_str() override;
    long get_signal_value_long() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    char **m_value_enum = nullptr;  // Do Not Free
    mtiInt32T m_num_enum = 0;
};

class FliLogicObjHdl : public FliValueObjHdl {
  public:
    FliLogicObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                   bool is_const, int acc_type, int acc_full_type, bool is_var,
                   mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    ~FliLogicObjHdl() override {
        if (m_mti_buff != NULL) delete[] m_mti_buff;
    }

    const char *get_signal_value_binstr() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action_t action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    char *m_mti_buff = nullptr;
    char **m_value_enum = nullptr;  // Do Not Free
    mtiInt32T m_num_enum = 0;
    std::map<char, mtiInt32T> m_enum_map;
};

class FliIntObjHdl : public FliValueObjHdl {
  public:
    FliIntObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                 bool is_const, int acc_type, int acc_full_type, bool is_var,
                 mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    const char *get_signal_value_binstr() override;
    long get_signal_value_long() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class FliRealObjHdl : public FliValueObjHdl {
  public:
    FliRealObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                  bool is_const, int acc_type, int acc_full_type, bool is_var,
                  mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    ~FliRealObjHdl() override {
        if (m_mti_buff != NULL) delete m_mti_buff;
    }

    double get_signal_value_real() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(double value, gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    double *m_mti_buff = nullptr;
};

class FliStringObjHdl : public FliValueObjHdl {
  public:
    FliStringObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype_t objtype,
                    bool is_const, int acc_type, int acc_full_type, bool is_var,
                    mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    ~FliStringObjHdl() override {
        if (m_mti_buff != NULL) delete[] m_mti_buff;
    }

    const char *get_signal_value_str() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value_str(std::string &value,
                             gpi_set_action_t action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    char *m_mti_buff = nullptr;
};

/** Maintains a cache of FliTimedCbHdl objects which can be reused.
 *
 * Apparently allocating and freeing Timer callback objects is very expensive
 * compared to anything Python or the simulator are doing.
 */
class FliTimerCache {
  public:
    FliTimerCache(FliImpl *impl) : impl(impl) {}

    FliTimedCbHdl *get_timer(uint64_t time);
    void put_timer(FliTimedCbHdl *);

  private:
    std::queue<FliTimedCbHdl *> free_list;
    FliImpl *impl;
};

class FliIterator : public GpiIterator {
  public:
    enum OneToMany {
        OTM_CONSTANTS,  // include Generics
        OTM_SIGNALS,
        OTM_REGIONS,
        OTM_SIGNAL_SUB_ELEMENTS,
        OTM_VARIABLE_SUB_ELEMENTS
    };

    FliIterator(GpiImplInterface *impl, GpiObjHdl *hdl);

    Status next_handle(std::string &name, GpiObjHdl **hdl,
                       void **raw_hdl) override;

  private:
    void populate_handle_list(OneToMany childType);

  private:
    static std::map<int, std::vector<OneToMany>>
        iterate_over;                 /* Possible mappings */
    std::vector<OneToMany> *selected; /* Mapping currently in use */
    std::vector<OneToMany>::iterator one2many;

    std::vector<void *> m_vars;
    std::vector<void *> m_sigs;
    std::vector<void *> m_regs;
    std::vector<void *> *m_currentHandles;
    std::vector<void *>::iterator m_iterator;
};

class FliImpl : public GpiImplInterface {
  public:
    FliImpl(const std::string &name)
        : GpiImplInterface(name),
          cache(this),
          m_readonly_cbhdl(this),
          m_nexttime_cbhdl(this),
          m_readwrite_cbhdl(this) {}

    /* Sim related */
    void sim_end() override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierachy related */
    GpiObjHdl *native_check_create(const std::string &name,
                                   GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(int32_t index, GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(void *raw_hdl, GpiObjHdl *paret) override;
    GpiObjHdl *get_root_handle(const char *name) override;
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl,
                                gpi_iterator_sel_t type) override;

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

    /* Method to provide strings from operation types */
    const char *reason_to_string(int reason) override;

    /* Method to provide strings from operation types */
    GpiObjHdl *create_gpi_obj_from_handle(void *hdl, const std::string &name,
                                          const std::string &fq_name,
                                          int accType, int accFullType);

  private:
    bool isValueConst(int kind);
    bool isValueLogic(mtiTypeIdT type);
    bool isValueChar(mtiTypeIdT type);
    bool isValueBoolean(mtiTypeIdT type);
    bool isTypeValue(int type);
    bool isTypeSignal(int type, int full_type);

  public:
    FliTimerCache cache;

  private:
    FliReadOnlyCbHdl m_readonly_cbhdl;
    FliNextPhaseCbHdl m_nexttime_cbhdl;
    FliReadWriteCbHdl m_readwrite_cbhdl;
};

#endif /*COCOTB_FLI_IMPL_H_ */
