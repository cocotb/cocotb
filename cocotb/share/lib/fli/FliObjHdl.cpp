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


mtiTypeIdT FliSignalObjIntf::mti_get_type(void)
{
    return mti_GetSignalType(m_hdl);
}

mtiInt32T FliSignalObjIntf::mti_get_value(void)
{
    return mti_GetSignalValue(m_hdl);
}

void * FliSignalObjIntf::mti_get_array_value(void *buffer)
{
    return mti_GetArraySignalValue(m_hdl, buffer);
}

void * FliSignalObjIntf::mti_get_value_indirect(void *buffer)
{
    return mti_GetSignalValueIndirect(m_hdl, buffer);
}

void FliSignalObjIntf::mti_set_value(mtiLongT value)
{
    mti_SetSignalValue(m_hdl, value);
}

mtiTypeIdT FliVariableObjIntf::mti_get_type(void)
{
    return mti_GetVarType(m_hdl);
}

mtiInt32T FliVariableObjIntf::mti_get_value(void)
{
    return mti_GetVarValue(m_hdl);
}

void * FliVariableObjIntf::mti_get_array_value(void *buffer)
{
    return mti_GetArrayVarValue(m_hdl, buffer);
}

void * FliVariableObjIntf::mti_get_value_indirect(void *buffer)
{
    return mti_GetVarValueIndirect(m_hdl, buffer);
}

void FliVariableObjIntf::mti_set_value(mtiLongT value)
{
    mti_SetVarValue(m_hdl, value);
}


FliArrayObjHdl::FliArrayObjHdl(GpiImplInterface *impl, mtiSignalIdT hdl) :
                   GpiObjHdl(impl, hdl, GPI_ARRAY)
{
    m_fli_intf = new FliSignalObjIntf(hdl);
}


FliArrayObjHdl::FliArrayObjHdl(GpiImplInterface *impl, mtiVariableIdT hdl, bool is_const) :
                   GpiObjHdl(impl, hdl, GPI_ARRAY, is_const)
{
    m_fli_intf = new FliVariableObjIntf(hdl);
}

FliArrayObjHdl::~FliArrayObjHdl()
{
    delete m_fli_intf;
}

int FliArrayObjHdl::initialise(std::string &name, std::string &fq_name)
{
    mtiTypeIdT _type = m_fli_intf->mti_get_type();

    m_range_left  = mti_TickLeft(_type);
    m_range_right = mti_TickRight(_type);
    m_num_elems   = mti_TickLength(_type);
    m_indexable   = true;

    return GpiObjHdl::initialise(name, fq_name);
}


FliRecordObjHdl::FliRecordObjHdl(GpiImplInterface *impl, mtiSignalIdT hdl) :
                   GpiObjHdl(impl, hdl, GPI_STRUCTURE)
{
    m_fli_intf = new FliSignalObjIntf(hdl);
}


FliRecordObjHdl::FliRecordObjHdl(GpiImplInterface *impl, mtiVariableIdT hdl, bool is_const) :
                   GpiObjHdl(impl, hdl, GPI_STRUCTURE, is_const)
{
    m_fli_intf = new FliVariableObjIntf(hdl);
}

FliRecordObjHdl::~FliRecordObjHdl()
{
    delete m_fli_intf;
}

int FliRecordObjHdl::initialise(std::string &name, std::string &fq_name)
{
    mtiTypeIdT _type = m_fli_intf->mti_get_type();

    m_num_elems = mti_GetNumRecordElements(_type);

    return GpiObjHdl::initialise(name, fq_name);
}

int FliObjHdl::initialise(std::string &name, std::string &fq_name)
{
    char * str;

    str = mti_GetPrimaryName(get_handle<mtiRegionIdT>());
    if (str != NULL)
        m_definition_name = str;

    str = mti_GetRegionSourceName(get_handle<mtiRegionIdT>());
    if (str != NULL)
        m_definition_file = str;

    return GpiObjHdl::initialise(name, fq_name);
}

