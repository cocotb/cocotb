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

#ifndef COCOTB_VPI_IMPL_H_ 
#define COCOTB_VPI_IMPL_H_ 

#include "../gpi/gpi_priv.h"
#include <vpi_user.h>
#include <vector>
#include <map>

// Should be run after every VPI call to check error status
static inline int __check_vpi_error(const char *file, const char *func, long line)
{
    int level=0;
#if VPI_CHECKING
    s_vpi_error_info info;
    int loglevel;

    memset(&info, 0, sizeof(info));
    level = vpi_chk_error(&info);
    if (info.code == 0 && level == 0)
        return 0;

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

    gpi_log("cocotb.gpi", loglevel, file, func, line,
            "VPI Error %s\nPROD %s\nCODE %s\nFILE %s",
            info.message, info.product, info.code, info.file);

#endif
    return level;
}

#define check_vpi_error() do { \
    __check_vpi_error(__FILE__, __func__, __LINE__); \
} while (0)

class VpiReadwriteCbHdl;
class VpiNextPhaseCbHdl;
class VpiReadOnlyCbHdl;

class VpiCbHdl : public virtual GpiCbHdl {
public:
    VpiCbHdl(GpiImplInterface *impl);
    virtual ~VpiCbHdl() { }

    virtual int arm_callback(void);
    virtual int cleanup_callback(void);

protected:
    s_cb_data cb_data;
    s_vpi_time vpi_time;
};

class VpiSignalObjHdl;

class VpiValueCbHdl : public VpiCbHdl, public GpiValueCbHdl {
public:
    VpiValueCbHdl(GpiImplInterface *impl, VpiSignalObjHdl *sig, int edge);
    virtual ~VpiValueCbHdl() { }
    int cleanup_callback(void);
private:
    s_vpi_value m_vpi_value;
};

class VpiTimedCbHdl : public VpiCbHdl {
public:
    VpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps);
    virtual ~VpiTimedCbHdl() { }
    int cleanup_callback();
};

class VpiReadOnlyCbHdl : public VpiCbHdl {
public:
    VpiReadOnlyCbHdl(GpiImplInterface *impl);
    virtual ~VpiReadOnlyCbHdl() { }
};

class VpiNextPhaseCbHdl : public VpiCbHdl {
public:
    VpiNextPhaseCbHdl(GpiImplInterface *impl);
    virtual ~VpiNextPhaseCbHdl() { }
};

class VpiReadwriteCbHdl : public VpiCbHdl {
public:
    VpiReadwriteCbHdl(GpiImplInterface *impl);
    virtual ~VpiReadwriteCbHdl() { }
    int run_callback(void) {
        if (delay_kill) {
            delay_kill = false;
            return 0;
        } else {
            return VpiCbHdl::run_callback();
        }
    }
    int cleanup_callback(void) {
        if (m_state == GPI_PRIMED) {
            delay_kill = true;
            return 0;
        } else {
            return VpiCbHdl::cleanup_callback();
        }
    }
    int arm_callback(void) {
        delay_kill = false;
        return VpiCbHdl::arm_callback();
    }
private:
    bool delay_kill;
};

class VpiStartupCbHdl : public VpiCbHdl {
public:
    VpiStartupCbHdl(GpiImplInterface *impl);
    int run_callback(void);
    int cleanup_callback(void) {
        /* Too many sims get upset with this so we override to do nothing */
        return 0;
    }
    virtual ~VpiStartupCbHdl() { }
};

class VpiShutdownCbHdl : public VpiCbHdl {
public:
    VpiShutdownCbHdl(GpiImplInterface *impl);
    int run_callback(void);
    int cleanup_callback(void) {
        /* Too many sims get upset with this so we override to do nothing */
        return 0;
    }
    virtual ~VpiShutdownCbHdl() { }
};

class KindMappings {
public:
    KindMappings();

public:
    std::map<int32_t, std::vector<int32_t> > options_map;
    std::vector<int32_t>* get_options(int32_t type);

private:
    void add_to_options(int32_t type, int32_t *options);
};

class VpiSignalObjHdl : public GpiSignalObjHdl {
public:
    VpiSignalObjHdl(GpiImplInterface *impl, vpiHandle hdl, gpi_objtype_t objtype) : 
                                                             GpiSignalObjHdl(impl, hdl, objtype),
                                                             m_rising_cb(impl, this, GPI_RISING),
                                                             m_falling_cb(impl, this, GPI_FALLING),
                                                             m_either_cb(impl, this, GPI_FALLING | GPI_RISING) { }
    virtual ~VpiSignalObjHdl() { }

    const char* get_signal_value_binstr(void);
    double get_signal_value_real(void);
    long get_signal_value_long(void);

    int set_signal_value(const long value);
    int set_signal_value(const double value);
    int set_signal_value(std::string &value);

    /* Value change callback accessor */
    GpiCbHdl *value_change_cb(unsigned int edge);
    int initialise(std::string &name);

private:
    VpiValueCbHdl m_rising_cb;
    VpiValueCbHdl m_falling_cb;
    VpiValueCbHdl m_either_cb;
};

class VpiIterator : public GpiIterator {
public:
    VpiIterator(GpiImplInterface *impl, vpiHandle hdl);
    
    virtual ~VpiIterator();

    GpiObjHdl *next_handle(void);

private:
    vpiHandle m_iterator;
    static KindMappings iterate_over;      /* Possible mappings */
    std::vector<int32_t> *selected; /* Mapping currently in use */
    std::vector<int32_t>::iterator one2many;
};

class VpiImpl : public GpiImplInterface {
public:
    VpiImpl(const std::string& name) : GpiImplInterface(name),
                                       m_read_write(this),
                                       m_next_phase(this),
                                       m_read_only(this) { }

     /* Sim related */
    void sim_end(void);
    void get_sim_time(uint32_t *high, uint32_t *low);

    /* Hierachy related */
    GpiObjHdl *get_root_handle(const char *name);
    GpiIterator *iterate_handle(GpiObjHdl *obj_hdl);
    GpiObjHdl *next_handle(GpiIterator *iter);

    /* Callback related, these may (will) return the same handle*/
    GpiCbHdl *register_timed_callback(uint64_t time_ps);
    GpiCbHdl *register_readonly_callback(void);
    GpiCbHdl *register_nexttime_callback(void);
    GpiCbHdl *register_readwrite_callback(void);
    int deregister_callback(GpiCbHdl *obj_hdl);
    GpiObjHdl* native_check_create(std::string &name, GpiObjHdl *parent);
    GpiObjHdl* native_check_create(uint32_t index, GpiObjHdl *parent);
    const char * reason_to_string(int reason);
    GpiObjHdl* create_gpi_obj_from_handle(vpiHandle new_hdl, std::string &name);

private:
    /* Singleton callbacks */
    VpiReadwriteCbHdl m_read_write;
    VpiNextPhaseCbHdl m_next_phase;
    VpiReadOnlyCbHdl m_read_only;
};

#endif /*COCOTB_VPI_IMPL_H_  */
