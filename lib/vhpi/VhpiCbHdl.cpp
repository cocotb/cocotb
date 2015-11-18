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

#include "VhpiImpl.h"

extern "C" void handle_vhpi_callback(const vhpiCbDataT *cb_data);

VhpiSignalObjHdl::~VhpiSignalObjHdl()
{
    switch (m_value.format) {
        case vhpiIntVecVal:
        case vhpiEnumVecVal:
        case vhpiLogicVecVal:
            free(m_value.value.enumvs);
        default:
            break;
    }

    if (m_binvalue.value.str)
        free(m_binvalue.value.str);
}

int VhpiSignalObjHdl::initialise(std::string &name, std::string &fq_name) {
    // Determine the type of object, either scalar or vector
    m_value.format = vhpiObjTypeVal;
    m_value.bufSize = 0;
    m_value.value.str = NULL;
    m_value.numElems = 0;
    /* We also alloc a second value member for use with read string operations */
    m_binvalue.format = vhpiBinStrVal;
    m_binvalue.bufSize = 0;
    m_binvalue.numElems = 0;
    m_binvalue.value.str = NULL;

    vhpiHandleT handle = GpiObjHdl::get_handle<vhpiHandleT>();

    if (0 > vhpi_get_value(get_handle<vhpiHandleT>(), &m_value)) {
        if (vhpiSliceNameK == vhpi_get(vhpiKindP, handle)) {
            m_value.format = vhpiEnumVecVal;
        } else {
            LOG_DEBUG("vhpi_get_value failed and not a vhpiSliceNameK setting to vhpiRawDataVal");
            m_value.format = vhpiRawDataVal;
        }
    }

    LOG_DEBUG("Found %s of format type %s (%d) format object with %d elems buffsize %d size %d",
              name.c_str(),
              ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format),
              m_value.format,
              m_value.numElems,
              m_value.bufSize,
              vhpi_get(vhpiSizeP, handle));

    // Default - overridden below in certain special cases
    m_num_elems = m_value.numElems;

    switch (m_value.format) {
        case vhpiIntVal:
        case vhpiEnumVal:
        case vhpiLogicVal:
        case vhpiRealVal:
        case vhpiCharVal: {
            break;
        }

        case vhpiIntVecVal:
        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            m_num_elems = vhpi_get(vhpiSizeP, handle);
            m_value.bufSize = m_num_elems*sizeof(vhpiEnumT);
            m_value.value.enumvs = (vhpiEnumT *)malloc(m_value.bufSize + 1);
            if (!m_value.value.enumvs) {
                LOG_CRITICAL("Unable to alloc mem for write buffer: ABORTING");
            }
            LOG_DEBUG("Overriding num_elems to %d", m_num_elems);
            break;
        }

        case vhpiStrVal: {
            m_num_elems = vhpi_get(vhpiSizeP, handle);
            m_value.bufSize = (m_num_elems)*sizeof(vhpiCharT) + 1;
            m_value.value.str = (vhpiCharT *)malloc(m_value.bufSize);
            m_value.numElems = m_num_elems;
            if (!m_value.value.str) {
                LOG_CRITICAL("Unable to alloc mem for write buffer");
            }
            LOG_DEBUG("Overriding num_elems to %d", m_num_elems);
            break;
        }
        case vhpiRawDataVal: {
            // This is an internal representation - the only way to determine
            // the size is to iterate over the members and count sub-elements
            m_num_elems = 0;
            vhpiHandleT result = NULL;
            vhpiHandleT iterator = vhpi_iterator(vhpiIndexedNames,
                                                 handle);
            while (true) {
                result = vhpi_scan(iterator);
                if (NULL == result)
                    break;
                m_num_elems++;
            }
            LOG_DEBUG("Found vhpiRawDataVal with %d elements", m_num_elems);
            goto gpi_init;
        }

        default: {
            LOG_ERROR("Unable to determine property for %s (%d) format object",
                         ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format), m_value.format);
        }
    }

    if (m_num_elems) {
        m_binvalue.bufSize = m_num_elems*sizeof(vhpiCharT) + 1;
        m_binvalue.value.str = (vhpiCharT *)calloc(m_binvalue.bufSize, sizeof(vhpiCharT));

        if (!m_binvalue.value.str) {
            LOG_CRITICAL("Unable to alloc mem for read buffer of signal %s", name.c_str());
        }
    }

