// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "VhpiImpl.h"
#include <cinttypes>
#include <memory>
#include <Windows.h>

/* Define function pointers for routines */

typedef int               (*fptr_vhpi_assert)               (vhpiSeverityT, const char *, ...);
typedef vhpiHandleT       (*fptr_vhpi_register_cb)          (vhpiCbDataT *, int32_t);
typedef int               (*fptr_vhpi_remove_cb)            (vhpiHandleT);
typedef int               (*fptr_vhpi_disable_cb)           (vhpiHandleT);
typedef int               (*fptr_vhpi_enable_cb)            (vhpiHandleT);
typedef int               (*fptr_vhpi_get_cb_info)          (vhpiHandleT, vhpiCbDataT *);
typedef int               (*fptr_vhpi_sens_first)           (vhpiValueT *);
typedef int               (*fptr_vhpi_sens_zero)            (vhpiValueT *);
typedef int               (*fptr_vhpi_sens_clr)             (int, vhpiValueT *);
typedef int               (*fptr_vhpi_sens_set)             (int, vhpiValueT *);
typedef int               (*fptr_vhpi_sens_isset)           (int, vhpiValueT *);
typedef vhpiHandleT       (*fptr_vhpi_handle_by_name)       (const char *, vhpiHandleT);
typedef vhpiHandleT       (*fptr_vhpi_handle_by_index)      (vhpiOneToManyT, vhpiHandleT, int32_t);
typedef vhpiHandleT       (*fptr_vhpi_handle)               (vhpiOneToOneT, vhpiHandleT);
typedef vhpiHandleT       (*fptr_vhpi_iterator)             (vhpiOneToManyT, vhpiHandleT);
typedef vhpiHandleT       (*fptr_vhpi_scan)                 (vhpiHandleT);
typedef vhpiIntT          (*fptr_vhpi_get)                  (vhpiIntPropertyT, vhpiHandleT);
typedef const vhpiCharT * (*fptr_vhpi_get_str)              (vhpiStrPropertyT, vhpiHandleT);
typedef vhpiRealT         (*fptr_vhpi_get_real)             (vhpiRealPropertyT, vhpiHandleT);
typedef vhpiPhysT         (*fptr_vhpi_get_phys)             (vhpiPhysPropertyT, vhpiHandleT);
typedef int               (*fptr_vhpi_protected_call)       (vhpiHandleT, vhpiUserFctT, void *);
typedef int               (*fptr_vhpi_get_value)            (vhpiHandleT, vhpiValueT *);
typedef int               (*fptr_vhpi_put_value)            (vhpiHandleT, vhpiValueT *, vhpiPutValueModeT);
typedef int               (*fptr_vhpi_schedule_transaction) (vhpiHandleT, vhpiValueT *, uint32_t, vhpiTimeT *, vhpiDelayModeT, vhpiTimeT *);
typedef int               (*fptr_vhpi_format_value)         (const vhpiValueT *, vhpiValueT *);
typedef void              (*fptr_vhpi_get_time)             (vhpiTimeT *, long *);
typedef int               (*fptr_vhpi_get_next_time)        (vhpiTimeT *);
typedef int               (*fptr_vhpi_control)              (vhpiSimControlT, ...);
typedef int               (*fptr_vhpi_sim_control)          (vhpiSimControlT);
typedef int               (*fptr_vhpi_printf)               (const char *, ...);
typedef int               (*fptr_vhpi_vprintf)              (const char *, va_list);
typedef int               (*fptr_vhpi_is_printable)         (char);
typedef int               (*fptr_vhpi_compare_handles)      (vhpiHandleT, vhpiHandleT);
typedef int               (*fptr_vhpi_check_error)          (vhpiErrorInfoT *);
typedef int               (*fptr_vhpi_release_handle)       (vhpiHandleT);
typedef vhpiHandleT       (*fptr_vhpi_create)               (vhpiClassKindT, vhpiHandleT, vhpiHandleT);
typedef vhpiHandleT       (*fptr_vhpi_register_foreignf)    (vhpiForeignDataT *);
typedef int               (*fptr_vhpi_get_foreignf_info)    (vhpiHandleT, vhpiForeignDataT *);
typedef int               (*fptr_vhpi_get_foreign_info)     (vhpiHandleT, vhpiForeignDataT *);
typedef size_t            (*fptr_vhpi_get_data)             (int32_t, void *, size_t);
typedef size_t            (*fptr_vhpi_put_data)             (int32_t, void *, size_t);
typedef vhpiHandleT       (*fptr_vhpi_get_cause_instance)   (vhpiHandleT);
typedef int               (*fptr_vhpi_get_cause)            (vhpiHandleT, unsigned int**);
typedef int               (*fptr_vhpi_get_cause_info)       (const unsigned int**, int, char*, int, char*, int*);
typedef vhpiIntT          (*fptr_vhpi_value_size)           (vhpiHandleT,  vhpiFormatT);

