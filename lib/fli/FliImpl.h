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

// Callback handles

// In FLI some callbacks require us to register a process
// We use a subclass to track the process state related to the callback
class FliProcessCbHdl : public virtual GpiCbHdl {
public:
    FliProcessCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                              m_proc_hdl(NULL),
                                              m_sensitised(false) { }
    virtual ~FliProcessCbHdl() { }

    virtual int arm_callback(void) = 0;
    virtual int cleanup_callback(void);

protected:
    mtiProcessIdT       m_proc_hdl;
    bool                m_sensitised;
};

class FliSignalObjHdl;
// One class of callbacks uses mti_Sensitize to react to a signal
class FliSignalCbHdl : public FliProcessCbHdl, public GpiValueCbHdl {

public:
    FliSignalCbHdl(GpiImplInterface *impl,
                   FliSignalObjHdl *sig_hdl,
                   unsigned int edge);

    virtual ~FliSignalCbHdl() { }
    int arm_callback(void);
    int cleanup_callback(void) { 
        return FliProcessCbHdl::cleanup_callback();
    }

private:
    mtiSignalIdT        m_sig_hdl;
};

class FliSignalObjHdl : public GpiSignalObjHdl {
public:
    FliSignalObjHdl(GpiImplInterface *impl, mtiSignalIdT hdl) : GpiSignalObjHdl(impl, hdl),
                                                                m_fli_hdl(hdl),
                                                                m_rising_cb(impl, this, GPI_RISING),
                                                                m_falling_cb(impl, this, GPI_FALLING),
                                                                m_either_cb(impl, this, GPI_FALLING | GPI_RISING),
                                                                m_type(MTI_TYPE_SCALAR),
                                                                m_mti_buff(NULL),
                                                                m_val_buff(NULL),
                                                                m_val_len(0) { }
    virtual ~FliSignalObjHdl() {
        if (m_val_len)
            free(m_val_buff);
        if (m_mti_buff)
            free(m_mti_buff);
    }

    const char* get_signal_value_binstr(void);
    int set_signal_value(const int value);
    int set_signal_value(std::string &value);
    int initialise(std::string &name);
    GpiCbHdl *value_change_cb(unsigned int edge);

protected:
    mtiSignalIdT       m_fli_hdl;
    FliSignalCbHdl     m_rising_cb;
    FliSignalCbHdl     m_falling_cb;
    FliSignalCbHdl     m_either_cb;

private:
    mtiTypeKindT       m_type;
    mtiInt32T         *m_mti_buff;
    char              *m_val_buff;
    int                m_val_len;
};


// All other callbacks are related to the simulation phasing
class FliSimPhaseCbHdl : public FliProcessCbHdl {

public:
    FliSimPhaseCbHdl(GpiImplInterface *impl, mtiProcessPriorityT priority) : GpiCbHdl(impl),
                                                                             FliProcessCbHdl(impl),
                                                                             m_priority(priority) { }
    virtual ~FliSimPhaseCbHdl() { }

    int arm_callback(void);

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

class FliShutdownCbHdl : public GpiCbHdl {
public:
    FliShutdownCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl) { }
    int run_callback(void);
    int arm_callback(void);
    virtual ~FliShutdownCbHdl() { }
};


class FliRegionObjHdl : public GpiObjHdl {
public:
    FliRegionObjHdl(GpiImplInterface *impl, mtiRegionIdT hdl) : GpiObjHdl(impl),
                                                                m_fli_hdl(hdl) { }
    virtual ~FliRegionObjHdl() { }

protected:
     mtiRegionIdT m_fli_hdl;
};

class FliImpl;
class FliTimedCbHdl;
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


class FliImpl : public GpiImplInterface {
public:
    FliImpl(const std::string& name) : GpiImplInterface(name),
                                       m_readonly_cbhdl(this),
                                       m_nexttime_cbhdl(this),
                                       m_readwrite_cbhdl(this),
                                       cache(this) { }

     /* Sim related */
    void sim_end(void);
    void get_sim_time(uint32_t *high, uint32_t *low);

    /* Hierachy related */
    GpiObjHdl* native_check_create(std::string &name, GpiObjHdl *parent);
    GpiObjHdl* native_check_create(uint32_t index, GpiObjHdl *parent);
    GpiObjHdl *get_root_handle(const char *name);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time_ps);
    GpiCbHdl *register_readonly_callback(void);
    GpiCbHdl *register_nexttime_callback(void);
    GpiCbHdl *register_readwrite_callback(void);
    int deregister_callback(GpiCbHdl *obj_hdl);

    /* Method to provide strings from operation types */
    const char *reason_to_string(int reason);

private:
    FliReadOnlyCbHdl  m_readonly_cbhdl;
    FliNextPhaseCbHdl m_nexttime_cbhdl;
    FliReadWriteCbHdl m_readwrite_cbhdl;
public:
    FliTimerCache cache;

};

class FliTimedCbHdl : public FliProcessCbHdl {
public:
    FliTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps);
    virtual ~FliTimedCbHdl() { }

    int arm_callback(void);
    void reset_time(uint64_t new_time) {
        m_time_ps = new_time;
    }
    int cleanup_callback(void);
private:
    uint64_t m_time_ps;
};

#endif /*COCOTB_FLI_IMPL_H_ */
