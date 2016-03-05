/******************************************************************************
* Copyright (c) 2015/16 Potential Ventures Ltd
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
#include <vector>

#include "FliImpl.h"
#include "acc_vhdl.h"

GpiCbHdl *FliSignalObjHdl::value_change_cb(unsigned int edge)
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

    return (GpiCbHdl *)cb;
}

int FliObjHdl::initialise(std::string &name, std::string &fq_name)
{
    bool is_signal = (get_acc_type() == accSignal || get_acc_full_type() == accAliasSignal);
    bool is_value  = (is_signal                     || get_acc_type() == accAlias        || 
                      get_acc_type() == accVariable || get_acc_type() == accVHDLConstant ||
                      get_acc_type() == accGeneric);

    switch (get_type()) {
        case GPI_STRUCTURE: {
                mtiTypeIdT recType; 
                if (is_signal) {
                    recType = mti_GetSignalType(get_handle<mtiSignalIdT>());
                } else {
                    recType = mti_GetVarType(get_handle<mtiVariableIdT>());
                }
                m_num_elems = mti_GetNumRecordElements(recType);
            }
            break;
        case GPI_MODULE:
            if (!is_value) {
                m_num_elems = 1;
            } else {
                mtiTypeIdT arrayType; 
                if (is_signal) {
                    arrayType = mti_GetSignalType(get_handle<mtiSignalIdT>());
                } else {
                    arrayType = mti_GetVarType(get_handle<mtiVariableIdT>());
                }
                m_num_elems = mti_TickLength(arrayType);
            }
            break;
        default:
            LOG_CRITICAL("Invalid object type for FliObjHdl. (%s (%s))", name.c_str(), get_type_str());
            return -1;
    }
 
    return GpiObjHdl::initialise(name, fq_name);
}


int FliSignalObjHdl::initialise(std::string &name, std::string &fq_name)
{
    return GpiObjHdl::initialise(name, fq_name);
}

int FliValueObjHdl::initialise(std::string &name, std::string &fq_name)
{
    return FliSignalObjHdl::initialise(name, fq_name);
}

const char* FliValueObjHdl::get_signal_value_binstr(void)
{
    LOG_ERROR("Getting signal/variable value as binstr not supported for %s of type %d", m_fullname.c_str(), m_type);
    return NULL;
}

const char* FliValueObjHdl::get_signal_value_str(void)
{
    LOG_ERROR("Getting signal/variable value as str not supported for %s of type %d", m_fullname.c_str(), m_type);
    return NULL;
}

double FliValueObjHdl::get_signal_value_real(void)
{
    LOG_ERROR("Getting signal/variable value as double not supported for %s of type %d", m_fullname.c_str(), m_type);
    return -1;
}

long FliValueObjHdl::get_signal_value_long(void)
{
    LOG_ERROR("Getting signal/variable value as long not supported for %s of type %d", m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value(const long value)
{
    LOG_ERROR("Setting signal/variable value via long not supported for %s of type %d", m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value(std::string &value)
{
    LOG_ERROR("Setting signal/variable value via string not supported for %s of type %d", m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value(const double value)
{
    LOG_ERROR("Setting signal/variable value via double not supported for %s of type %d", m_fullname.c_str(), m_type);
    return -1;
}

int FliEnumObjHdl::initialise(std::string &name, std::string &fq_name)
{
    m_num_elems   = 1;
    m_value_enum  = mti_GetEnumValues(m_val_type);
    m_num_enum    = mti_TickLength(m_val_type);

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliEnumObjHdl::get_signal_value_str(void)
{
    if (m_is_var) {
        return m_value_enum[mti_GetVarValue(get_handle<mtiVariableIdT>())];
    } else {
        return m_value_enum[mti_GetSignalValue(get_handle<mtiSignalIdT>())];
    }
}

long FliEnumObjHdl::get_signal_value_long(void)
{
    if (m_is_var) {
        return (long)mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        return (long)mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }
}

int FliEnumObjHdl::set_signal_value(const long value)
{
    if (value > m_num_enum || value < 0) {
        LOG_ERROR("Attempted to set a enum with range [0,%d] with invalid value %d!\n", m_num_enum, value);
        return -1;
    }

    if (m_is_var) {
        mti_SetVarValue(get_handle<mtiVariableIdT>(), value);
    } else {
        mti_SetSignalValue(get_handle<mtiSignalIdT>(), value);
    }

    return 0;
}

int FliLogicObjHdl::initialise(std::string &name, std::string &fq_name)
{
    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            m_num_elems   = 1;
            m_value_enum  = mti_GetEnumValues(m_val_type);
            m_num_enum    = mti_TickLength(m_val_type);
            break;
        case MTI_TYPE_ARRAY: {
                mtiTypeIdT elemType = mti_GetArrayElementType(m_val_type);

                m_ascending   = (mti_TickDir(m_val_type) == 1);
                m_value_enum  = mti_GetEnumValues(elemType);
                m_num_enum    = mti_TickLength(elemType);
                m_num_elems   = mti_TickLength(m_val_type);

                m_mti_buff    = (char*)malloc(sizeof(*m_mti_buff) * m_num_elems);
                if (!m_mti_buff) {
                    LOG_CRITICAL("Unable to alloc mem for value object mti read buffer: ABORTING");
                    return -1;
                }
            }
            break;
        default:
            LOG_CRITICAL("Object type is not 'logic' for %s (%d)", name.c_str(), m_fli_type);
            return -1;
    }

    for (mtiInt32T i = 0; i < m_num_enum; i++) {
        m_enum_map[m_value_enum[i][1]] = i;  // enum is of the format 'U' or '0', etc.
    }

    m_val_buff = (char*)malloc(m_num_elems+1);
    if (!m_val_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object read buffer: ABORTING");
    }
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliLogicObjHdl::get_signal_value_binstr(void)
{
    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            if (m_is_var) {
                m_val_buff[0] = m_value_enum[mti_GetVarValue(get_handle<mtiVariableIdT>())][1];
            } else {
                m_val_buff[0] = m_value_enum[mti_GetSignalValue(get_handle<mtiSignalIdT>())][1];
            }
            break;
        case MTI_TYPE_ARRAY: {
                if (m_is_var) {
                    mti_GetArrayVarValue(get_handle<mtiVariableIdT>(), m_mti_buff);
                } else {
                    mti_GetArraySignalValue(get_handle<mtiSignalIdT>(), m_mti_buff);
                }

                for (int i = 0; i < m_num_elems; i++ ) {
                    m_val_buff[i] = m_value_enum[(int)m_mti_buff[i]][1];
                }
            }
            break;
        default:
            LOG_CRITICAL("Object type is not 'logic' for %s (%d)", m_name.c_str(), m_fli_type);
            return NULL;
    }

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff, m_name.c_str());

    return m_val_buff;
}

int FliLogicObjHdl::set_signal_value(const long value)
{
    if (m_num_elems == 1) {
        mtiInt32T enumVal = value ? m_enum_map['1'] : m_enum_map['0'];

        if (m_is_var) {
            mti_SetVarValue(get_handle<mtiVariableIdT>(), enumVal);
        } else {
            mti_SetSignalValue(get_handle<mtiSignalIdT>(), enumVal);
        }
    } else {
        int valLen = sizeof(value) * 8;
        mtiInt32T enumVal;
        int numPad;
        int idx;

        numPad       = valLen < m_num_elems ? m_num_elems-valLen : 0;
        valLen       = valLen > m_num_elems ? m_num_elems : valLen;

        LOG_DEBUG("set_signal_value(long)::0x%016x", value);

        // Pad MSB for descending vector
        for (idx = 0; idx < numPad && !m_ascending; idx++) {
            m_mti_buff[idx] = (char)m_enum_map['0']; 
        }

        if (m_ascending) {
            for (int i = 0; i < valLen; i++) {
                enumVal = value&(1L<<i) ? m_enum_map['1'] : m_enum_map['0'];

                m_mti_buff[i] = (char)enumVal; 
            }
        } else {
            int len = valLen + numPad;
            for (int i = 0; i < valLen; i++, idx++) {
                enumVal = value&(1L<<i) ? m_enum_map['1'] : m_enum_map['0'];

                m_mti_buff[len - idx - 1] = (char)enumVal; 
            }
        }

        // Pad MSB for ascending vector
        for (idx = valLen; idx < (numPad+valLen) && m_ascending; idx++) {
            m_mti_buff[idx] = (char)m_enum_map['0']; 
        }


        if (m_is_var) {
            mti_SetVarValue(get_handle<mtiVariableIdT>(), (long)m_mti_buff);
        } else {
            mti_SetSignalValue(get_handle<mtiSignalIdT>(), (long)m_mti_buff);
        }
    }

    return 0;
}

int FliLogicObjHdl::set_signal_value(std::string &value)
{
    if (m_num_elems == 1) {
        mtiInt32T enumVal = m_enum_map[value.c_str()[0]];

        if (m_is_var) {
            mti_SetVarValue(get_handle<mtiVariableIdT>(), enumVal);
        } else {
            mti_SetSignalValue(get_handle<mtiSignalIdT>(), enumVal);
        }
    } else {
        int len = value.length();
        int numPad;

        numPad = len < m_num_elems ? m_num_elems-len : 0;

        LOG_DEBUG("set_signal_value(string)::%s", value.c_str());

        if (len > m_num_elems) {
            LOG_DEBUG("FLI: Attempt to write sting longer than (%s) signal %d > %d", m_name.c_str(), len, m_num_elems);
            len = m_num_elems;
        }

        mtiInt32T enumVal;
        std::string::iterator valIter;
        int i = 0;

        // Pad MSB for descending vector
        for (i = 0; i < numPad && !m_ascending; i++) {
            m_mti_buff[i] = (char)m_enum_map['0']; 
        }

        for (valIter = value.begin(); (valIter != value.end()) && (i < m_num_elems); valIter++, i++) {
            enumVal = m_enum_map[*valIter];
            m_mti_buff[i] = (char)enumVal; 
        }

        // Fill bits a the end of the value to 0's
        for (i = len; i < m_num_elems && m_ascending; i++) {
            m_mti_buff[i] = (char)m_enum_map['0']; 
        }

        if (m_is_var) {
            mti_SetVarValue(get_handle<mtiVariableIdT>(), (long)m_mti_buff);
        } else {
            mti_SetSignalValue(get_handle<mtiSignalIdT>(), (long)m_mti_buff);
        }
    }

    return 0;
}

int FliIntObjHdl::initialise(std::string &name, std::string &fq_name)
{
    m_num_elems   = 1;

    m_val_buff = (char*)malloc(33);  // Integers are always 32-bits
    if (!m_val_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object read buffer: ABORTING");
        return -1;
    }
    m_val_buff[m_num_elems] = '\0';
 
    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliIntObjHdl::get_signal_value_binstr(void)
{
    mtiInt32T val;

    if (m_is_var) {
        val = mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        val = mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }

    std::bitset<32> value((unsigned long)val);
    std::string bin_str = value.to_string<char,std::string::traits_type, std::string::allocator_type>();
    snprintf(m_val_buff, 33, "%s", bin_str.c_str());

    return m_val_buff;
}

long FliIntObjHdl::get_signal_value_long(void)
{
    mtiInt32T value;

    if (m_is_var) {
        value = mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        value = mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }

    return (long)value;
}

int FliIntObjHdl::set_signal_value(const long value)
{
    if (m_is_var) {
        mti_SetVarValue(get_handle<mtiVariableIdT>(), value);
    } else {
        mti_SetSignalValue(get_handle<mtiSignalIdT>(), value);
    }

    return 0;
}

int FliRealObjHdl::initialise(std::string &name, std::string &fq_name)
{

    m_num_elems   = 1;

    m_mti_buff    = (double*)malloc(sizeof(double));
    if (!m_mti_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object mti read buffer: ABORTING");
        return -1;
    }
 
    return FliValueObjHdl::initialise(name, fq_name);
}

double FliRealObjHdl::get_signal_value_real(void)
{
    if (m_is_var) {
        mti_GetVarValueIndirect(get_handle<mtiVariableIdT>(), m_mti_buff);
    } else {
        mti_GetSignalValueIndirect(get_handle<mtiSignalIdT>(), m_mti_buff);
    }

    LOG_DEBUG("Retrieved \"%f\" for value object %s", m_mti_buff[0], m_name.c_str());

    return m_mti_buff[0];
}

int FliRealObjHdl::set_signal_value(const double value)
{
    m_mti_buff[0] = value;

    if (m_is_var) {
        mti_SetVarValue(get_handle<mtiVariableIdT>(), (long)m_mti_buff);
    } else {
        mti_SetSignalValue(get_handle<mtiSignalIdT>(), (long)m_mti_buff);
    }

    return 0;
}

int FliStringObjHdl::initialise(std::string &name, std::string &fq_name)
{
    m_num_elems   = mti_TickLength(m_val_type);

    m_mti_buff    = (char*)malloc(sizeof(char) * m_num_elems);
    if (!m_mti_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object mti read buffer: ABORTING");
        return -1;
    }

    m_val_buff = (char*)malloc(m_num_elems+1);
    if (!m_val_buff) {
        LOG_CRITICAL("Unable to alloc mem for value object read buffer: ABORTING");
        return -1;
    }
    m_val_buff[m_num_elems] = '\0';
 
    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliStringObjHdl::get_signal_value_str(void)
{
    if (m_is_var) {
        mti_GetArrayVarValue(get_handle<mtiVariableIdT>(), m_mti_buff);
    } else {
        mti_GetArraySignalValue(get_handle<mtiSignalIdT>(), m_mti_buff);
    }

    strncpy(m_val_buff, m_mti_buff, m_num_elems);

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff, m_name.c_str());

    return m_val_buff;
}

int FliStringObjHdl::set_signal_value(std::string &value)
{
    strncpy(m_mti_buff, value.c_str(), m_num_elems);

    if (m_is_var) {
        mti_SetVarValue(get_handle<mtiVariableIdT>(), (long)m_mti_buff);
    } else {
        mti_SetSignalValue(get_handle<mtiSignalIdT>(), (long)m_mti_buff);
    }

    return 0;
}