FliValueObjHdl::FliValueObjHdl(GpiImplInterface *impl, mtiSignalIdT hdl, gpi_objtype_t objtype) :
                   GpiSignalObjHdl(impl, hdl, objtype, false)
{
    m_fli_intf   = new FliSignalObjIntf(hdl);
    m_rising_cb  = new FliSignalCbHdl(m_impl, this, GPI_RISING);
    m_falling_cb = new FliSignalCbHdl(m_impl, this, GPI_FALLING);
    m_either_cb  = new FliSignalCbHdl(m_impl, this, GPI_FALLING | GPI_RISING);
}
FliValueObjHdl::FliValueObjHdl(GpiImplInterface *impl, mtiVariableIdT hdl, gpi_objtype_t objtype, bool is_const) :
                   GpiSignalObjHdl(impl, hdl, objtype, is_const)
{
    m_fli_intf   = new FliVariableObjIntf(hdl);
    m_rising_cb  = NULL;
    m_falling_cb = NULL;
    m_either_cb  = NULL;
}

FliValueObjHdl::~FliValueObjHdl() {
    if (m_fli_intf != NULL)
        delete m_fli_intf;
    if (m_rising_cb != NULL)
        delete m_rising_cb;
    if (m_falling_cb != NULL)
        delete m_falling_cb;
    if (m_either_cb != NULL)
        delete m_either_cb;
}

int FliValueObjHdl::initialise(std::string &name, std::string &fq_name)
{
    return GpiObjHdl::initialise(name, fq_name);
}

