// Copyright cocotb contributors
// Copyright (c) 2015/16 Potential Ventures Ltd
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <bitset>
#include <cmath>
#include <cstring>
#include <string>

#include "FliImpl.h"
#include "_vendor/fli/acc_vhdl.h"
#include "gpi.h"

using std::abs;
using std::to_string;

GpiCbHdl *FliSignalObjHdl::register_value_change_callback(
    gpi_edge edge, int (*cb_func)(void *), void *cb_data) {
    if (m_is_var) {
        return NULL;
    }
    // TODO The dynamic cast here is a good reason to not declare members in
    // base classes.
    auto &cache = dynamic_cast<FliImpl *>(m_impl)->m_value_change_cache;
    auto cb = cache.acquire();
    cb->set_signal_and_edge(this, edge);
    auto err = cb->arm();
    // LCOV_EXCL_START
    if (err) {
        cache.release(cb);
        return NULL;
    }
    // LCOV_EXCL_STOP
    cb->set_cb_info(cb_func, cb_data);
    return cb;
}

int FliObjHdl::initialise(const std::string &name, const std::string &fq_name) {
    bool is_signal =
        (get_acc_type() == accSignal || get_acc_full_type() == accAliasSignal);
    mtiTypeIdT typeId;
    char *str;

    switch (get_type()) {
        case GPI_STRUCTURE:
            if (is_signal) {
                typeId = mti_GetSignalType(get_handle<mtiSignalIdT>());
            } else {
                typeId = mti_GetVarType(get_handle<mtiVariableIdT>());
            }

            m_num_elems = mti_GetNumRecordElements(typeId);
            break;
        case GPI_GENARRAY:
            m_indexable = true;
            // fall through
        case GPI_MODULE:
            m_num_elems = 1;
            break;
        default:
            LOG_ERROR("Invalid object type for FliObjHdl. (%s (%s))",
                      name.c_str(), get_type_str());
            return -1;
    }

    str = mti_GetPrimaryName(get_handle<mtiRegionIdT>());
    if (str != NULL) m_definition_name = str;

    str = mti_GetRegionSourceName(get_handle<mtiRegionIdT>());
    if (str != NULL) m_definition_file = str;

    return GpiObjHdl::initialise(name, fq_name);
}

int FliSignalObjHdl::initialise(const std::string &name,
                                const std::string &fq_name) {
    return GpiObjHdl::initialise(name, fq_name);
}

int FliValueObjHdl::initialise(const std::string &name,
                               const std::string &fq_name) {
    if (get_type() == GPI_ARRAY) {
        m_range_left = mti_TickLeft(m_val_type);
        m_range_right = mti_TickRight(m_val_type);
        m_range_dir = static_cast<gpi_range_dir>(mti_TickDir(m_val_type));
        m_num_elems = mti_TickLength(m_val_type);
        m_indexable = true;
    }

    return FliSignalObjHdl::initialise(name, fq_name);
}

const char *FliValueObjHdl::get_signal_value_binstr() {
    LOG_ERROR(
        "Getting signal/variable value as binstr not supported for %s of type "
        "%d",
        m_fullname.c_str(), m_type);
    return NULL;
}

const char *FliValueObjHdl::get_signal_value_str() {
    LOG_ERROR(
        "Getting signal/variable value as str not supported for %s of type %d",
        m_fullname.c_str(), m_type);
    return NULL;
}

double FliValueObjHdl::get_signal_value_real() {
    LOG_ERROR(
        "Getting signal/variable value as double not supported for %s of type "
        "%d",
        m_fullname.c_str(), m_type);
    return -1;
}