gpi_init:
    return GpiObjHdl::initialise(name, fq_name);
}

VhpiCbHdl::VhpiCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl)
{
    cb_data.reason    = 0;
    cb_data.cb_rtn    = handle_vhpi_callback;
    cb_data.obj       = NULL;
    cb_data.time      = NULL;
    cb_data.value     = NULL;
    cb_data.user_data = (char *)this;

    vhpi_time.high = 0;
    vhpi_time.low = 0;
}

int VhpiCbHdl::cleanup_callback(void)
{
    /* For non timer callbacks we disable rather than remove */
    int ret = 0;
    if (m_state == GPI_FREE)
        return 0;

    vhpiStateT cbState = (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
    if (vhpiEnable == cbState) {
        ret = vhpi_disable_cb(get_handle<vhpiHandleT>());
        m_state = GPI_FREE;
    }

    if (ret)
        check_vhpi_error();

    return 0;
}

int VhpiCbHdl::arm_callback(void)
{
    int ret = 0;
    vhpiStateT cbState;

    if (m_state == GPI_PRIMED)
        return 0;

    /* Do we already have a handle, if so and it is disabled then
       just re-enable it */

    if (get_handle<vhpiHandleT>()) {
        cbState = (vhpiStateT)vhpi_get(vhpiStateP, get_handle<vhpiHandleT>());
        if (vhpiDisable == cbState) {
            if (vhpi_enable_cb(get_handle<vhpiHandleT>())) {
                check_vhpi_error();
                goto error;
            }
        }
    } else {

        vhpiHandleT new_hdl = vhpi_register_cb(&cb_data, vhpiReturnCb);

        if (!new_hdl) {
            check_vhpi_error();
            LOG_ERROR("VHPI: Unable to register callback a handle for VHPI type %s(%d)",
                         m_impl->reason_to_string(cb_data.reason), cb_data.reason);
            goto error;
        }

        cbState = (vhpiStateT)vhpi_get(vhpiStateP, new_hdl);
        if (vhpiEnable != cbState) {
            LOG_ERROR("VHPI ERROR: Registered callback isn't enabled! Got %d\n", cbState);
            goto error;
        }

        m_obj_hdl = new_hdl;
    }
    m_state = GPI_PRIMED;

    return ret;

error:
    m_state = GPI_FREE;
    return -1;
}

// Value related functions
const vhpiEnumT VhpiSignalObjHdl::chr2vhpi(const char value)
{
    switch (value) {
        case '0':
            return vhpi0;
        case '1':
            return vhpi1;
        case 'U':
        case 'u':
            return vhpiU;
        case 'Z':
        case 'z':
            return vhpiZ;
        case 'X':
        case 'x':
            return vhpiX;
        default:
            return vhpiDontCare;
    }
}

// Value related functions
int VhpiLogicSignalObjHdl::set_signal_value(long value)
{
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = value ? vhpi1 : vhpi0;
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            int i;
            for (i=0; i<m_num_elems; i++)
                m_value.value.enumvs[m_num_elems-i-1] = value&(1<<i) ? vhpi1 : vhpi0;

            m_value.numElems = m_num_elems;
            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to set a std_logic signal with a raw value");
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiDepositPropagate)) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiLogicSignalObjHdl::set_signal_value(std::string &value)
{
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = chr2vhpi(value.c_str()[0]);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            int len = value.length();

            // Since we may not get the numElems correctly from the sim and have to infer it
            // we also need to set it here as well each time.

            m_value.numElems = len;

            if (len > m_num_elems) {
                LOG_DEBUG("VHPI: Attempt to write string longer than (%s) signal %d > %d",
                          m_name.c_str(), len, m_num_elems);
                m_value.numElems = m_num_elems;
            }

            std::string::iterator iter;

            int i = 0;
            for (iter = value.begin();
                 (iter != value.end()) && (i < m_num_elems);
                 iter++, i++) {
                m_value.value.enumvs[i] = chr2vhpi(*iter);
            }

            // Fill bits at the end of the value to 0's
            for (i = len; i < m_num_elems; i++) {
                m_value.value.enumvs[i] = vhpi0;
            }

            break;
        }

        default: {
           LOG_ERROR("VHPI: Unable to set a std_logic signal with a raw value");
           return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiDepositPropagate)) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