GpiCbHdl *FliValueObjHdl::value_change_cb(unsigned int edge)
{
    FliSignalCbHdl *cb = NULL;

    switch (edge) {
        case 1:
            cb = m_rising_cb;
            break;
        case 2:
            cb = m_falling_cb;
            break;
        case 3:
            cb = m_either_cb;
            break;
        default:
            return NULL;
    }

    if (cb == NULL) {
        return NULL;
    }

    if (cb->arm_callback()) {
        return NULL;
    }

    return (GpiCbHdl *)cb;
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
    mtiTypeIdT _type = m_fli_intf->mti_get_type();

    m_num_elems   = 1;
    m_value_enum  = mti_GetEnumValues(_type);
    m_num_enum    = mti_TickLength(_type);

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliEnumObjHdl::get_signal_value_str(void)
{
    return m_value_enum[m_fli_intf->mti_get_value()];
}

long FliEnumObjHdl::get_signal_value_long(void)
{
    return (long)m_fli_intf->mti_get_value();
}

int FliEnumObjHdl::set_signal_value(const long value)
{
    if (value > m_num_enum || value < 0) {
        LOG_ERROR("Attempted to set a enum with range [0,%d] with invalid value %d!\n", m_num_enum, value);
        return -1;
    }

    m_fli_intf->mti_set_value(value);

    return 0;
}

int FliLogicObjHdl::initialise(std::string &name, std::string &fq_name)
{
    mtiTypeIdT _type = m_fli_intf->mti_get_type();

    switch (mti_GetTypeKind(_type)) {
        case MTI_TYPE_ENUM:
            m_num_elems   = 1;
            m_value_enum  = mti_GetEnumValues(_type);
            m_num_enum    = mti_TickLength(_type);
            break;
        case MTI_TYPE_ARRAY: {
                mtiTypeIdT elemType = mti_GetArrayElementType(_type);

                m_range_left  = mti_TickLeft(_type);
                m_range_right = mti_TickRight(_type);
                m_num_elems   = mti_TickLength(_type);
                m_indexable   = true;

                m_value_enum  = mti_GetEnumValues(elemType);
                m_num_enum    = mti_TickLength(elemType);

                m_mti_buff    = new char[m_num_elems];
            }
            break;
        default:
            LOG_CRITICAL("Object type is not 'logic' for %s (%d)", name.c_str(), mti_GetTypeKind(_type));
            return -1;
    }

    for (mtiInt32T i = 0; i < m_num_enum; i++) {
        m_enum_map[m_value_enum[i][1]] = i;  // enum is of the format 'U' or '0', etc.
    }

    m_val_buff = new char[m_num_elems+1];
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliLogicObjHdl::get_signal_value_binstr(void)
{
    if (!m_indexable) {
        m_val_buff[0] = m_value_enum[m_fli_intf->mti_get_value()][1];
    } else {
        m_fli_intf->mti_get_array_value(m_mti_buff);

        for (int i = 0; i < m_num_elems; i++ ) {
            m_val_buff[i] = m_value_enum[(int)m_mti_buff[i]][1];
        }
    }

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff, m_name.c_str());

    return m_val_buff;
}

int FliLogicObjHdl::set_signal_value(const long value)
{
    if (!m_indexable) {
        mtiInt32T enumVal = value ? m_enum_map['1'] : m_enum_map['0'];

        m_fli_intf->mti_set_value(enumVal);
    } else {
        LOG_DEBUG("set_signal_value(long)::0x%016x", value);
        for (int i = 0, idx = m_num_elems-1; i < m_num_elems; i++, idx--) {
            mtiInt32T enumVal = value&(1L<<i) ? m_enum_map['1'] : m_enum_map['0'];

            m_mti_buff[idx] = (char)enumVal;
        }

        m_fli_intf->mti_set_value(reinterpret_cast<mtiLongT>(m_mti_buff));
    }

    return 0;
}

int FliLogicObjHdl::set_signal_value(std::string &value)
{
    if (!m_indexable) {
        mtiInt32T enumVal = m_enum_map[value.c_str()[0]];

        m_fli_intf->mti_set_value(enumVal);
    } else {

        if ((int)value.length() != m_num_elems) {
            LOG_ERROR("FLI: Unable to set logic vector due to the string having incorrect length.  Length of %d needs to be %d", value.length(), m_num_elems);
            return -1;
        }

        LOG_DEBUG("set_signal_value(string)::%s", value.c_str());

        mtiInt32T enumVal;
        std::string::iterator valIter;
        int i = 0;

        for (valIter = value.begin(); (valIter != value.end()) && (i < m_num_elems); valIter++, i++) {
            enumVal = m_enum_map[*valIter];
            m_mti_buff[i] = (char)enumVal;
        }

        m_fli_intf->mti_set_value(reinterpret_cast<mtiLongT>(m_mti_buff));
    }

    return 0;
}

int FliIntObjHdl::initialise(std::string &name, std::string &fq_name)
{
    m_num_elems   = 1;

    m_val_buff = new char[33];  // Integers are always 32-bits
    m_val_buff[33] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliIntObjHdl::get_signal_value_binstr(void)
{
    mtiInt32T val;

    val = m_fli_intf->mti_get_value();

    std::bitset<32> value((unsigned long)val);
    std::string bin_str = value.to_string<char,std::string::traits_type, std::string::allocator_type>();
    snprintf(m_val_buff, 33, "%s", bin_str.c_str());

    return m_val_buff;
}

long FliIntObjHdl::get_signal_value_long(void)
{
    mtiInt32T value;

    value = m_fli_intf->mti_get_value();

    return (long)value;
}

int FliIntObjHdl::set_signal_value(const long value)
{
    m_fli_intf->mti_set_value(value);
    return 0;
}

int FliRealObjHdl::initialise(std::string &name, std::string &fq_name)
{

    m_num_elems   = 1;

    return FliValueObjHdl::initialise(name, fq_name);
}

double FliRealObjHdl::get_signal_value_real(void)
{
    double rv;

    m_fli_intf->mti_get_value_indirect(&rv);

    LOG_DEBUG("Retrieved \"%f\" for value object %s", rv, m_name.c_str());

    return rv;
}

int FliRealObjHdl::set_signal_value(const double value)
{
    m_fli_intf->mti_set_value(reinterpret_cast<mtiLongT>(&value));

    return 0;
}

int FliStringObjHdl::initialise(std::string &name, std::string &fq_name)
{
    mtiTypeIdT _type = m_fli_intf->mti_get_type();

    m_range_left  = mti_TickLeft(_type);
    m_range_right = mti_TickRight(_type);
    m_num_elems   = mti_TickLength(_type);
    m_indexable   = true;

    m_val_buff    = new char[m_num_elems+1];
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char* FliStringObjHdl::get_signal_value_str(void)
{
    m_fli_intf->mti_get_array_value(m_val_buff);

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff, m_name.c_str());

    return m_val_buff;
}

int FliStringObjHdl::set_signal_value(std::string &value)
{
    m_fli_intf->mti_set_value(reinterpret_cast<mtiLongT>(value.data()));

    return 0;
}