namespace {
class VhpiTrampoline
{
    public:
        static int               vhpi_assert               (vhpiSeverityT severity, const char *formatmsg, ...)                                                                                       { va_list ap; va_start(ap, formatmsg); int ret = vhpi_vassert(severity, formatmsg, ap); va_end(ap); return ret; }
        static vhpiHandleT       vhpi_register_cb          (vhpiCbDataT *cb_data_p, int32_t flags)                                                                                                    { static fptr_vhpi_register_cb          f = reinterpret_cast<fptr_vhpi_register_cb>          (resolve_function("vhpi_register_cb"         )); return f(cb_data_p, flags);                                                                           }
        static int               vhpi_remove_cb            (vhpiHandleT cb_obj)                                                                                                                       { static fptr_vhpi_remove_cb            f = reinterpret_cast<fptr_vhpi_remove_cb>            (resolve_function("vhpi_remove_cb"           )); return f(cb_obj);                                                                                     }
        static int               vhpi_disable_cb           (vhpiHandleT cb_obj)                                                                                                                       { static fptr_vhpi_disable_cb           f = reinterpret_cast<fptr_vhpi_disable_cb>           (resolve_function("vhpi_disable_cb"          )); return f(cb_obj);                                                                                     }
        static int               vhpi_enable_cb            (vhpiHandleT cb_obj)                                                                                                                       { static fptr_vhpi_enable_cb            f = reinterpret_cast<fptr_vhpi_enable_cb>            (resolve_function("vhpi_enable_cb"           )); return f(cb_obj);                                                                                     }
        static int               vhpi_get_cb_info          (vhpiHandleT object, vhpiCbDataT *cb_data_p)                                                                                               { static fptr_vhpi_get_cb_info          f = reinterpret_cast<fptr_vhpi_get_cb_info>          (resolve_function("vhpi_get_cb_info"         )); return f(object, cb_data_p);                                                                          }
        static int               vhpi_sens_first           (vhpiValueT *sens)                                                                                                                         { static fptr_vhpi_sens_first           f = reinterpret_cast<fptr_vhpi_sens_first>           (resolve_function("vhpi_sens_first"          )); return f(sens);                                                                                       }
        static int               vhpi_sens_zero            (vhpiValueT *sens)                                                                                                                         { static fptr_vhpi_sens_zero            f = reinterpret_cast<fptr_vhpi_sens_zero>            (resolve_function("vhpi_sens_zero"           )); return f(sens);                                                                                       }
        static int               vhpi_sens_clr             (int obj, vhpiValueT *sens)                                                                                                                { static fptr_vhpi_sens_clr             f = reinterpret_cast<fptr_vhpi_sens_clr>             (resolve_function("vhpi_sens_clr"            )); return f(obj, sens);                                                                                  }
        static int               vhpi_sens_set             (int obj, vhpiValueT *sens)                                                                                                                { static fptr_vhpi_sens_set             f = reinterpret_cast<fptr_vhpi_sens_set>             (resolve_function("vhpi_sens_set"            )); return f(obj, sens);                                                                                  }
        static int               vhpi_sens_isset           (int obj, vhpiValueT *sens)                                                                                                                { static fptr_vhpi_sens_isset           f = reinterpret_cast<fptr_vhpi_sens_isset>           (resolve_function("vhpi_sens_isset"          )); return f(obj, sens);                                                                                  }
        static vhpiHandleT       vhpi_handle_by_name       (const char *name, vhpiHandleT scope)                                                                                                      { static fptr_vhpi_handle_by_name       f = reinterpret_cast<fptr_vhpi_handle_by_name>       (resolve_function("vhpi_handle_by_name"      )); return f(name, scope);                                                                                }
        static vhpiHandleT       vhpi_handle_by_index      (vhpiOneToManyT itRel, vhpiHandleT parent, int32_t indx)                                                                                   { static fptr_vhpi_handle_by_index      f = reinterpret_cast<fptr_vhpi_handle_by_index>      (resolve_function("vhpi_handle_by_index"     )); return f(itRel, parent, indx);                                                                        }
        static vhpiHandleT       vhpi_handle               (vhpiOneToOneT type, vhpiHandleT referenceHandle)                                                                                          { static fptr_vhpi_handle               f = reinterpret_cast<fptr_vhpi_handle>               (resolve_function("vhpi_handle"              )); return f(type, referenceHandle);                                                                      }
        static vhpiHandleT       vhpi_iterator             (vhpiOneToManyT type, vhpiHandleT referenceHandle)                                                                                         { static fptr_vhpi_iterator             f = reinterpret_cast<fptr_vhpi_iterator>             (resolve_function("vhpi_iterator"            )); return f(type, referenceHandle);                                                                      }
        static vhpiHandleT       vhpi_scan                 (vhpiHandleT iterator)                                                                                                                     { static fptr_vhpi_scan                 f = reinterpret_cast<fptr_vhpi_scan>                 (resolve_function("vhpi_scan"                )); return f(iterator);                                                                                   }
        static vhpiIntT          vhpi_get                  (vhpiIntPropertyT property, vhpiHandleT object)                                                                                            { static fptr_vhpi_get                  f = reinterpret_cast<fptr_vhpi_get>                  (resolve_function("vhpi_get"                 )); return f(property, object);                                                                           }
        static const vhpiCharT * vhpi_get_str              (vhpiStrPropertyT property, vhpiHandleT object)                                                                                            { static fptr_vhpi_get_str              f = reinterpret_cast<fptr_vhpi_get_str>              (resolve_function("vhpi_get_str"             )); return f(property, object);                                                                           }
        static vhpiRealT         vhpi_get_real             (vhpiRealPropertyT property, vhpiHandleT object)                                                                                           { static fptr_vhpi_get_real             f = reinterpret_cast<fptr_vhpi_get_real>             (resolve_function("vhpi_get_real"            )); return f(property, object);                                                                           }
        static vhpiPhysT         vhpi_get_phys             (vhpiPhysPropertyT property, vhpiHandleT object)                                                                                           { static fptr_vhpi_get_phys             f = reinterpret_cast<fptr_vhpi_get_phys>             (resolve_function("vhpi_get_phys"            )); return f(property, object);                                                                           }
        static int               vhpi_protected_call       (vhpiHandleT varHdl, vhpiUserFctT userFct, void *userData)                                                                                 { static fptr_vhpi_protected_call       f = reinterpret_cast<fptr_vhpi_protected_call>       (resolve_function("vhpi_protected_call"      )); return f(varHdl, userFct, userData);                                                                  }
        static int               vhpi_get_value            (vhpiHandleT expr, vhpiValueT *value_p)                                                                                                    { static fptr_vhpi_get_value            f = reinterpret_cast<fptr_vhpi_get_value>            (resolve_function("vhpi_get_value"           )); return f(expr, value_p);                                                                              }
        static int               vhpi_put_value            (vhpiHandleT object, vhpiValueT *value_p, vhpiPutValueModeT flags)                                                                         { static fptr_vhpi_put_value            f = reinterpret_cast<fptr_vhpi_put_value>            (resolve_function("vhpi_put_value"           )); return f(object, value_p, flags);                                                                     }
        static int               vhpi_schedule_transaction (vhpiHandleT drivHdl, vhpiValueT *value_p, uint32_t numValues, vhpiTimeT *delayp, vhpiDelayModeT delayMode, vhpiTimeT *pulseRejp)          { static fptr_vhpi_schedule_transaction f = reinterpret_cast<fptr_vhpi_schedule_transaction> (resolve_function("vhpi_schedule_transaction")); return f(drivHdl, value_p, numValues, delayp, delayMode, pulseRejp);                                  }
        static int               vhpi_format_value         (const vhpiValueT *in_value_p, vhpiValueT *out_value_p)                                                                                    { static fptr_vhpi_format_value         f = reinterpret_cast<fptr_vhpi_format_value>         (resolve_function("vhpi_format_value"        )); return f(in_value_p, out_value_p);                                                                    }
        static void              vhpi_get_time             (vhpiTimeT *time_p, long *cycles)                                                                                                          { static fptr_vhpi_get_time             f = reinterpret_cast<fptr_vhpi_get_time>             (resolve_function("vhpi_get_time"            ));        f(time_p, cycles);                                                                             }
        static int               vhpi_get_next_time        (vhpiTimeT *time_p)                                                                                                                        { static fptr_vhpi_get_next_time        f = reinterpret_cast<fptr_vhpi_get_next_time>        (resolve_function("vhpi_get_next_time"       )); return f(time_p);                                                                                     }
        static int               vhpi_control              (vhpiSimControlT command, ...)                                                                                                             { va_list ap; va_start(ap, command); int ret = vhpi_vcontrol(command, ap); va_end(ap); return ret; }
        static int               vhpi_sim_control          (vhpiSimControlT command)                                                                                                                  { static fptr_vhpi_sim_control          f = reinterpret_cast<fptr_vhpi_sim_control>          (resolve_function("vhpi_sim_control"         )); return f(command);                                                                                    }
        static int               vhpi_printf               (const char *format, ...)                                                                                                                  { va_list ap; va_start(ap, format); int ret = vhpi_vprintf(format, ap); va_end(ap); return ret; }
        static int               vhpi_vprintf              (const char *format, va_list args)                                                                                                         { static fptr_vhpi_vprintf              f = reinterpret_cast<fptr_vhpi_vprintf>              (resolve_function("vhpi_vprintf"             )); return f(format, args);                                                                               }
        static int               vhpi_is_printable         (char ch)                                                                                                                                  { static fptr_vhpi_is_printable         f = reinterpret_cast<fptr_vhpi_is_printable>         (resolve_function("vhpi_is_printable"        )); return f(ch);                                                                                         }
        static int               vhpi_compare_handles      (vhpiHandleT handle1, vhpiHandleT handle2)                                                                                                 { static fptr_vhpi_compare_handles      f = reinterpret_cast<fptr_vhpi_compare_handles>      (resolve_function("vhpi_compare_handles"     )); return f(handle1, handle2);                                                                           }
        static int               vhpi_check_error          (vhpiErrorInfoT *error_info_p)                                                                                                             { static fptr_vhpi_check_error          f = reinterpret_cast<fptr_vhpi_check_error>          (resolve_function("vhpi_check_error"         )); return f(error_info_p);                                                                               }
        static int               vhpi_release_handle       (vhpiHandleT object)                                                                                                                       { static fptr_vhpi_release_handle       f = reinterpret_cast<fptr_vhpi_release_handle>       (resolve_function("vhpi_release_handle"      )); return f(object);                                                                                     }
        static vhpiHandleT       vhpi_create               (vhpiClassKindT kind, vhpiHandleT handle1, vhpiHandleT handle2)                                                                            { static fptr_vhpi_create               f = reinterpret_cast<fptr_vhpi_create>               (resolve_function("vhpi_create"              )); return f(kind, handle1, handle2);                                                                     }
        static vhpiHandleT       vhpi_register_foreignf    (vhpiForeignDataT *foreignDatap)                                                                                                           { static fptr_vhpi_register_foreignf    f = reinterpret_cast<fptr_vhpi_register_foreignf>    (resolve_function("vhpi_register_foreignf"   )); return f(foreignDatap);                                                                               }
        static int               vhpi_get_foreignf_info    (vhpiHandleT hdl, vhpiForeignDataT *foreignDatap)                                                                                          { static fptr_vhpi_get_foreignf_info    f = reinterpret_cast<fptr_vhpi_get_foreignf_info>    (resolve_function("vhpi_get_foreignf_info"   )); return f(hdl, foreignDatap);                                                                          }
        static int               vhpi_get_foreign_info     (vhpiHandleT hdl, vhpiForeignDataT *foreignDatap)                                                                                          { static fptr_vhpi_get_foreign_info     f = reinterpret_cast<fptr_vhpi_get_foreign_info>     (resolve_function("vhpi_get_foreign_info"    )); return f(hdl, foreignDatap);                                                                          }
        static size_t            vhpi_get_data             (int32_t id, void *dataLoc, size_t numBytes)                                                                                               { static fptr_vhpi_get_data             f = reinterpret_cast<fptr_vhpi_get_data>             (resolve_function("vhpi_get_data"            )); return f(id, dataLoc, numBytes);                                                                      }
        static size_t            vhpi_put_data             (int32_t id, void *dataLoc, size_t numBytes)                                                                                               { static fptr_vhpi_put_data             f = reinterpret_cast<fptr_vhpi_put_data>             (resolve_function("vhpi_put_data"            )); return f(id, dataLoc, numBytes);                                                                      }
        static vhpiHandleT       vhpi_get_cause_instance   (vhpiHandleT sigHandle)                                                                                                                    { static fptr_vhpi_get_cause_instance   f = reinterpret_cast<fptr_vhpi_get_cause_instance>   (resolve_function("vhpi_get_cause_instance"  )); return f(sigHandle);                                                                                  }
        static int               vhpi_get_cause            (vhpiHandleT sigHandle, unsigned int** p2MagicNumbersBuffer)                                                                               { static fptr_vhpi_get_cause            f = reinterpret_cast<fptr_vhpi_get_cause>            (resolve_function("vhpi_get_cause"           )); return f(sigHandle, p2MagicNumbersBuffer);                                                            }
        static int               vhpi_get_cause_info       (const unsigned int** pn2MagicNumbers, int nBufLen, char* pszHierScopeBuf, int nFilePathBufLen, char* pszSourceFilePathBuf, int* pnLineNr) { static fptr_vhpi_get_cause_info       f = reinterpret_cast<fptr_vhpi_get_cause_info>       (resolve_function("vhpi_get_cause_info"      )); return f(pn2MagicNumbers, nBufLen, pszHierScopeBuf, nFilePathBufLen, pszSourceFilePathBuf, pnLineNr); }
        static vhpiIntT          vhpi_value_size           (vhpiHandleT objHdl,  vhpiFormatT format)                                                                                                  { static fptr_vhpi_value_size           f = reinterpret_cast<fptr_vhpi_value_size>           (resolve_function("vhpi_value_size"          )); return f(objHdl, format);                                                                             }

