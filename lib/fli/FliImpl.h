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
#include <mti.h>



class FliImpl : public GpiImplInterface {
public:
    FliImpl(const std::string& name) : GpiImplInterface(name) { }

     /* Sim related */
    void sim_end(void);
    void get_sim_time(uint32_t *high, uint32_t *low);

    /* Hierachy related */
    GpiObjHdl *get_root_handle(const char *name);

    GpiCbHdl *register_timed_callback(uint64_t time_ps);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_readonly_callback(void);
    GpiCbHdl *register_nexttime_callback(void);
    GpiCbHdl *register_readwrite_callback(void);
    int deregister_callback(GpiCbHdl *obj_hdl);
    bool native_check(std::string &name, GpiObjHdl *parent);

private:
    GpiCbHdl m_readonly_cbhdl;
    GpiCbHdl m_nexttime_cbhdl;
    GpiCbHdl m_readwrite_cbhdl;

};

class FliObjHdl : public GpiObjHdl {
public:
    FliObjHdl(GpiImplInterface *impl, mtiRegionIdT hdl) : GpiObjHdl(impl),
                                                          fli_hdl(hdl) { }
    virtual ~FliObjHdl() { }

    virtual GpiObjHdl *get_handle_by_name(std::string &name);
    virtual GpiObjHdl *get_handle_by_index(uint32_t index);
    virtual GpiIterator *iterate_handle(uint32_t type) { return NULL ;}
    virtual GpiObjHdl *next_handle(GpiIterator *iterator) { return NULL; }

    const char* get_name_str(void);
    const char* get_type_str(void);

protected:
     mtiRegionIdT fli_hdl;

};

class FliCbHdl : public GpiCbHdl {
public:
    FliCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl) { }
    virtual ~FliCbHdl() { }

    virtual int arm_callback(void);
    virtual int cleanup_callback(void);

protected:
    int register_cb(p_cb_data cb_data);
};


// In FLI some callbacks require us to register a process
// We use a subclass to track the process state related to the callback
class FliProcessCbHdl : public FliCbHdl {

public:
    FliCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                       m_proc_hdl(NULL) { }
    virtual ~FliCbHdl() { }

    virtual int arm_callback(void);
    virtual int cleanup_callback(void);

private:
    mtiProcessIdt       m_proc_hdl;
    bool                m_sensitised;
}


class FliSignalObjHdl : public GpiSignalObjHdl {
public:
    FliSignalObjHdl(GpiImplInterface *impl) : GpiSignalObjHdl(impl) { }
    virtual ~FliSignalObjHdl() { }

    virtual int set_signal_value(const int value);
    virtual int set_signal_value(const char *str);

    virtual GpiCbHdl *rising_edge_cb(void);
    virtual GpiCbHdl *falling_edge_cb(void);
    virtual GpiCbHdl *value_change_cb(void);

private:
    mtiSignalIdt  fli_hdl;

};

class FliTimedCbHdl : public FliCbHdl {
public:
    FliTimedCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) { }
    int arm_callback(uint64_t time_ps);
    virtual ~FliTimedCbHdl() { }
};

class FliStartupCbHdl : public FliCbHdl {
public:
    FliStartupCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) { }
    int run_callback(void);
    int arm_callback(void);
    virtual ~FliStartupCbHdl() { }
};

class FliShutdownCbHdl : public FliCbHdl {
public:
    FliShutdownCbHdl(GpiImplInterface *impl) : FliCbHdl(impl) { }
    int run_callback(void);
    int arm_callback(void);
    virtual ~FliShutdownCbHdl() { }
};

#endif /*COCOTB_FLI_IMPL_H_  */