long FliValueObjHdl::get_signal_value_long() {
    LOG_ERROR(
        "Getting signal/variable value as long not supported for %s of type %d",
        m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value(int32_t, gpi_set_action) {
    LOG_ERROR(
        "Setting signal/variable value via int32_t not supported for %s of "
        "type %d",
        m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value_binstr(std::string &, gpi_set_action) {
    LOG_ERROR(
        "Setting signal/variable value via string not supported for %s of type "
        "%d",
        m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value_str(std::string &, gpi_set_action) {
    LOG_ERROR(
        "Setting signal/variable value via string not supported for %s of type "
        "%d",
        m_fullname.c_str(), m_type);
    return -1;
}

int FliValueObjHdl::set_signal_value(double, gpi_set_action) {
    LOG_ERROR(
        "Setting signal/variable value via double not supported for %s of type "
        "%d",
        m_fullname.c_str(), m_type);
    return -1;
}

void *FliValueObjHdl::get_sub_hdl(int index) {
    if (!m_indexable) return NULL;

    if (m_sub_hdls == NULL) {
        if (m_is_var) {
            m_sub_hdls = (void **)mti_GetVarSubelements(
                get_handle<mtiVariableIdT>(), NULL);
        } else {
            m_sub_hdls = (void **)mti_GetSignalSubelements(
                get_handle<mtiSignalIdT>(), NULL);
        }
    }

    int idx;

    if (m_range_left > m_range_right) {
        idx = m_range_left - index;
    } else {
        idx = index - m_range_left;
    }

    if (idx < 0 || idx >= m_num_elems)
        return NULL;
    else
        return m_sub_hdls[idx];
}

int FliEnumObjHdl::initialise(const std::string &name,
                              const std::string &fq_name) {
    m_num_elems = 1;
    m_value_enum = mti_GetEnumValues(m_val_type);
    m_num_enum = mti_TickLength(m_val_type);

    return FliValueObjHdl::initialise(name, fq_name);
}

const char *FliEnumObjHdl::get_signal_value_str() {
    if (m_is_var) {
        return m_value_enum[mti_GetVarValue(get_handle<mtiVariableIdT>())];
    } else {
        return m_value_enum[mti_GetSignalValue(get_handle<mtiSignalIdT>())];
    }
}

long FliEnumObjHdl::get_signal_value_long() {
    if (m_is_var) {
        return (long)mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        return (long)mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }
}

int FliEnumObjHdl::set_signal_value(const int32_t value,
                                    const gpi_set_action action) {
    if (value > m_num_enum || value < 0) {
        LOG_ERROR(
            "Attempted to set an enum with range [0,%d] with invalid value %d!",
            m_num_enum, value);
        return -1;
    }

    if (m_is_var) {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                static_cast<mtiLongT>(value));
                return 0;
            case GPI_FORCE:
                LOG_ERROR("Forcing VHDL variables is not supported by the FLI");
                return -1;
            case GPI_RELEASE:
                LOG_ERROR(
                    "Releasing VHDL variables is not supported by the FLI");
                return -1;
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    } else {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                   static_cast<mtiLongT>(value));
                return 0;
            case GPI_FORCE: {
                std::string value_str = "10#";
                value_str.append(to_string(abs(value)));
                return !mti_ForceSignal(get_handle<mtiSignalIdT>(),
                                        const_cast<char *>(value_str.c_str()),
                                        0, MTI_FORCE_FREEZE, -1, -1);
            }
            case GPI_RELEASE:
                return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    }
}

int FliLogicObjHdl::initialise(const std::string &name,
                               const std::string &fq_name) {
    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            m_num_elems = 1;
            m_value_enum = mti_GetEnumValues(m_val_type);
            m_num_enum = mti_TickLength(m_val_type);
            break;
        case MTI_TYPE_ARRAY: {
            mtiTypeIdT elemType = mti_GetArrayElementType(m_val_type);

            m_range_left = mti_TickLeft(m_val_type);
            m_range_right = mti_TickRight(m_val_type);
            m_range_dir = static_cast<gpi_range_dir>(mti_TickDir(m_val_type));
            m_num_elems = mti_TickLength(m_val_type);
            m_indexable = true;

            m_value_enum = mti_GetEnumValues(elemType);
            m_num_enum = mti_TickLength(elemType);

            m_mti_buff = new char[m_num_elems + 1];
        } break;
        default:
            LOG_ERROR("Object type is not 'logic' for %s (%d)", name.c_str(),
                      m_fli_type);
            return -1;
    }

    for (mtiInt32T i = 0; i < m_num_enum; i++) {
        m_enum_map[m_value_enum[i][1]] =
            i;  // enum is of the format 'U' or '0', etc.
    }

    m_val_buff = new char[m_num_elems + 1];
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char *FliLogicObjHdl::get_signal_value_binstr() {
    switch (m_fli_type) {
        case MTI_TYPE_ENUM:
            if (m_is_var) {
                m_val_buff[0] =
                    m_value_enum[mti_GetVarValue(get_handle<mtiVariableIdT>())]
                                [1];
            } else {
                m_val_buff[0] =
                    m_value_enum[mti_GetSignalValue(get_handle<mtiSignalIdT>())]
                                [1];
            }
            break;
        case MTI_TYPE_ARRAY: {
            if (m_is_var) {
                mti_GetArrayVarValue(get_handle<mtiVariableIdT>(), m_mti_buff);
            } else {
                mti_GetArraySignalValue(get_handle<mtiSignalIdT>(), m_mti_buff);
            }

            for (int i = 0; i < m_num_elems; i++) {
                m_val_buff[i] = m_value_enum[(int)m_mti_buff[i]][1];
            }
        } break;
        default:
            LOG_ERROR("Object type is not 'logic' for %s (%d)", m_name.c_str(),
                      m_fli_type);
            return NULL;
    }

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff,
              m_name.c_str());

    return m_val_buff;
}

int FliLogicObjHdl::set_signal_value(const int32_t value,
                                     const gpi_set_action action) {
    if (m_fli_type == MTI_TYPE_ENUM) {
        mtiInt32T enumVal = value ? m_enum_map['1'] : m_enum_map['0'];

        if (m_is_var) {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetVarValue(get_handle<mtiVariableIdT>(), enumVal);
                    return 0;
                case GPI_FORCE:
                    LOG_ERROR(
                        "Forcing VHDL variables is not supported by the FLI");
                    return -1;
                case GPI_RELEASE:
                    LOG_ERROR(
                        "Releasing VHDL variables is not supported by the FLI");
                    return -1;
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        } else {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetSignalValue(get_handle<mtiSignalIdT>(), enumVal);
                    return 0;
                case GPI_FORCE: {
                    char const *value_str = (value ? "2#1" : "2#0");
                    return !mti_ForceSignal(get_handle<mtiSignalIdT>(),
                                            const_cast<char *>(value_str), 0,
                                            MTI_FORCE_FREEZE, -1, -1);
                }
                case GPI_RELEASE:
                    return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        }
    } else {
        for (int i = 0, idx = m_num_elems - 1; i < m_num_elems; i++, idx--) {
            mtiInt32T enumVal =
                value & (1 << i) ? m_enum_map['1'] : m_enum_map['0'];

            m_mti_buff[idx] = (char)enumVal;
        }

        if (m_is_var) {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                    (mtiLongT)m_mti_buff);
                    return 0;
                case GPI_FORCE:
                    LOG_ERROR(
                        "Forcing VHDL variables is not supported by the FLI");
                    return -1;
                case GPI_RELEASE:
                    LOG_ERROR(
                        "Releasing VHDL variables is not supported by the FLI");
                    return -1;
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        } else {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                       (mtiLongT)m_mti_buff);
                    return 0;
                case GPI_FORCE: {
                    std::string value_str = "2#";
                    for (int idx = m_num_elems - 1; idx >= 0; idx--) {
                        value_str.append((value & (1 << idx)) ? "1" : "0");
                    }
                    return !mti_ForceSignal(
                        get_handle<mtiSignalIdT>(),
                        const_cast<char *>(value_str.c_str()), 0,
                        MTI_FORCE_FREEZE, -1, -1);
                }
                case GPI_RELEASE:
                    return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        }
    }
}

int FliLogicObjHdl::set_signal_value_binstr(std::string &value,
                                            const gpi_set_action action) {
    if (m_fli_type == MTI_TYPE_ENUM) {
        if (value.length() != 1) {
            LOG_ERROR(
                "FLI: Unable to set logic vector due to the string having "
                "incorrect length. Length of %d needs to be 1",
                value.length());
            return -1;
        }
        mtiInt32T enumVal = m_enum_map[value.c_str()[0]];

        if (m_is_var) {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetVarValue(get_handle<mtiVariableIdT>(), enumVal);
                    return 0;
                case GPI_FORCE:
                    LOG_ERROR(
                        "Forcing VHDL variables is not supported by the FLI");
                    return -1;
                case GPI_RELEASE:
                    LOG_ERROR(
                        "Releasing VHDL variables is not supported by the FLI");
                    return -1;
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        } else {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetSignalValue(get_handle<mtiSignalIdT>(), enumVal);
                    return 0;
                case GPI_FORCE: {
                    std::string value_str = "2#";
                    value_str.append(value);
                    return !mti_ForceSignal(
                        get_handle<mtiSignalIdT>(),
                        const_cast<char *>(value_str.c_str()), 0,
                        MTI_FORCE_FREEZE, -1, -1);
                }
                case GPI_RELEASE:
                    return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        }
    } else {
        if ((int)value.length() != m_num_elems) {
            LOG_ERROR(
                "FLI: Unable to set logic vector due to the string having "
                "incorrect length.  Length of %d needs to be %d",
                value.length(), m_num_elems);
            return -1;
        }

        int i = 0;

        for (auto valIter = value.begin();
             (valIter != value.end()) && (i < m_num_elems); valIter++, i++) {
            auto enumVal = m_enum_map[*valIter];
            m_mti_buff[i] = (char)enumVal;
        }

        if (m_is_var) {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                    (mtiLongT)m_mti_buff);
                    return 0;
                case GPI_FORCE:
                    LOG_ERROR(
                        "Forcing VHDL variables is not supported by the FLI");
                    return -1;
                case GPI_RELEASE:
                    LOG_ERROR(
                        "Releasing VHDL variables is not supported by the FLI");
                    return -1;
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        } else {
            switch (action) {
                case GPI_DEPOSIT:
                case GPI_NO_DELAY:
                    mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                       (mtiLongT)m_mti_buff);
                    return 0;
                case GPI_FORCE: {
                    std::string value_str = "2#";
                    value_str.append(value);
                    return !mti_ForceSignal(
                        get_handle<mtiSignalIdT>(),
                        const_cast<char *>(value_str.c_str()), 0,
                        MTI_FORCE_FREEZE, -1, -1);
                }
                case GPI_RELEASE:
                    return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
                default:
                    LOG_ERROR("Unknown set value action (%d)", action);
                    return -1;
            }
        }
    }
}

