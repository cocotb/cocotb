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

#define gpi_container_of(_address, _type, _member)  \
        ((_type *)((uintptr_t)(_address) -      \
         (uintptr_t)(&((_type *)0)->_member)))

typedef struct t_gpi_impl_tbl {
	void (*sim_end)(void);
	void (*get_sim_time)(uint32_t *high, uint32_t *low);
	gpi_sim_hdl (*get_root_handle)(const char *name);
	gpi_sim_hdl (*get_handle_by_name)(const char *name, gpi_sim_hdl parent);
	gpi_sim_hdl (*get_handle_by_index)(gpi_sim_hdl parent, uint32_t index);
	void (*free_handle)(gpi_sim_hdl);
	gpi_iterator_hdl (*iterate_handle)(uint32_t type, gpi_sim_hdl base);
	gpi_sim_hdl (*next_handle)(gpi_iterator_hdl iterator);
	char* (*get_signal_value_binstr)(gpi_sim_hdl gpi_hdl);
	char* (*get_signal_name_str)(gpi_sim_hdl gpi_hdl);
	char* (*get_signal_type_str)(gpi_sim_hdl gpi_hdl);
	void (*set_signal_value_int)(gpi_sim_hdl gpi_hdl, int value);
	void (*set_signal_value_str)(gpi_sim_hdl gpi_hdl, const char *str);    // String of binary char(s) [1, 0, x, z]
	int (*register_timed_callback)(gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data, uint64_t time_ps);
	int (*register_value_change_callback)(gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data, gpi_sim_hdl gpi_hdl);
	int (*register_readonly_callback)(gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);
	int (*register_nexttime_callback)(gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);
	int (*register_readwrite_callback)(gpi_sim_hdl, int (*gpi_function)(void *), void *gpi_cb_data);
	gpi_cb_hdl (*create_cb_handle)(void);
	void (*destroy_cb_handle)(gpi_cb_hdl gpi_hdl);
	int (*deregister_callback)(gpi_sim_hdl gpi_hdl);
	void* (*get_callback_data)(gpi_sim_hdl gpi_hdl);
} s_gpi_impl_tbl, *gpi_impl_tbl;

int gpi_register_impl(gpi_impl_tbl func_tbl, int type);

void gpi_embed_init(gpi_sim_info_t *info);
void gpi_embed_end(void);
void gpi_embed_init_python(void);

char *gpi_copy_name(const char *name);

void gpi_handle_callback(gpi_sim_hdl cb_data);

