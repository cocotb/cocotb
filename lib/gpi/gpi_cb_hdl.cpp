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

#include "gpi_priv.h"
#include <iostream>

using namespace std;

/* Genertic base clss implementations */
char *gpi_obj_hdl::gpi_copy_name(const char *name)
{
    int len;
    char *result;
    const char null[] = "NULL";

    if (name)
        len = strlen(name) + 1;
    else {
        LOG_CRITICAL("GPI: attempt to use NULL from impl");
        len = strlen(null);
        name = null;
    }

    result = (char *)malloc(len);
    if (result == NULL) {
        LOG_CRITICAL("GPI: Attempting allocate string buffer failed!");
        len = strlen(null);
        name = null;
    }

    snprintf(result, len, "%s", name);

    return result;
}

int gpi_cb_hdl::handle_callback(void)
{
    return this->gpi_function(m_cb_data);
}

int gpi_cb_hdl::arm_callback(void)
{
    return 0;
}

int gpi_cb_hdl::run_callback(void)
{
    return this->gpi_function(m_cb_data);
}

int gpi_cb_hdl::set_user_data(int (*gpi_function)(void*), void *data)
{
    if (!gpi_function) {
        LOG_ERROR("gpi_function to set_user_data is NULL");
    }
    this->gpi_function = gpi_function;
    this->m_cb_data = data;
    return 0;
}

void * gpi_cb_hdl::get_user_data(void)
{
    return m_cb_data;
}

int gpi_cb_hdl::cleanup_callback(void)
{
    LOG_WARN("Generic cleanup handler");
    return 0;
}

/* Specific callback types */

int gpi_recurring_cb::cleanup_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}

int gpi_onetime_cb::cleanup_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}

int gpi_cb_value_change::run_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}

int gpi_cb_readonly_phase::run_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}

int gpi_cb_nexttime_phase::run_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}

int gpi_cb_readwrite_phase::run_callback(void)
{
    LOG_ERROR("Need to override");
    return 0;
}