int FliIntObjHdl::initialise(const std::string &name,
                             const std::string &fq_name) {
    m_num_elems = 1;

    m_val_buff = new char[33];  // Integers are always 32-bits
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char *FliIntObjHdl::get_signal_value_binstr() {
    mtiInt32T val;

    if (m_is_var) {
        val = mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        val = mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }

    unsigned long tmp = static_cast<unsigned long>(
        val);  // only way to keep next line from warning
    std::bitset<32> value{tmp};
    std::string bin_str = value.to_string<char, std::string::traits_type,
                                          std::string::allocator_type>();
    snprintf(m_val_buff, 33, "%s", bin_str.c_str());

    return m_val_buff;
}

long FliIntObjHdl::get_signal_value_long() {
    mtiInt32T value;

    if (m_is_var) {
        value = mti_GetVarValue(get_handle<mtiVariableIdT>());
    } else {
        value = mti_GetSignalValue(get_handle<mtiSignalIdT>());
    }

    return (long)value;
}

int FliIntObjHdl::set_signal_value(const int32_t value,
                                   const gpi_set_action action) {
    if (m_is_var) {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                static_cast<mtiLongT>(value));
                return 0;
            case GPI_FORCE:
                LOG_ERROR("Forcing VHDL variables is not supported by the FLI");
                return -1;
            case GPI_RELEASE:
                LOG_ERROR(
                    "Releasing VHDL variables is not supported by the FLI");
                return -1;
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    } else {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                   static_cast<mtiLongT>(value));
                return 0;
            case GPI_FORCE: {
                std::string value_str;
                if (value < 0) {
                    value_str.append("-");
                }
                value_str.append("10#");
                value_str.append(to_string(abs(value)));
                return !mti_ForceSignal(get_handle<mtiSignalIdT>(),
                                        const_cast<char *>(value_str.c_str()),
                                        0, MTI_FORCE_FREEZE, -1, -1);
            }
            case GPI_RELEASE:
                return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    }
}

