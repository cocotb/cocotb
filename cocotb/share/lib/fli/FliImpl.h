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
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#ifndef COCOTB_FLI_IMPL_H_
#define COCOTB_FLI_IMPL_H_

#include "../gpi/gpi_priv.h"
#include "mti.h"

#include <queue>
#include <map>

extern "C" {
void cocotb_init();
void handle_fli_callback(void *data);
}

class FliImpl;
class FliSignalObjHdl;

// Callback handles

// In FLI some callbacks require us to register a process
// We use a subclass to track the process state related to the callback
class FliProcessCbHdl : public virtual GpiCbHdl {
public:
    FliProcessCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                              m_proc_hdl(NULL),
                                              m_sensitised(false) { }
    virtual ~FliProcessCbHdl() { }

    virtual int arm_callback() = 0;
    virtual int cleanup_callback();

protected:
    mtiProcessIdT       m_proc_hdl;
    bool                m_sensitised;
};

// One class of callbacks uses mti_Sensitize to react to a signal
class FliSignalCbHdl : public FliProcessCbHdl, public GpiValueCbHdl {

public:
    FliSignalCbHdl(GpiImplInterface *impl,
                   FliSignalObjHdl *sig_hdl,
                   unsigned int edge);

    virtual ~FliSignalCbHdl() { }
    int arm_callback();
    int cleanup_callback() {
        return FliProcessCbHdl::cleanup_callback();
    }

private:
    mtiSignalIdT        m_sig_hdl;
};

// All other callbacks are related to the simulation phasing
class FliSimPhaseCbHdl : public FliProcessCbHdl {

public:
    FliSimPhaseCbHdl(GpiImplInterface *impl, mtiProcessPriorityT priority) : GpiCbHdl(impl),
                                                                             FliProcessCbHdl(impl),
                                                                             m_priority(priority) { }
    virtual ~FliSimPhaseCbHdl() { }

    int arm_callback();

protected:
    mtiProcessPriorityT         m_priority;
};

// FIXME templates?
class FliReadWriteCbHdl : public FliSimPhaseCbHdl {
public:
    FliReadWriteCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                FliSimPhaseCbHdl(impl, MTI_PROC_SYNCH) { }
    virtual ~FliReadWriteCbHdl() { }
};

class FliNextPhaseCbHdl : public FliSimPhaseCbHdl {
public:
    FliNextPhaseCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                FliSimPhaseCbHdl(impl, MTI_PROC_IMMEDIATE) { }
    virtual ~FliNextPhaseCbHdl() { }
};

class FliReadOnlyCbHdl : public FliSimPhaseCbHdl {
public:
    FliReadOnlyCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                               FliSimPhaseCbHdl(impl, MTI_PROC_POSTPONED) { }
    virtual ~FliReadOnlyCbHdl() { }
};

class FliStartupCbHdl : public FliProcessCbHdl {
public:
    FliStartupCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                              FliProcessCbHdl(impl) { }
    virtual ~FliStartupCbHdl() { }

    int arm_callback();
    int run_callback();
};

class FliShutdownCbHdl : public FliProcessCbHdl {
public:
    FliShutdownCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                               FliProcessCbHdl(impl) { }
    virtual ~FliShutdownCbHdl() { }

    int arm_callback();
    int run_callback();
};

class FliTimedCbHdl : public FliProcessCbHdl {
public:
    FliTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps);
    virtual ~FliTimedCbHdl() { }

    int arm_callback();
    void reset_time(uint64_t new_time) {
        m_time_ps = new_time;
    }
    int cleanup_callback();
private:
    uint64_t m_time_ps;
};


// Object Handles
class FliObj {
public:
    FliObj(int acc_type,
           int acc_full_type) :
               m_acc_type(acc_type),
               m_acc_full_type(acc_full_type) { }

    virtual ~FliObj() { }

    int get_acc_type() { return m_acc_type; }
    int get_acc_full_type() { return m_acc_full_type; }


protected:
    int m_acc_type;
    int m_acc_full_type;
};

class FliObjHdl : public GpiObjHdl, public FliObj {
public:
    FliObjHdl(GpiImplInterface *impl,
              void *hdl,
              gpi_objtype_t objtype,
              int acc_type,
              int acc_full_type) :
                  GpiObjHdl(impl, hdl, objtype, false),
                  FliObj(acc_type, acc_full_type) { }

    FliObjHdl(GpiImplInterface *impl,
              void *hdl,
              gpi_objtype_t objtype,
              int acc_type,
              int acc_full_type,
              bool is_const) :
                  GpiObjHdl(impl, hdl, objtype, is_const),
                  FliObj(acc_type, acc_full_type) { }

    virtual ~FliObjHdl() { }

    virtual int initialise(std::string &name, std::string &fq_name);
};