// Value related functions
int VhpiSignalObjHdl::set_signal_value(long value)
{
    switch (m_value.format) {
        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {
            int i;
            for (i=0; i<m_num_elems; i++)
                m_value.value.enumvs[m_num_elems-i-1] = value&(1<<i);

            // Since we may not get the numElems correctly from the sim and have to infer it
            // we also need to set it here as well each time.

            m_value.numElems = m_num_elems;
            break;
        }

        case vhpiLogicVal:
        case vhpiEnumVal: {
            m_value.value.enumv = value;
            break;
        }

        case vhpiIntVal: {
            m_value.value.intg = value;
            break;
        }

        case vhpiCharVal: {
            m_value.value.ch = value;
            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to handle this format type %s",
                      ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            return -1;
        }
    }
    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiDepositPropagate)) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiSignalObjHdl::set_signal_value(double value)
{
    switch (m_value.format) {
        case vhpiRealVal:
            m_value.numElems = 1;
            m_value.bufSize = sizeof(value);
            m_value.value.real = value;
            break;

        default: {
            LOG_ERROR("VHPI: Unable to set a Real handle this format type %s",
                      ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            return -1;
        }

    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiDepositPropagate)) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

int VhpiSignalObjHdl::set_signal_value(std::string &value)
{
    switch (m_value.format) {
        case vhpiEnumVal:
        case vhpiLogicVal: {
            m_value.value.enumv = chr2vhpi(value.c_str()[0]);
            break;
        }

        case vhpiEnumVecVal:
        case vhpiLogicVecVal: {

            int len = value.length();

            // Since we may not get the numElems correctly from the sim and have to infer it
            // we also need to set it here as well each time.

            m_value.numElems = len;

            if (len > m_num_elems) {
                LOG_DEBUG("VHPI: Attempt to write string longer than (%s) signal %d > %d",
                          m_name.c_str(), len, m_num_elems);
                m_value.numElems = m_num_elems;
            }

            std::string::iterator iter;

            int i = 0;
            for (iter = value.begin();
                 (iter != value.end()) && (i < m_num_elems);
                 iter++, i++) {
                m_value.value.enumvs[i] = chr2vhpi(*iter);
            }

            // Fill bits at the end of the value to 0's
            for (i = len; i < m_num_elems; i++) {
                m_value.value.enumvs[i] = vhpi0;
            }

            break;
        }

        case vhpiStrVal: {
            std::vector<char> writable(value.begin(), value.end());
            writable.push_back('\0');
            strncpy(m_value.value.str, &writable[0], m_value.numElems);
            m_value.value.str[m_value.numElems] = '\0';
            break;
        }

        default: {
            LOG_ERROR("VHPI: Unable to handle this format type %s",
                      ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            return -1;
        }
    }

    if (vhpi_put_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value, vhpiDepositPropagate)) {
        check_vhpi_error();
        return -1;
    }

    return 0;
}

const char* VhpiSignalObjHdl::get_signal_value_binstr(void)
{
    switch (m_value.format) {
        case vhpiRealVal:
            LOG_INFO("get_signal_value_binstr not supported for %s",
                      ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            return "";
        default: {
            /* Some simulators do not support BinaryValues so we fake up here for them */
            int ret = vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_binvalue);
            if (ret) {
                check_vhpi_error();
                LOG_ERROR("Size of m_binvalue.value.str was not large enough req=%d have=%d for type %s",
                          ret,
                          m_binvalue.bufSize,
                          ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            }

            return m_binvalue.value.str;
        }
    }
}

const char* VhpiSignalObjHdl::get_signal_value_str(void)
{
    switch (m_value.format) {
        case vhpiStrVal: {
            int ret = vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value);
            if (ret) {
                check_vhpi_error();
                LOG_ERROR("Size of m_value.value.str was not large enough req=%d have=%d for type %s",
                          ret,
                          m_value.bufSize,
                          ((VhpiImpl*)GpiObjHdl::m_impl)->format_to_string(m_value.format));
            }
            break;
        }
        default: {
            LOG_ERROR("Reading strings not valid for this handle");
            return "";
        }
    }
    return m_value.value.str;
}

double VhpiSignalObjHdl::get_signal_value_real(void)
{
    m_value.format = vhpiRealVal;
    m_value.numElems = 1;
    m_value.bufSize = sizeof(double);

    if (vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &m_value)) {
        check_vhpi_error();
        LOG_ERROR("failed to get real value");
    }
    return m_value.value.real;
}