int FliRealObjHdl::initialise(const std::string &name,
                              const std::string &fq_name) {
    m_num_elems = 1;

    m_mti_buff = new double;

    return FliValueObjHdl::initialise(name, fq_name);
}

double FliRealObjHdl::get_signal_value_real() {
    if (m_is_var) {
        mti_GetVarValueIndirect(get_handle<mtiVariableIdT>(), m_mti_buff);
    } else {
        mti_GetSignalValueIndirect(get_handle<mtiSignalIdT>(), m_mti_buff);
    }

    LOG_DEBUG("Retrieved \"%f\" for value object %s", m_mti_buff[0],
              m_name.c_str());

    return m_mti_buff[0];
}

int FliRealObjHdl::set_signal_value(const double value,
                                    const gpi_set_action action) {
    m_mti_buff[0] = value;

    if (m_is_var) {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                (mtiLongT)m_mti_buff);
                return 0;
            case GPI_FORCE:
                LOG_ERROR("Forcing VHDL variables is not supported by the FLI");
                return -1;
            case GPI_RELEASE:
                LOG_ERROR(
                    "Releasing VHDL variables is not supported by the FLI");
                return -1;
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    } else {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                   (mtiLongT)m_mti_buff);
                return 0;
            case GPI_FORCE: {
                LOG_ERROR("Cannot force a real signal with the FLI");
                return -1;
            }
            case GPI_RELEASE:
                mti_ReleaseSignal(get_handle<mtiSignalIdT>());
                return 0;
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    }
}