class FliSignalObjHdl : public GpiSignalObjHdl, public FliObj {
public:
    FliSignalObjHdl(GpiImplInterface *impl,
                    void *hdl,
                    gpi_objtype_t objtype,
                    bool is_const,
                    int acc_type,
                    int acc_full_type,
                    bool is_var) :
                        GpiSignalObjHdl(impl, hdl, objtype, is_const),
                        FliObj(acc_type, acc_full_type),
                        m_is_var(is_var),
                        m_rising_cb(impl, this, GPI_RISING),
                        m_falling_cb(impl, this, GPI_FALLING),
                        m_either_cb(impl, this, GPI_FALLING | GPI_RISING) { }

    virtual ~FliSignalObjHdl() { }

    virtual GpiCbHdl *value_change_cb(unsigned int edge);
    virtual int initialise(std::string &name, std::string &fq_name);

    bool is_var() { return m_is_var; }

protected:
    bool               m_is_var;
    FliSignalCbHdl     m_rising_cb;
    FliSignalCbHdl     m_falling_cb;
    FliSignalCbHdl     m_either_cb;
};

class FliValueObjHdl : public FliSignalObjHdl {
public:
    FliValueObjHdl(GpiImplInterface *impl,
                   void *hdl,
                   gpi_objtype_t objtype,
                   bool is_const,
                   int acc_type,
                   int acc_full_type,
                   bool is_var,
                   mtiTypeIdT valType,
                   mtiTypeKindT typeKind) :
                       FliSignalObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type, is_var),
                       m_fli_type(typeKind),
                       m_val_type(valType),
                       m_val_buff(NULL),
                       m_sub_hdls(NULL) { }

    virtual ~FliValueObjHdl() {
        if (m_val_buff != NULL)
            free(m_val_buff);
        if (m_sub_hdls != NULL)
            mti_VsimFree(m_sub_hdls);
    }

    virtual const char* get_signal_value_binstr();
    virtual const char* get_signal_value_str();
    virtual double get_signal_value_real();
    virtual long get_signal_value_long();

    virtual int set_signal_value(const long value);
    virtual int set_signal_value(const double value);
    virtual int set_signal_value(std::string &value);

    virtual void *get_sub_hdl(int index);

    virtual int initialise(std::string &name, std::string &fq_name);

    mtiTypeKindT get_fli_typekind() { return m_fli_type; }
    mtiTypeIdT   get_fli_typeid() { return m_val_type; }

protected:
    mtiTypeKindT       m_fli_type;
    mtiTypeIdT         m_val_type;
    char              *m_val_buff;
    void             **m_sub_hdls;
};

class FliEnumObjHdl : public FliValueObjHdl {
public:
    FliEnumObjHdl(GpiImplInterface *impl,
                  void *hdl,
                  gpi_objtype_t objtype,
                  bool is_const,
                  int acc_type,
                  int acc_full_type,
                  bool is_var,
                  mtiTypeIdT valType,
                  mtiTypeKindT typeKind) :
                      FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type, is_var, valType, typeKind),
                      m_value_enum(NULL),
                      m_num_enum(0) { }

    virtual ~FliEnumObjHdl() { }

    const char* get_signal_value_str();
    long get_signal_value_long();

    int set_signal_value(const long value);

    int initialise(std::string &name, std::string &fq_name);

private:
    char             **m_value_enum;    // Do Not Free
    mtiInt32T          m_num_enum;
};

class FliLogicObjHdl : public FliValueObjHdl {
public:
    FliLogicObjHdl(GpiImplInterface *impl,
                   void *hdl,
                   gpi_objtype_t objtype,
                   bool is_const,
                   int acc_type,
                   int acc_full_type,
                   bool is_var, 
                   mtiTypeIdT valType,
                   mtiTypeKindT typeKind) :
                       FliValueObjHdl(impl,
                                      hdl,
                                      objtype,
                                      is_const,
                                      acc_type,
                                      acc_full_type,
                                      is_var,
                                      valType,
                                      typeKind),
                       m_mti_buff(NULL),
                       m_value_enum(NULL),
                       m_num_enum(0),
                       m_enum_map() { }

    virtual ~FliLogicObjHdl() {
        if (m_mti_buff != NULL)
            free(m_mti_buff);
    }

    const char* get_signal_value_binstr();

    int set_signal_value(const long value);
    int set_signal_value(std::string &value);

    int initialise(std::string &name, std::string &fq_name);


private:
    char                      *m_mti_buff;
    char                     **m_value_enum;    // Do Not Free
    mtiInt32T                  m_num_enum;
    std::map<char,mtiInt32T>   m_enum_map;
};

class FliIntObjHdl : public FliValueObjHdl {
public:
    FliIntObjHdl(GpiImplInterface *impl,
                 void *hdl,
                 gpi_objtype_t objtype,
                 bool is_const,
                 int acc_type,
                 int acc_full_type,
                 bool is_var,
                 mtiTypeIdT valType,
                 mtiTypeKindT typeKind) :
                     FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type, is_var, valType, typeKind) { }

    virtual ~FliIntObjHdl() { }

    const char* get_signal_value_binstr();
    long get_signal_value_long();

    int set_signal_value(const long value);

    int initialise(std::string &name, std::string &fq_name);
};

