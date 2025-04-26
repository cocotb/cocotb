// Copyright cocotb contributors
// Copyright (c) 2014 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef COCOTB_FLI_IMPL_H_
#define COCOTB_FLI_IMPL_H_

#include <map>
#include <vector>

#include "../gpi/gpi_priv.h"
#include "_vendor/fli/mti.h"
#include "exports.h"
#include "gpi.h"

#ifdef COCOTBFLI_EXPORTS
#define COCOTBFLI_EXPORT COCOTB_EXPORT
#else
#define COCOTBFLI_EXPORT COCOTB_IMPORT
#endif

class FliImpl;
class FliSignalObjHdl;

class FliCbHdl : public GpiCbHdl {
  public:
    using GpiCbHdl::GpiCbHdl;
};

// In FLI some callbacks require us to register a process
// We use a subclass to track the process state related to the callback
class FliProcessCbHdl : public FliCbHdl {
  public:
    FliProcessCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) {}

    void set_mti_proc(mtiProcessIdT mti_proc) noexcept {
        m_proc_hdl = mti_proc;
    }

    virtual void release() = 0;

  protected:
    mtiProcessIdT m_proc_hdl;
};

/** Maintains a cache of FliProcessCbHdl objects which can be reused.
 *
 * MTI Processes cannot be destroyed. So we never delete FliProcessCbHdl objects
 * and their MTI Processes and instead reuse them to prevent runaway leaks.
 *
 * We use the queue with LIFO behavior so recently used objects are reused first
 * leveraging cache locality.
 */
template <typename FliProcessCbHdlType, int priority>
class FliProcessCbHdlCache {
  public:
    FliProcessCbHdlCache(FliImpl *impl) : m_impl(impl) {}

    FliProcessCbHdlType *acquire() {
        void handle_fli_callback(void *);

        if (!free_list.empty()) {
            FliProcessCbHdlType *cb_hdl = free_list.back();
            free_list.pop_back();
            return cb_hdl;
        } else {
            auto cb_hdl = new FliProcessCbHdlType(m_impl);
            auto mti_proc = mti_CreateProcessWithPriority(
                nullptr, handle_fli_callback, cb_hdl,
                (mtiProcessPriorityT)priority);
            cb_hdl->set_mti_proc(mti_proc);
            return cb_hdl;
        }
    }
    void release(FliProcessCbHdlType *cb_hdl) { free_list.push_back(cb_hdl); }

  private:
    FliImpl *m_impl;
    std::vector<FliProcessCbHdlType *> free_list;
};

class FliSignalCbHdl : public FliProcessCbHdl {
  public:
    using FliProcessCbHdl::FliProcessCbHdl;

    /** Set the signal and edge used by arm()
     *
     * MUST BE CALLED BEFORE arm()!
     */
    void set_signal_and_edge(FliSignalObjHdl *signal, gpi_edge edge) noexcept {
        m_signal = signal;
        m_edge = edge;
    };
    int arm() override;
    int run() override;
    int remove() override;
    void release() override;

  private:
    FliSignalObjHdl *m_signal;
    gpi_edge m_edge;
};

class FliSimPhaseCbHdl : public FliProcessCbHdl {
  public:
    using FliProcessCbHdl::FliProcessCbHdl;
    int arm() override;
    int run() override;
    int remove() override;

  private:
    bool m_removed;
};

class FliReadWriteCbHdl : public FliSimPhaseCbHdl {
  public:
    using FliSimPhaseCbHdl::FliSimPhaseCbHdl;
    void release() override;
};

class FliNextPhaseCbHdl : public FliSimPhaseCbHdl {
  public:
    using FliSimPhaseCbHdl::FliSimPhaseCbHdl;
    void release() override;
};

class FliReadOnlyCbHdl : public FliSimPhaseCbHdl {
  public:
    using FliSimPhaseCbHdl::FliSimPhaseCbHdl;
    void release() override;
};

class FliStartupCbHdl : public FliCbHdl {
  public:
    FliStartupCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) {}

    int arm() override;
    int run() override;
    int remove() override;
};

class FliShutdownCbHdl : public FliCbHdl {
  public:
    FliShutdownCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) {}

    int arm() override;
    int run() override;
    int remove() override;
};

class FliTimedCbHdl : public FliProcessCbHdl {
  public:
    using FliProcessCbHdl::FliProcessCbHdl;

    /** Set the time used by arm()
     *
     * MUST BE CALLED BEFORE arm()!
     */
    void set_time(uint64_t time) noexcept { m_time = time; }
    int arm() override;
    int run() override;
    int remove() override;
    void release() override;

  private:
    uint64_t m_time;
    bool m_removed;
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
    FliObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
              int acc_type, int acc_full_type, bool is_const = false)
        : GpiObjHdl(impl, hdl, objtype, is_const),
          FliObj(acc_type, acc_full_type) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class FliSignalObjHdl : public GpiSignalObjHdl, public FliObj {
  public:
    FliSignalObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
                    bool is_const, int acc_type, int acc_full_type, bool is_var)
        : GpiSignalObjHdl(impl, hdl, objtype, is_const),
          FliObj(acc_type, acc_full_type),
          m_is_var(is_var) {}

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
    GpiCbHdl *register_value_change_callback(gpi_edge edge,
                                             int (*function)(void *),
                                             void *cb_data) override;

    bool is_variable() { return m_is_var; }

  protected:
    bool m_is_var;
};