long VhpiSignalObjHdl::get_signal_value_long(void)
{
    vhpiValueT value;
    value.format = vhpiIntVal;
    value.numElems = 0;

    if (vhpi_get_value(GpiObjHdl::get_handle<vhpiHandleT>(), &value)) {
        check_vhpi_error();
        LOG_ERROR("failed to get long value");
    }

    return value.value.intg;
}


GpiCbHdl * VhpiSignalObjHdl::value_change_cb(unsigned int edge)
{
    VhpiValueCbHdl *cb = NULL;

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

    return cb;
}

VhpiValueCbHdl::VhpiValueCbHdl(GpiImplInterface *impl,
                               VhpiSignalObjHdl *sig,
                               int edge) : GpiCbHdl(impl),
                                           VhpiCbHdl(impl),
                                           GpiValueCbHdl(impl,sig,edge)
{
    cb_data.reason = vhpiCbValueChange;
    cb_data.time = &vhpi_time;
    cb_data.obj = m_signal->get_handle<vhpiHandleT>();
}

VhpiStartupCbHdl::VhpiStartupCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                             VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbStartOfSimulation;
}

int VhpiStartupCbHdl::run_callback(void) {
    gpi_sim_info_t sim_info;
    sim_info.argc = 0;
    sim_info.argv = NULL;
    sim_info.product = gpi_copy_name(vhpi_get_str(vhpiNameP, NULL));
    sim_info.version = gpi_copy_name(vhpi_get_str(vhpiToolVersionP, NULL));
    gpi_embed_init(&sim_info);

    free(sim_info.product);
    free(sim_info.version);

    return 0;
}

VhpiShutdownCbHdl::VhpiShutdownCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbEndOfSimulation;
}

int VhpiShutdownCbHdl::run_callback(void) {
    set_call_state(GPI_DELETE);
    gpi_embed_end();
    return 0;
}

VhpiTimedCbHdl::VhpiTimedCbHdl(GpiImplInterface *impl, uint64_t time_ps) : GpiCbHdl(impl),
                                                                           VhpiCbHdl(impl)
{
    vhpi_time.high = (uint32_t)(time_ps>>32);
    vhpi_time.low  = (uint32_t)(time_ps); 

    cb_data.reason = vhpiCbAfterDelay;
    cb_data.time = &vhpi_time;
}

int VhpiTimedCbHdl::cleanup_callback(void)
{
    if (m_state == GPI_FREE)
        return 1;

    vhpi_remove_cb(get_handle<vhpiHandleT>());

    m_obj_hdl = NULL;
    m_state = GPI_FREE;
    return 1;
}

VhpiReadwriteCbHdl::VhpiReadwriteCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                                 VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepEndOfProcesses;
    cb_data.time = &vhpi_time;
}

VhpiReadOnlyCbHdl::VhpiReadOnlyCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                               VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepLastKnownDeltaCycle;
    cb_data.time = &vhpi_time;
}