        static int               vhpi_vassert              (vhpiSeverityT severity, const char *formatmsg, va_list ap)
        {
            static fptr_vhpi_assert f = reinterpret_cast<fptr_vhpi_assert>(resolve_function("vhpi_assert"));

            va_list ap_size;
            va_copy(ap_size, ap);
            int size = vsnprintf(nullptr, 0, formatmsg, ap_size) + 1;
            if(size < 0)
                LOG_CRITICAL("Unable to format message: %s", formatmsg);
            va_end(ap_size);
            std::unique_ptr<char[]> buf(new char[size]);
            vsnprintf(buf.get(), size, formatmsg, ap);

            return f(severity, buf.get());
        }

        static int               vhpi_vcontrol             (vhpiSimControlT command, va_list ap)
        {
            static fptr_vhpi_control f = reinterpret_cast<fptr_vhpi_control>(resolve_function("vhpi_control"));

            switch(command)
            {
                case vhpiStop:
                    return f(command, va_arg(ap, int));
                case vhpiFinish:
                    return f(command, va_arg(ap, int));
                case vhpiReset:
                    return f(command, va_arg(ap, int), va_arg(ap, int), va_arg(ap, int));
                default:
                    LOG_CRITICAL("Unable to forward, operation %" PRId32 " unknown", command);
            }
        }

