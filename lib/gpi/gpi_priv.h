/******************************************************************************
* Copyright (c) 2013 Potential Ventures Ltd
* Copyright (c) 2013 SolarFlare Communications Inc
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
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
******************************************************************************/

#include <gpi.h>
#include <embed.h>
#include <string>

using namespace std;

class gpi_impl_interface;

class gpi_hdl {
public:
    gpi_hdl(gpi_impl_interface *impl) : m_impl(impl) { }
    virtual ~gpi_hdl() { }

public:
    gpi_impl_interface *m_impl;     // Implementation routines
};

class gpi_obj_hdl : public gpi_hdl {
public:
    gpi_obj_hdl(gpi_impl_interface *impl) : gpi_hdl(impl) { }
    char *gpi_copy_name(const char *name);

    virtual ~gpi_obj_hdl() { }
};

class gpi_cb_hdl : public gpi_hdl {
public:
    /* Override to change behaviour as needed */
    gpi_cb_hdl(gpi_impl_interface *impl) : gpi_hdl(impl) { }
    int handle_callback(void);
    virtual int arm_callback(void);
    virtual int run_callback(void);
    virtual int cleanup_callback(void) = 0;

    int set_user_data(int (*gpi_function)(void*), void *data);
    void *get_user_data(void);

    virtual ~gpi_cb_hdl() { }

private:
    gpi_cb_hdl();

protected:
    int (*gpi_function)(void *);    // GPI function to callback
    void *m_cb_data;              // GPI data supplied to "gpi_function"
};

class gpi_recurring_cb : public gpi_cb_hdl {
public:
    int cleanup_callback(void);
};

class gpi_onetime_cb : public gpi_cb_hdl {
public:
    int cleanup_callback(void);
};

class gpi_cb_timed : public gpi_onetime_cb {
public:
    int run_callback(void);
};

class gpi_cb_value_change : public gpi_recurring_cb {
public:
    int run_callback(void);
};

class gpi_cb_readonly_phase : public gpi_onetime_cb {
public:
    int run_callback(void);
};

class gpi_cb_nexttime_phase : public gpi_onetime_cb {
public:
    int run_callback(void);
};

class gpi_cb_readwrite_phase : public gpi_onetime_cb {
public:
    int run_callback(void);
};

class gpi_iterator {
public:
	gpi_obj_hdl *parent;
};

class gpi_impl_interface {
public:
    string m_name;

public:
    gpi_impl_interface(const string& name);
    virtual ~gpi_impl_interface() = 0;

    /* Sim related */
    virtual void sim_end(void) = 0;
    virtual void get_sim_time(uint32_t *high, uint32_t *low) = 0;

    /* Signal related */
    virtual gpi_obj_hdl *get_root_handle(const char *name) = 0;
    virtual gpi_obj_hdl *get_handle_by_name(const char *name, gpi_obj_hdl *parent) = 0;
    virtual gpi_obj_hdl *get_handle_by_index(gpi_obj_hdl *parent, uint32_t index) = 0;
    virtual void free_handle(gpi_obj_hdl*) = 0;
    virtual gpi_iterator *iterate_handle(uint32_t type, gpi_obj_hdl *base) = 0;
    virtual gpi_obj_hdl *next_handle(gpi_iterator *iterator) = 0;
    virtual char* get_signal_value_binstr(gpi_obj_hdl *gpi_hdl) = 0;
    virtual char* get_signal_name_str(gpi_obj_hdl *gpi_hdl) = 0;
    virtual char* get_signal_type_str(gpi_obj_hdl *gpi_hdl) = 0;
    virtual void set_signal_value_int(gpi_obj_hdl *gpi_hdl, int value) = 0;
    virtual void set_signal_value_str(gpi_obj_hdl *gpi_hdl, const char *str) = 0;    // String of binary char(s) [1, 0, x, z]
    
    /* Callback related */
    virtual gpi_cb_hdl *register_timed_callback(uint64_t time_ps) = 0;
    virtual gpi_cb_hdl *register_value_change_callback(gpi_obj_hdl *obj_hdl) = 0;
    virtual gpi_cb_hdl *register_readonly_callback(void) = 0;
    virtual gpi_cb_hdl *register_nexttime_callback(void) = 0;
    virtual gpi_cb_hdl *register_readwrite_callback(void) = 0;
    virtual int deregister_callback(gpi_cb_hdl *gpi_hdl) = 0;

    virtual gpi_cb_hdl *create_cb_handle(void) = 0;
    virtual void destroy_cb_handle(gpi_cb_hdl *gpi_hdl) = 0;
    //virtual void* get_callback_data(gpi_sim_hdl gpi_hdl) = 0;
};

/* Called from implementaton layers back up the stack */
int gpi_register_impl(gpi_impl_interface *func_tbl);

void gpi_embed_init(gpi_sim_info_t *info);
void gpi_embed_end(void);
void gpi_embed_init_python(void);