VhpiNextPhaseCbHdl::VhpiNextPhaseCbHdl(GpiImplInterface *impl) : GpiCbHdl(impl),
                                                                 VhpiCbHdl(impl)
{
    cb_data.reason = vhpiCbRepNextTimeStep;
    cb_data.time = &vhpi_time;
}

void vhpi_mappings(GpiIteratorMapping<vhpiClassKindT, vhpiOneToManyT> &map)
{
    /* vhpiRootInstK */
    vhpiOneToManyT root_options[] = {
        vhpiInternalRegions,
        vhpiSigDecls,
        vhpiVarDecls,
        vhpiPortDecls,
        vhpiGenericDecls,
        //    vhpiIndexedNames,
        vhpiCompInstStmts,
        vhpiBlockStmts,
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiRootInstK, &root_options[0]);

    /* vhpiSigDeclK */
    vhpiOneToManyT sig_options[] = {
        vhpiIndexedNames,
        vhpiSelectedNames,
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiGenericDeclK, &sig_options[0]);
    map.add_to_options(vhpiSigDeclK, &sig_options[0]);

    /* vhpiIndexedNameK */
    map.add_to_options(vhpiSelectedNameK, &sig_options[0]);
    map.add_to_options(vhpiIndexedNameK, &sig_options[0]);

    /* vhpiCompInstStmtK */
    map.add_to_options(vhpiCompInstStmtK, &root_options[0]);

    /* vhpiSimpleSigAssignStmtK */
    vhpiOneToManyT simplesig_options[] = {
        vhpiDecls,
        vhpiInternalRegions,
        vhpiSensitivitys,
        vhpiStmts,
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiCondSigAssignStmtK, &simplesig_options[0]);
    map.add_to_options(vhpiSimpleSigAssignStmtK, &simplesig_options[0]);
    map.add_to_options(vhpiSelectSigAssignStmtK, &simplesig_options[0]);

    /* vhpiPortDeclK */
    map.add_to_options(vhpiPortDeclK, &sig_options[0]);

    /* vhpiForGenerateK */
    vhpiOneToManyT gen_options[] = {
        vhpiDecls,
        vhpiCompInstStmts,  
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiForGenerateK, &gen_options[0]);

    /* vhpiIfGenerateK */
    vhpiOneToManyT ifgen_options[] = {
        vhpiDecls,
        vhpiInternalRegions,
        vhpiCompInstStmts,
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiIfGenerateK, &ifgen_options[0]);

    /* vhpiConstDeclK */
    vhpiOneToManyT const_options[] = {
        vhpiAttrSpecs,
        vhpiIndexedNames,
        vhpiSelectedNames,
        (vhpiOneToManyT)0,
    };
    map.add_to_options(vhpiConstDeclK, &const_options[0]);

}

GpiIteratorMapping<vhpiClassKindT, vhpiOneToManyT> VhpiIterator::iterate_over(vhpi_mappings);

VhpiIterator::VhpiIterator(GpiImplInterface *impl, GpiObjHdl *hdl) : GpiIterator(impl, hdl),
                                                                     m_iterator(NULL),
                                                                     m_iter_obj(NULL)
{
    vhpiHandleT iterator;
    vhpiHandleT vhpi_hdl = m_parent->get_handle<vhpiHandleT>();

    vhpiClassKindT type = (vhpiClassKindT)vhpi_get(vhpiKindP, vhpi_hdl);
    if (NULL == (selected = iterate_over.get_options(type))) {
        LOG_WARN("VHPI: Implementation does not know how to iterate over %s(%d)",
                 vhpi_get_str(vhpiKindStrP, vhpi_hdl), type);
        return;
    }

    /* Find the first mapping type that yields a valid iterator */
    for (one2many = selected->begin();
         one2many != selected->end();
         one2many++) {
        iterator = vhpi_iterator(*one2many, vhpi_hdl);

        if (iterator)
            break;

        LOG_DEBUG("vhpi_iterate vhpiOneToManyT=%d returned NULL", *one2many);
    }

    if (NULL == iterator) {
        LOG_DEBUG("vhpi_iterate return NULL for all relationships on %s (%d) kind:%s",
                  vhpi_get_str(vhpiCaseNameP, vhpi_hdl),
                  type,
                  vhpi_get_str(vhpiKindStrP, vhpi_hdl));
        selected = NULL;
        return;
    }

    LOG_DEBUG("Created iterator working from scope %d (%s)", 
             vhpi_get(vhpiKindP, vhpi_hdl),
             vhpi_get_str(vhpiKindStrP, vhpi_hdl));

    /* On some simulators (Aldec) vhpiRootInstK is a null level of hierachy
     * We check that something is going to come back if not we try the level
     * down
     */
    m_iter_obj = vhpi_hdl;
    m_iterator = iterator;
}