    private:
        VhpiTrampoline() {}

        VhpiTrampoline(VhpiTrampoline const&);
        void operator=(VhpiTrampoline const&);

        static void *resolve_function(const char *name)
        {
#if defined(ALDEC)
            static HMODULE hModule = GetModuleHandle("aldecpli.dll");
#else
#error No target module defined for trampoline
#endif
            if(!hModule)
                LOG_CRITICAL("Failed to load module");

            void *f = reinterpret_cast<void *>(GetProcAddress(hModule, name));

            if(!f)
                LOG_CRITICAL("Failed to resolve %s", name);

            return f;
        }
};
}

/*
   Redirect all API calls to VhpiTrampoline which resolves the function once on the first call
   and then passes execution on to the correct implementation
*/

int               vhpi_assert               (vhpiSeverityT severity, const char *formatmsg, ...)                                                                                       { va_list ap; va_start(ap, formatmsg); int ret = VhpiTrampoline::vhpi_vassert(severity, formatmsg, ap); va_end(ap); return ret; }
vhpiHandleT       vhpi_register_cb          (vhpiCbDataT *cb_data_p, int32_t flags)                                                                                                    { return VhpiTrampoline::vhpi_register_cb(cb_data_p, flags); }
int               vhpi_remove_cb            (vhpiHandleT cb_obj)                                                                                                                       { return VhpiTrampoline::vhpi_remove_cb(cb_obj); }
int               vhpi_disable_cb           (vhpiHandleT cb_obj)                                                                                                                       { return VhpiTrampoline::vhpi_disable_cb(cb_obj); }
int               vhpi_enable_cb            (vhpiHandleT cb_obj)                                                                                                                       { return VhpiTrampoline::vhpi_enable_cb(cb_obj); }
int               vhpi_get_cb_info          (vhpiHandleT object, vhpiCbDataT *cb_data_p)                                                                                               { return VhpiTrampoline::vhpi_get_cb_info(object, cb_data_p); }
int               vhpi_sens_first           (vhpiValueT *sens)                                                                                                                         { return VhpiTrampoline::vhpi_sens_first(sens); }
int               vhpi_sens_zero            (vhpiValueT *sens)                                                                                                                         { return VhpiTrampoline::vhpi_sens_zero(sens); }
int               vhpi_sens_clr             (int obj, vhpiValueT *sens)                                                                                                                { return VhpiTrampoline::vhpi_sens_clr(obj, sens); }
int               vhpi_sens_set             (int obj, vhpiValueT *sens)                                                                                                                { return VhpiTrampoline::vhpi_sens_set(obj, sens); }
int               vhpi_sens_isset           (int obj, vhpiValueT *sens)                                                                                                                { return VhpiTrampoline::vhpi_sens_isset(obj, sens); }
vhpiHandleT       vhpi_handle_by_name       (const char *name, vhpiHandleT scope)                                                                                                      { return VhpiTrampoline::vhpi_handle_by_name(name, scope); }
vhpiHandleT       vhpi_handle_by_index      (vhpiOneToManyT itRel, vhpiHandleT parent, int32_t indx)                                                                                   { return VhpiTrampoline::vhpi_handle_by_index(itRel, parent, indx); }
vhpiHandleT       vhpi_handle               (vhpiOneToOneT type, vhpiHandleT referenceHandle)                                                                                          { return VhpiTrampoline::vhpi_handle(type, referenceHandle); }
vhpiHandleT       vhpi_iterator             (vhpiOneToManyT type, vhpiHandleT referenceHandle)                                                                                         { return VhpiTrampoline::vhpi_iterator(type, referenceHandle); }
vhpiHandleT       vhpi_scan                 (vhpiHandleT iterator)                                                                                                                     { return VhpiTrampoline::vhpi_scan(iterator); }
vhpiIntT          vhpi_get                  (vhpiIntPropertyT property, vhpiHandleT object)                                                                                            { return VhpiTrampoline::vhpi_get(property, object); }
const vhpiCharT * vhpi_get_str              (vhpiStrPropertyT property, vhpiHandleT object)                                                                                            { return VhpiTrampoline::vhpi_get_str(property, object); }
vhpiRealT         vhpi_get_real             (vhpiRealPropertyT property, vhpiHandleT object)                                                                                           { return VhpiTrampoline::vhpi_get_real(property, object); }
vhpiPhysT         vhpi_get_phys             (vhpiPhysPropertyT property, vhpiHandleT object)                                                                                           { return VhpiTrampoline::vhpi_get_phys(property, object); }
int               vhpi_protected_call       (vhpiHandleT varHdl, vhpiUserFctT userFct, void *userData)                                                                                 { return VhpiTrampoline::vhpi_protected_call(varHdl, userFct, userData); }
int               vhpi_get_value            (vhpiHandleT expr, vhpiValueT *value_p)                                                                                                    { return VhpiTrampoline::vhpi_get_value(expr, value_p); }
int               vhpi_put_value            (vhpiHandleT object, vhpiValueT *value_p, vhpiPutValueModeT flags)                                                                         { return VhpiTrampoline::vhpi_put_value(object, value_p, flags); }
int               vhpi_schedule_transaction (vhpiHandleT drivHdl, vhpiValueT *value_p, uint32_t numValues, vhpiTimeT *delayp, vhpiDelayModeT delayMode, vhpiTimeT *pulseRejp)          { return VhpiTrampoline::vhpi_schedule_transaction(drivHdl, value_p, numValues, delayp, delayMode, pulseRejp); }
int               vhpi_format_value         (const vhpiValueT *in_value_p, vhpiValueT *out_value_p)                                                                                    { return VhpiTrampoline::vhpi_format_value(in_value_p, out_value_p); }
void              vhpi_get_time             (vhpiTimeT *time_p, long *cycles)                                                                                                          { return VhpiTrampoline::vhpi_get_time(time_p, cycles); }
int               vhpi_get_next_time        (vhpiTimeT *time_p)                                                                                                                        { return VhpiTrampoline::vhpi_get_next_time(time_p); }
int               vhpi_control              (vhpiSimControlT command, ...)                                                                                                             { va_list ap; va_start(ap, command); int ret = VhpiTrampoline::vhpi_vcontrol(command, ap); va_end(ap); return ret; }
int               vhpi_sim_control          (vhpiSimControlT command)                                                                                                                  { return VhpiTrampoline::vhpi_sim_control(command); }
int               vhpi_printf               (const char *format, ...)                                                                                                                  { va_list ap; va_start(ap, format); int ret = VhpiTrampoline::vhpi_vprintf(format, ap); va_end(ap); return ret; }
int               vhpi_vprintf              (const char *format, va_list args)                                                                                                         { return VhpiTrampoline::vhpi_vprintf(format, args); }
int               vhpi_is_printable         (char ch)                                                                                                                                  { return VhpiTrampoline::vhpi_is_printable(ch); }
int               vhpi_compare_handles      (vhpiHandleT handle1, vhpiHandleT handle2)                                                                                                 { return VhpiTrampoline::vhpi_compare_handles(handle1, handle2); }
int               vhpi_check_error          (vhpiErrorInfoT *error_info_p)                                                                                                             { return VhpiTrampoline::vhpi_check_error(error_info_p); }
int               vhpi_release_handle       (vhpiHandleT object)                                                                                                                       { return VhpiTrampoline::vhpi_release_handle(object); }
vhpiHandleT       vhpi_create               (vhpiClassKindT kind, vhpiHandleT handle1, vhpiHandleT handle2)                                                                            { return VhpiTrampoline::vhpi_create(kind, handle1, handle2); }
vhpiHandleT       vhpi_register_foreignf    (vhpiForeignDataT *foreignDatap)                                                                                                           { return VhpiTrampoline::vhpi_register_foreignf(foreignDatap); }
int               vhpi_get_foreignf_info    (vhpiHandleT hdl, vhpiForeignDataT *foreignDatap)                                                                                          { return VhpiTrampoline::vhpi_get_foreignf_info(hdl, foreignDatap); }
int               vhpi_get_foreign_info     (vhpiHandleT hdl, vhpiForeignDataT *foreignDatap)                                                                                          { return VhpiTrampoline::vhpi_get_foreign_info(hdl, foreignDatap); }
size_t            vhpi_get_data             (int32_t id, void *dataLoc, size_t numBytes)                                                                                               { return VhpiTrampoline::vhpi_get_data(id, dataLoc, numBytes); }
size_t            vhpi_put_data             (int32_t id, void *dataLoc, size_t numBytes)                                                                                               { return VhpiTrampoline::vhpi_put_data(id, dataLoc, numBytes); }
vhpiHandleT       vhpi_get_cause_instance   (vhpiHandleT sigHandle)                                                                                                                    { return VhpiTrampoline::vhpi_get_cause_instance(sigHandle); }
int               vhpi_get_cause            (vhpiHandleT sigHandle, unsigned int** p2MagicNumbersBuffer)                                                                               { return VhpiTrampoline::vhpi_get_cause(sigHandle, p2MagicNumbersBuffer); }
int               vhpi_get_cause_info       (const unsigned int** pn2MagicNumbers, int nBufLen, char* pszHierScopeBuf, int nFilePathBufLen, char* pszSourceFilePathBuf, int* pnLineNr) { return VhpiTrampoline::vhpi_get_cause_info(pn2MagicNumbers, nBufLen, pszHierScopeBuf, nFilePathBufLen, pszSourceFilePathBuf, pnLineNr); }
vhpiIntT          vhpi_value_size           (vhpiHandleT objHdl,  vhpiFormatT format)                                                                                                  { return VhpiTrampoline::vhpi_value_size(objHdl, format); }