int FliStringObjHdl::initialise(const std::string &name,
                                const std::string &fq_name) {
    m_range_left = mti_TickLeft(m_val_type);
    m_range_right = mti_TickRight(m_val_type);
    m_range_dir = static_cast<gpi_range_dir>(mti_TickDir(m_val_type));
    m_num_elems = mti_TickLength(m_val_type);
    m_indexable = true;

    m_mti_buff = new char[m_num_elems];

    m_val_buff = new char[m_num_elems + 1];
    m_val_buff[m_num_elems] = '\0';

    return FliValueObjHdl::initialise(name, fq_name);
}

const char *FliStringObjHdl::get_signal_value_str() {
    if (m_is_var) {
        mti_GetArrayVarValue(get_handle<mtiVariableIdT>(), m_mti_buff);
    } else {
        mti_GetArraySignalValue(get_handle<mtiSignalIdT>(), m_mti_buff);
    }

    strncpy(m_val_buff, m_mti_buff, static_cast<size_t>(m_num_elems));

    LOG_DEBUG("Retrieved \"%s\" for value object %s", m_val_buff,
              m_name.c_str());

    return m_val_buff;
}

int FliStringObjHdl::set_signal_value_str(std::string &value,
                                          const gpi_set_action action) {
    strncpy(m_mti_buff, value.c_str(), static_cast<size_t>(m_num_elems));

    if (m_is_var) {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetVarValue(get_handle<mtiVariableIdT>(),
                                (mtiLongT)m_mti_buff);
                return 0;
            case GPI_FORCE:
                LOG_ERROR("Forcing VHDL variables is not supported by the FLI");
                return -1;
            case GPI_RELEASE:
                LOG_ERROR(
                    "Releasing VHDL variables is not supported by the FLI");
                return -1;
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    } else {
        switch (action) {
            case GPI_DEPOSIT:
            case GPI_NO_DELAY:
                mti_SetSignalValue(get_handle<mtiSignalIdT>(),
                                   (mtiLongT)m_mti_buff);
                return 0;
            case GPI_FORCE: {
                return !mti_ForceSignal(get_handle<mtiSignalIdT>(),
                                        const_cast<char *>(value.c_str()), 0,
                                        MTI_FORCE_FREEZE, -1, -1);
            }
            case GPI_RELEASE:
                return !mti_ReleaseSignal(get_handle<mtiSignalIdT>());
            default:
                LOG_ERROR("Unknown set value action (%d)", action);
                return -1;
        }
    }
}
