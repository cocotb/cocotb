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

#ifndef COCOTB_VHPI_IMPL_H_ 
#define COCOTB_VHPI_IMPL_H_ 

#include "../gpi/gpi_priv.h"
#include <vhpi_user.h>

#define VHPI_CHECKING 1

// Should be run after every VHPI call to check error status
static inline int __check_vhpi_error(const char *func, long line)
{
    int level=0;
#if VHPI_CHECKING
    vhpiErrorInfoT info;
    int loglevel;
    level = vhpi_check_error(&info);
    if (level == 0)
        return 0;

    switch (level) {
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
    }

    gpi_log("cocotb.gpi", loglevel, __FILE__, func, line,
            "VHPI Error level %d: %s\nFILE %s:%d",
            info.severity, info.message, info.file, info.line);

#endif
    return level;
}

#define check_vhpi_error() do { \
    __check_vhpi_error(__func__, __LINE__); \
} while (0)

class VhpiImpl : public GpiImplInterface {
public:
    VhpiImpl(const std::string& name) : GpiImplInterface(name) { }

     /* Sim related */
    void sim_end(void);
    void get_sim_time(uint32_t *high, uint32_t *low);

    /* Hierachy related */
    GpiObjHdl *get_root_handle(const char *name);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time_ps);
    GpiCbHdl *register_readonly_callback(void) { return NULL; }
    GpiCbHdl *register_nexttime_callback(void) { return NULL; }
    GpiCbHdl *register_readwrite_callback(void) { return NULL; }
    int deregister_callback(GpiCbHdl *obj_hdl) { return 0; }
    bool native_check(std::string &name, GpiObjHdl *parent) { return false; }
    GpiObjHdl* native_check_create(std::string &name, GpiObjHdl *parent) { return NULL; }
    GpiObjHdl* native_check_create(uint32_t index, GpiObjHdl *parent) { return NULL; }

    const char * reason_to_string(int reason);
};

class VhpiObjHdl : public GpiObjHdl {
public:
    VhpiObjHdl(GpiImplInterface *impl, vhpiHandleT hdl) : GpiObjHdl(impl),
                                                          vhpi_hdl(hdl) { }
    virtual ~VhpiObjHdl() { }

    virtual GpiObjHdl *get_handle_by_name(std::string &name) { return NULL; }
    virtual GpiObjHdl *get_handle_by_index(uint32_t index) { return NULL; }
    virtual GpiIterator *iterate_handle(uint32_t type) { return NULL ;}
    virtual GpiObjHdl *next_handle(GpiIterator *iterator) { return NULL; }

    vhpiHandleT get_handle(void); 

protected:
    vhpiHandleT vhpi_hdl;
};

class VhpiCbHdl : public GpiCbHdl {
public:
    VhpiCbHdl(GpiImplInterface *impl); 
    virtual ~VhpiCbHdl() { }

    virtual int arm_callback(void);
    virtual int cleanup_callback(void);

protected:
    vhpiHandleT vhpi_hdl;
    vhpiCbDataT cb_data;
};

class VhpiSignalObjHdl : public VhpiObjHdl, public GpiSignalObjHdl {
public:
    VhpiSignalObjHdl(GpiImplInterface *impl, vhpiHandleT hdl) : VhpiObjHdl(impl, hdl),
                                                                GpiSignalObjHdl(impl) { }
    virtual ~VhpiSignalObjHdl() { }

    const char* get_signal_value_binstr(void);

    int set_signal_value(const int value);
    int set_signal_value(std::string &value);
    //virtual GpiCbHdl monitor_value(bool rising_edge) = 0; this was for the triggers
    // but the explicit ones are probably better

    // Also think we want the triggers here?
    virtual GpiCbHdl *rising_edge_cb(void) { return NULL; }
    virtual GpiCbHdl *falling_edge_cb(void) { return NULL; }
    virtual GpiCbHdl *value_change_cb(void) { return NULL; }

    /* Functions that I would like to inherit but do not ?*/
    virtual GpiObjHdl *get_handle_by_name(std::string &name) {
        return VhpiObjHdl::get_handle_by_name(name);
    }
    virtual GpiObjHdl *get_handle_by_index(uint32_t index) {
        return VhpiObjHdl::get_handle_by_index(index);
    }
    virtual GpiIterator *iterate_handle(uint32_t type)
    {
        return VhpiObjHdl::iterate_handle(type);
    }
    virtual GpiObjHdl *next_handle(GpiIterator *iterator)
    {
        return VhpiObjHdl::next_handle(iterator);
    }
    virtual int initialise(std::string name) {
        return VhpiObjHdl::initialise(name);
    }
};

class VhpiTimedCbHdl : public VhpiCbHdl {
public:
    VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps);
    virtual ~VhpiTimedCbHdl() { }
private:
    vhpiTimeT vhpi_time;
};

#if 0
class VhpiReadOnlyCbHdl : public VhpiCbHdl {

};

class VhpiReadWriteCbHdl : public VhpiCbHdl {

};

class VhpiNextPhaseCbHdl : public VhpiCbHdl {

};
#endif

class VhpiStartupCbHdl : public VhpiCbHdl {
public:
    VhpiStartupCbHdl(GpiImplInterface *impl);
    int run_callback(void);
    virtual ~VhpiStartupCbHdl() { }
};

class VhpiShutdownCbHdl : public VhpiCbHdl {
public:
    VhpiShutdownCbHdl(GpiImplInterface *impl);
    int run_callback(void);
    virtual ~VhpiShutdownCbHdl() { }
};

class VhpiReadwriteCbHdl : public VhpiCbHdl {
public:
    VhpiReadwriteCbHdl(GpiImplInterface *impl);
    virtual ~VhpiReadwriteCbHdl() { }
};

#endif /*COCOTB_VHPI_IMPL_H_  */