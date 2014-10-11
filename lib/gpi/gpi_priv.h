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
*    * Neither the name of Potential Ventures Ltd,
*       SolarFlare Communications Inc nor the
*      names of its contributors may be used to endorse or promote products
*      derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
* ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE dGOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#ifndef COCOTB_GPI_PRIV_H_
#define COCOTB_GPI_PRIV_H_

#include <gpi.h>
#include <embed.h>
#include <string>

typedef enum gpi_cb_state {
    GPI_FREE = 0,
    GPI_PRIMED = 1,
    GPI_PRE_CALL = 2,
    GPI_POST_CALL = 3,
    GPI_DELETE = 4,
} gpi_cb_state_e;

class GpiCbHdl;
class GpiImplInterface;
class GpiIterator;
class GpiCbHdl;

template<class To, class Ti>
inline To sim_to_hdl(Ti input)
{
    To result = reinterpret_cast<To>(input);
    if (!result) {
        LOG_CRITICAL("GPI: Handle passed down is not valid gpi_sim_hdl");
        exit(1);
    }

    return result;
}

/* Base GPI class others are derived from */
class GpiHdl {
public:
    //GpiHdl() : m_impl(NULL) { }
    GpiHdl(GpiImplInterface *impl) : m_impl(impl) { }
    virtual ~GpiHdl() { }
    virtual int initialise(std::string name);                   // Post constructor init

private:
    GpiHdl() { }   // Disable default constructor

public:
    GpiImplInterface *m_impl;             // VPI/VHPI/FLI routines
    char *gpi_copy_name(const char *name);  // Might not be needed
};

/* GPI object handle, maps to a simulation object */
// An object is any item in the hierarchy
// Provides methods for iterating through children or finding by name
// Initial object is returned by call to GpiImplInterface::get_root_handle()
// Susequent operations to get children go through this handle.
// GpiObjHdl::get_handle_by_name/get_handle_by_index are really factories
// that construct an object derived from GpiSignalObjHdl or GpiObjHdl
class GpiObjHdl : public GpiHdl {
public:
    GpiObjHdl(std::string name) : GpiHdl(NULL), m_name(name) { }
    GpiObjHdl(GpiImplInterface *impl) : GpiHdl(impl) { }
    virtual ~GpiObjHdl() { }

    // The following methods permit children below this level of the hierarchy
    // to be discovered and instantiated
    virtual GpiObjHdl *get_handle_by_name(std::string &name) = 0;
    virtual GpiObjHdl *get_handle_by_index(uint32_t index) = 0;
    virtual GpiIterator *iterate_handle(uint32_t type) = 0;
    virtual GpiObjHdl *next_handle(GpiIterator *iterator) = 0;

    virtual const char* get_name_str(void);
    virtual const char* get_type_str(void);

    bool is_native_impl(GpiImplInterface *impl);
    virtual int initialise(std::string name);

protected:
    std::string m_name;
    std::string m_type;
};


/* GPI Signal object handle, maps to a simulation object */
//
// Identical to an object but adds additional methods for getting/setting the
// value of the signal (which doesn't apply to non signal items in the hierarchy
class GpiSignalObjHdl : public GpiObjHdl {
public:
    GpiSignalObjHdl(GpiImplInterface *impl) : GpiObjHdl(impl) { }
    virtual ~GpiSignalObjHdl() { }
    // Provide public access to the implementation (composition vs inheritance)
    virtual const char* get_signal_value_binstr(void) = 0;

    int m_length;

    virtual int set_signal_value(const int value) = 0;
    virtual int set_signal_value(std::string &value) = 0;
    //virtual GpiCbHdl monitor_value(bool rising_edge) = 0; this was for the triggers
    // but the explicit ones are probably better

    // Also think we want the triggers here?
    virtual GpiCbHdl *rising_edge_cb(void) = 0;
    virtual GpiCbHdl *falling_edge_cb(void) = 0;
    virtual GpiCbHdl *value_change_cb(void) = 0;

private:
    //GpiCbHdl value_change_cb;
};


/* GPI Callback handle */
// To set a callback it needs the signal to do this on,
// vpiHandle/vhpiHandleT for instance. The 
class GpiCbHdl : public GpiHdl {
public:
    GpiCbHdl(GpiImplInterface *impl) : GpiHdl(impl),
                                       m_state(GPI_FREE) { }
    // Pure virtual functions for derived classes
    virtual int arm_callback(void) = 0;         // Register with siumlator
    virtual int run_callback(void);         // Entry point from simulator
    virtual int cleanup_callback(void) = 0;     // Cleanup the callback, arm can be called after

    // Set the data to be used for run callback, seperate to arm_callback so data can be re-used
    int set_user_data(const int (*gpi_function)(const void*), const void *data);
    const void *get_user_data(void);

    void set_call_state(gpi_cb_state_e new_state);
    gpi_cb_state_e get_call_state(void);

    virtual ~GpiCbHdl();

protected:
    const int (*gpi_function)(const void *);    // GPI function to callback
    const void *m_cb_data;                // GPI data supplied to "gpi_function"
    gpi_cb_state_e m_state;         // GPI state of the callback through its cycle
};

/* We would then have */
class GpiClockHdl {
public:
    GpiClockHdl(GpiObjHdl *clk) { }
    GpiClockHdl(const char *clk) { }
    ~GpiClockHdl() { }
    int start_clock(const int period_ps); /* Do things with the GpiSignalObjHdl */
    int stop_clock(void);
};

class GpiNextTime : public GpiCbHdl {

};

class GpiTimer : public GpiCbHdl {

};

class GpiReadOnly : public GpiCbHdl {

};

class GpiReadWrite : public GpiCbHdl {

};

class GpiIterator {
public:
	GpiObjHdl *parent;
};

class GpiImplInterface {
public:
    GpiImplInterface(const std::string& name);
    const char *get_name_c(void);
    const std::string& get_name_s(void);
    virtual ~GpiImplInterface() = 0;

    /* Sim related */
    virtual void sim_end(void) = 0;
    virtual void get_sim_time(uint32_t *high, uint32_t *low) = 0;

    /* Hierachy related */
    virtual bool native_check(std::string &name, GpiObjHdl *parent) = 0;
    virtual GpiObjHdl* native_check_create(std::string &name, GpiObjHdl *parent) = 0;
    virtual GpiObjHdl* native_check_create(uint32_t index, GpiObjHdl *parent) = 0;
    virtual GpiObjHdl *get_root_handle(const char *name) = 0;

    /* Callback related, these may (will) return the same handle*/
    virtual GpiCbHdl *register_timed_callback(uint64_t time_ps) = 0;
    virtual GpiCbHdl *register_readonly_callback(void) = 0;
    virtual GpiCbHdl *register_nexttime_callback(void) = 0;
    virtual GpiCbHdl *register_readwrite_callback(void) = 0;
    virtual int deregister_callback(GpiCbHdl *obj_hdl) = 0;

    /* Method to provide strings from operation types */
    virtual const char * reason_to_string(int reason) = 0;

private:
    std::string m_name;
};

/* Called from implementaton layers back up the stack */
int gpi_register_impl(GpiImplInterface *func_tbl);

void gpi_embed_init(gpi_sim_info_t *info);
void gpi_embed_end(void);
void gpi_embed_init_python(void);

#endif /* COCOTB_GPI_PRIV_H_ */