VhpiIterator::~VhpiIterator()
{
    if (m_iterator)
        vhpi_release_handle(m_iterator);
}

#define VHPI_TYPE_MIN (1000)

GpiIterator::Status VhpiIterator::next_handle(std::string &name,
                                              GpiObjHdl **hdl,
                                              void **raw_hdl)
{
    vhpiHandleT obj;
    GpiObjHdl *new_obj;

    if (!selected)
        return GpiIterator::END;

    /* We want the next object in the current mapping.
     * If the end of mapping is reached then we want to
     * try then next one until a new object is found
     */
    do {
        obj = NULL;

        if (m_iterator) {
            obj = vhpi_scan(m_iterator);

            if (obj && (vhpiProcessStmtK == vhpi_get(vhpiKindP, obj))) {
                LOG_DEBUG("Skipping %s (%s)", vhpi_get_str(vhpiFullNameP, obj),
                                              vhpi_get_str(vhpiKindStrP, obj));
                obj=NULL;
                continue;
            }

            if (obj) {
                LOG_DEBUG("Found an item %s", vhpi_get_str(vhpiFullNameP, obj));
                break;
            } else {
                LOG_DEBUG("vhpi_scan on %d returned NULL", *one2many);
            }

            LOG_DEBUG("End of vhpiOneToManyT=%d iteration", *one2many);
            m_iterator = NULL;
        } else {
            LOG_DEBUG("No valid vhpiOneToManyT=%d iterator", *one2many);
        }

        if (++one2many >= selected->end()) {
            obj = NULL;
            break;
        }
        m_iterator = vhpi_iterator(*one2many, m_iter_obj);

    } while (!obj);

    if (NULL == obj) {
        LOG_DEBUG("No more children, all relationships tested");
        return GpiIterator::END;
    }

    const char *c_name = vhpi_get_str(vhpiCaseNameP, obj);
    if (!c_name) {
        int type = vhpi_get(vhpiKindP, obj);

        if (type < VHPI_TYPE_MIN) {
            *raw_hdl = (void*)obj;
            return GpiIterator::NOT_NATIVE_NO_NAME;
        }

        LOG_DEBUG("Unable to get the name for this object of type %d", type);

        return GpiIterator::NATIVE_NO_NAME;
    }
    name = c_name;

    LOG_DEBUG("vhpi_scan found %s (%d) kind:%s name:%s", name.c_str(),
            vhpi_get(vhpiKindP, obj),
            vhpi_get_str(vhpiKindStrP, obj),
            vhpi_get_str(vhpiCaseNameP, obj));

    /* We try and create a handle internally, if this is not possible we
       return and GPI will try other implementations with the name
       */
    std::string fq_name = m_parent->get_fullname();
    if (fq_name == ":") {
        fq_name += name;
    } else {
        fq_name += "." + name;
    }
    VhpiImpl *vhpi_impl = reinterpret_cast<VhpiImpl*>(m_impl);
    new_obj = vhpi_impl->create_gpi_obj_from_handle(obj, name, fq_name);
    if (new_obj) {
        *hdl = new_obj;
        return GpiIterator::NATIVE;
    }
    else
        return GpiIterator::NOT_NATIVE;
}