class FliValueObjHdl : public FliSignalObjHdl {
  public:
    FliValueObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
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

    int set_signal_value(int32_t value, gpi_set_action action) override;
    int set_signal_value(double value, gpi_set_action action) override;
    int set_signal_value_str(std::string &value,
                             gpi_set_action action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action action) override;

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
    FliEnumObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
                  bool is_const, int acc_type, int acc_full_type, bool is_var,
                  mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    const char *get_signal_value_str() override;
    long get_signal_value_long() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    char **m_value_enum = nullptr;  // Do Not Free
    mtiInt32T m_num_enum = 0;
};

class FliLogicObjHdl : public FliValueObjHdl {
  public:
    FliLogicObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
                   bool is_const, int acc_type, int acc_full_type, bool is_var,
                   mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    ~FliLogicObjHdl() override {
        if (m_mti_buff != NULL) delete[] m_mti_buff;
    }

    const char *get_signal_value_binstr() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action action) override;
    int set_signal_value_binstr(std::string &value,
                                gpi_set_action action) override;

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
    FliIntObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
                 bool is_const, int acc_type, int acc_full_type, bool is_var,
                 mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    const char *get_signal_value_binstr() override;
    long get_signal_value_long() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(int32_t value, gpi_set_action action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;
};

class FliRealObjHdl : public FliValueObjHdl {
  public:
    FliRealObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
                  bool is_const, int acc_type, int acc_full_type, bool is_var,
                  mtiTypeIdT valType, mtiTypeKindT typeKind)
        : FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type,
                         is_var, valType, typeKind) {}

    ~FliRealObjHdl() override {
        if (m_mti_buff != NULL) delete m_mti_buff;
    }

    double get_signal_value_real() override;

    using FliValueObjHdl::set_signal_value;
    int set_signal_value(double value, gpi_set_action action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    double *m_mti_buff = nullptr;
};

class FliStringObjHdl : public FliValueObjHdl {
  public:
    FliStringObjHdl(GpiImplInterface *impl, void *hdl, gpi_objtype objtype,
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
                             gpi_set_action action) override;

    int initialise(const std::string &name,
                   const std::string &fq_name) override;

  private:
    char *m_mti_buff = nullptr;
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
          m_timer_cache(this),
          m_value_change_cache(this),
          m_read_write_cache(this),
          m_read_only_cache(this),
          m_next_phase_cache(this) {}

    /* Sim related */
    void sim_end() override;
    void get_sim_time(uint32_t *high, uint32_t *low) override;
    void get_sim_precision(int32_t *precision) override;
    const char *get_simulator_product() override;
    const char *get_simulator_version() override;

    /* Hierarchy related */
    GpiObjHdl *native_check_create(const std::string &name,
                                   GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(int32_t index, GpiObjHdl *parent) override;
    GpiObjHdl *native_check_create(void *raw_hdl, GpiObjHdl *parent) override;
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

    /* Method to provide strings from operation types */
    const char *reason_to_string(int reason) override;

    /* Method to provide strings from operation types */
    GpiObjHdl *create_gpi_obj_from_handle(void *hdl, const std::string &name,
                                          const std::string &fq_name,
                                          int accType, int accFullType);

    static bool compare_generate_labels(const std::string &a,
                                        const std::string &b);

    void main() noexcept;

  private:
    bool isValueConst(int kind);
    bool isValueLogic(mtiTypeIdT type);
    bool isValueChar(mtiTypeIdT type);
    bool isValueBoolean(mtiTypeIdT type);
    bool isTypeValue(int type);
    bool isTypeSignal(int type, int full_type);

  private:
    // We store the shutdown callback handle here so sim_end() can remove() it
    // if it's called.
    FliShutdownCbHdl *m_sim_finish_cb;

    // Caches for each type of callback handle. This must be associated with the
    // FliImpl rather than be static member of the callback handle type because
    // each callback handle is associated with an FliImpl.
    // TODO remove the FliImpl association from the callback handle types then
    // move these to static fields in the callback handle types.
    FliProcessCbHdlCache<FliTimedCbHdl, MTI_PROC_IMMEDIATE> m_timer_cache;
    FliProcessCbHdlCache<FliSignalCbHdl, MTI_PROC_NORMAL> m_value_change_cache;
    FliProcessCbHdlCache<FliReadWriteCbHdl, MTI_PROC_SYNCH> m_read_write_cache;
    FliProcessCbHdlCache<FliReadOnlyCbHdl, MTI_PROC_POSTPONED>
        m_read_only_cache;
    FliProcessCbHdlCache<FliNextPhaseCbHdl, MTI_PROC_IMMEDIATE>
        m_next_phase_cache;
    friend FliSignalObjHdl;
    friend FliTimedCbHdl;
    friend FliSignalCbHdl;
    friend FliReadWriteCbHdl;
    friend FliReadOnlyCbHdl;
    friend FliNextPhaseCbHdl;
};

#endif /*COCOTB_FLI_IMPL_H_ */