class FliRealObjHdl : public FliValueObjHdl {
public:
    FliRealObjHdl(GpiImplInterface *impl,
                  void *hdl,
                  gpi_objtype_t objtype,
                  bool is_const,
                  int acc_type,
                  int acc_full_type,
                  bool is_var,
                  mtiTypeIdT valType,
                  mtiTypeKindT typeKind) :
                      FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type, is_var, valType, typeKind),
                      m_mti_buff(NULL) { }

    virtual ~FliRealObjHdl() {
        if (m_mti_buff != NULL)
            free(m_mti_buff);
    }

    double get_signal_value_real();

    int set_signal_value(const double value);

    int initialise(std::string &name, std::string &fq_name);

private:
    double *m_mti_buff;
};

class FliStringObjHdl : public FliValueObjHdl {
public:
    FliStringObjHdl(GpiImplInterface *impl,
                  void *hdl,
                  gpi_objtype_t objtype,
                  bool is_const,
                  int acc_type,
                  int acc_full_type,
                  bool is_var,
                  mtiTypeIdT valType,
                  mtiTypeKindT typeKind) :
                      FliValueObjHdl(impl, hdl, objtype, is_const, acc_type, acc_full_type, is_var, valType, typeKind),
                      m_mti_buff(NULL) { }

    virtual ~FliStringObjHdl() {
        if (m_mti_buff != NULL)
            free(m_mti_buff);
    }

    const char* get_signal_value_str();

    int set_signal_value(std::string &value);

    int initialise(std::string &name, std::string &fq_name);

private:
    char *m_mti_buff;
};

class FliTimerCache {
public:
    FliTimerCache(FliImpl* impl) : impl(impl) { }
    ~FliTimerCache() { }

    FliTimedCbHdl* get_timer(uint64_t time_ps);
    void put_timer(FliTimedCbHdl*);

private:
    std::queue<FliTimedCbHdl*> free_list;
    FliImpl *impl;
};

class FliIterator : public GpiIterator {
public:
    enum OneToMany {
        OTM_END = 0,
        OTM_CONSTANTS,  // include Generics
        OTM_SIGNALS,
        OTM_REGIONS,
        OTM_SIGNAL_SUB_ELEMENTS,
        OTM_VARIABLE_SUB_ELEMENTS
    };

    FliIterator(GpiImplInterface *impl, GpiObjHdl *hdl);

    virtual ~FliIterator() { };

    Status next_handle(std::string &name, GpiObjHdl **hdl, void **raw_hdl);

private:
    void populate_handle_list(OneToMany childType);

private:
    static GpiIteratorMapping<int, OneToMany> iterate_over;      /* Possible mappings */
    std::vector<OneToMany> *selected;                            /* Mapping currently in use */
    std::vector<OneToMany>::iterator one2many;

    std::vector<void *> m_vars;
    std::vector<void *> m_sigs;
    std::vector<void *> m_regs;
    std::vector<void *> *m_currentHandles;
    std::vector<void *>::iterator m_iterator;
};

class FliImpl : public GpiImplInterface {
public:
    FliImpl(const std::string& name) : GpiImplInterface(name),
                                       cache(this),
                                       m_readonly_cbhdl(this),
                                       m_nexttime_cbhdl(this),
                                       m_readwrite_cbhdl(this) { }

     /* Sim related */
    void sim_end();
    void get_sim_time(uint32_t *high, uint32_t *low);
    void get_sim_precision(int32_t *precision);

    /* Hierachy related */
    GpiObjHdl* native_check_create(std::string &name, GpiObjHdl *parent);
    GpiObjHdl* native_check_create(int32_t index, GpiObjHdl *parent);
    GpiObjHdl* native_check_create(void *raw_hdl, GpiObjHdl *paret);
    GpiObjHdl *get_root_handle(const char *name);
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl, gpi_iterator_sel_t type);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time_ps);
    GpiCbHdl *register_readonly_callback();
    GpiCbHdl *register_nexttime_callback();
    GpiCbHdl *register_readwrite_callback();
    int deregister_callback(GpiCbHdl *obj_hdl);

    /* Method to provide strings from operation types */
    const char *reason_to_string(int reason);

    /* Method to provide strings from operation types */
    GpiObjHdl *create_gpi_obj_from_handle(void *hdl, std::string &name, std::string &fq_name, int accType, int accFullType);

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
    FliReadOnlyCbHdl  m_readonly_cbhdl;
    FliNextPhaseCbHdl m_nexttime_cbhdl;
    FliReadWriteCbHdl m_readwrite_cbhdl;
};

#endif /*COCOTB_FLI_IMPL_H_ */
