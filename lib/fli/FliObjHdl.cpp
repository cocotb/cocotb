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

#include <bitset>

#include "FliImpl.h"

GpiCbHdl *FliValueObjHdl::value_change_cb(unsigned int edge)
{
    FliSignalCbHdl *cb = NULL;

    if (m_is_var) {
        return NULL;
    }

    switch (edge) {
        case 1:
            cb = &m_rising_cb;
            break;
        case 2:
            cb = &m_falling_cb;
            break;
        case 3:
            cb = &m_either_cb;
            break;
        default:
            return NULL;
    }

    if (cb->arm_callback()) {
        return NULL;
    }

    return (GpiValueCbHdl*)cb;
}

static const char value_enum[10] = "UX01ZWLH-";

const char* FliValueObjHdl::get_signal_value_binstr(void)
{

    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            if (m_is_var) {
                m_val_buff[0] = value_enum[mti_GetVarValue(get_handle<mtiVariableIdT>())];
            } else {
                m_val_buff[0] = value_enum[mti_GetSignalValue(get_handle<mtiSignalIdT>())];
            }
            break;
        case MTI_TYPE_SCALAR:
        case MTI_TYPE_PHYSICAL: {
                unsigned long val = 0;

                if (m_is_var) {
                    val = (unsigned long)mti_GetVarValue(get_handle<mtiVariableIdT>());
                } else {
                    val = (unsigned long)mti_GetSignalValue(get_handle<mtiSignalIdT>());
                }

                std::bitset<32> value(val);
                std::string bin_str = value.to_string<char,std::string::traits_type, std::string::allocator_type>();
                snprintf(m_val_buff, m_val_len+1, "%s", bin_str.c_str());
            }
            break;
        case MTI_TYPE_ARRAY: {
                if (m_is_var) {
                    mti_GetArrayVarValue(get_handle<mtiVariableIdT>(), m_mti_buff);
                } else {
                    mti_GetArraySignalValue(get_handle<mtiSignalIdT>(), m_mti_buff);
                }
                if (m_val_len <= 256) {
                    char *iter = (char*)m_mti_buff;
                    for (int i = 0; i < m_val_len; i++ ) {
                        m_val_buff[i] = value_enum[(int)iter[i]];
                    }
                } else {
                    for (int i = 0; i < m_val_len; i++ ) {
                        m_val_buff[i] = value_enum[m_mti_buff[i]];
                    }
                }
            }
            break;
        default:
            LOG_ERROR("Value Object %s of type %d is not currently supported",
                m_name.c_str(), m_fli_type);
            break;
    }

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff, m_name.c_str());

    return m_val_buff;
}

const char* FliValueObjHdl::get_signal_value_str(void)
{
    LOG_ERROR("Getting signal value as str not currently supported");
    return NULL;
}

double FliValueObjHdl::get_signal_value_real(void)
{
    LOG_ERROR("Getting signal value as double not currently supported!");
    return -1;
}

long FliValueObjHdl::get_signal_value_long(void)
{
    LOG_ERROR("Getting signal value as long not currently supported!");
    return -1;
}

int FliValueObjHdl::set_signal_value(const long value)
{
    int rc;
    char buff[20];

    snprintf(buff, 20, "16#%016X", (int)value);

    if (m_is_var) {
        rc = 0;
        LOG_WARN("Setting a variable is not currently supported!\n");
    } else {
        rc = mti_ForceSignal(get_handle<mtiSignalIdT>(), &buff[0], 0, MTI_FORCE_DEPOSIT, -1, -1);
    }

    if (!rc) {
        LOG_ERROR("Setting signal value failed!\n");
    }
    return rc-1;
}

int FliValueObjHdl::set_signal_value(std::string &value)
{
    int rc;

    snprintf(m_val_str_buff, m_val_str_len+1, "%d'b%s", m_val_len, value.c_str());

    if (m_is_var) {
        rc = 0;
        LOG_WARN("Setting a variable is not currently supported!\n");
    } else {
        rc = mti_ForceSignal(get_handle<mtiSignalIdT>(), &m_val_str_buff[0], 0, MTI_FORCE_DEPOSIT, -1, -1);
    }

    if (!rc) {
        LOG_ERROR("Setting signal value failed!\n");
    }
    return rc-1;
}

int FliValueObjHdl::set_signal_value(const double value)
{
    LOG_ERROR("Setting Signal via double not supported!");
    return -1;
}

int FliValueObjHdl::initialise(std::string &name, std::string &fq_name)
{
    mtiTypeIdT valType;

    /* Pre allocte buffers on signal type basis */
    if (m_is_var) {
        valType = mti_GetVarType(get_handle<mtiVariableIdT>());
    } else {
        valType = mti_GetSignalType(get_handle<mtiSignalIdT>());
    }

    m_fli_type = mti_GetTypeKind(valType);

    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            m_val_len     = 1;
            m_val_str_len = 3+m_val_len;
            break;
        case MTI_TYPE_SCALAR:
        case MTI_TYPE_PHYSICAL:
            m_val_len     = 32;
            m_val_str_len = 4+m_val_len;
            break;
        case MTI_TYPE_ARRAY:
            m_val_len     = mti_TickLength(valType);
            m_val_str_len = snprintf(NULL, 0, "%d'b", m_val_len)+m_val_len;
            m_mti_buff    = (mtiInt32T*)malloc(sizeof(*m_mti_buff) * m_val_len);
            if (!m_mti_buff) {
                LOG_CRITICAL("Unable to alloc mem for value object mti read buffer: ABORTING");
            }
            break;
        default:
            LOG_ERROR("Unable to handle object type for %s (%d)",
                         name.c_str(), m_fli_type);
    }

    m_val_buff = (char*)malloc(m_val_len+1);
    if (!m_val_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object read buffer: ABORTING");
    }
    m_val_buff[m_val_len] = '\0';
    m_val_str_buff = (char*)malloc(m_val_str_len+1);
    if (!m_val_str_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object write buffer: ABORTING");
    }
    m_val_str_buff[m_val_str_len] = '\0';

    GpiObjHdl::initialise(name, fq_name);

    return 0;
}

