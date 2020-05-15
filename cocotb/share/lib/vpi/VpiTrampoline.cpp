// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "VpiImpl.h"
#include <cinttypes>
#include <Windows.h>

/* Define function pointers for routines */

typedef vpiHandle  (*fptr_vpi_register_cb)     (p_cb_data);
typedef PLI_INT32  (*fptr_vpi_remove_cb)       (vpiHandle);
typedef void       (*fptr_vpi_get_cb_info)     (vpiHandle, p_cb_data);
typedef vpiHandle  (*fptr_vpi_register_systf)  (p_vpi_systf_data);
typedef void       (*fptr_vpi_get_systf_info)  (vpiHandle, p_vpi_systf_data);
typedef vpiHandle  (*fptr_vpi_handle_by_name)  (PLI_BYTE8 *,  vpiHandle);
typedef vpiHandle  (*fptr_vpi_handle_by_index) (vpiHandle, PLI_INT32);

typedef vpiHandle  (*fptr_vpi_handle)          (PLI_INT32, vpiHandle);
typedef vpiHandle  (*fptr_vpi_handle_multi)    (PLI_INT32, vpiHandle, vpiHandle, ...);
typedef vpiHandle  (*fptr_vpi_iterate)         (PLI_INT32, vpiHandle);
typedef vpiHandle  (*fptr_vpi_scan)            (vpiHandle);

typedef PLI_INT32  (*fptr_vpi_get)             (PLI_INT32, vpiHandle);
typedef PLI_INT64  (*fptr_vpi_get64)           (PLI_INT32, vpiHandle);
typedef PLI_BYTE8 *(*fptr_vpi_get_str)         (PLI_INT32, vpiHandle);

typedef void       (*fptr_vpi_get_delays)      (vpiHandle, p_vpi_delay);
typedef void       (*fptr_vpi_put_delays)      (vpiHandle, p_vpi_delay);

typedef void       (*fptr_vpi_get_value)       (vpiHandle, p_vpi_value);
typedef vpiHandle  (*fptr_vpi_put_value)       (vpiHandle, p_vpi_value, p_vpi_time, PLI_INT32);
typedef void       (*fptr_vpi_get_value_array) (vpiHandle, p_vpi_arrayvalue, PLI_INT32 *, PLI_UINT32);

typedef void       (*fptr_vpi_put_value_array) (vpiHandle, p_vpi_arrayvalue, PLI_INT32 *, PLI_UINT32);

typedef void       (*fptr_vpi_get_time)        (vpiHandle, p_vpi_time);

typedef PLI_UINT32 (*fptr_vpi_mcd_open)        (const PLI_BYTE8 *);
typedef PLI_UINT32 (*fptr_vpi_mcd_close)       (PLI_UINT32);
typedef PLI_BYTE8 *(*fptr_vpi_mcd_name)        (PLI_UINT32);
typedef PLI_INT32  (*fptr_vpi_mcd_printf)      (PLI_UINT32, const PLI_BYTE8 *, ...);
typedef PLI_INT32  (*fptr_vpi_printf)          (const PLI_BYTE8 *, ...);

typedef PLI_INT32  (*fptr_vpi_compare_objects) (vpiHandle, vpiHandle);
typedef PLI_INT32  (*fptr_vpi_chk_error)       (p_vpi_error_info);
typedef PLI_INT32  (*fptr_vpi_free_object)     (vpiHandle);
typedef PLI_INT32  (*fptr_vpi_release_handle)  (vpiHandle);
typedef PLI_INT32  (*fptr_vpi_get_vlog_info)   (p_vpi_vlog_info);

/* Routines added with 1364-2001 */

typedef PLI_INT32  (*fptr_vpi_get_data)        (PLI_INT32, PLI_BYTE8 *, PLI_INT32);
typedef PLI_INT32  (*fptr_vpi_put_data)        (PLI_INT32, PLI_BYTE8 *, PLI_INT32);
typedef void      *(*fptr_vpi_get_userdata)    (vpiHandle);
typedef PLI_INT32  (*fptr_vpi_put_userdata)    (vpiHandle, void *);
typedef PLI_INT32  (*fptr_vpi_vprintf)         (const PLI_BYTE8 *, va_list);
typedef PLI_INT32  (*fptr_vpi_mcd_vprintf)     (PLI_UINT32, const PLI_BYTE8 *, va_list);
typedef PLI_INT32  (*fptr_vpi_flush)           (void);
typedef PLI_INT32  (*fptr_vpi_mcd_flush)       (PLI_UINT32);
typedef PLI_INT32  (*fptr_vpi_control)         (PLI_INT32, ...);
typedef vpiHandle  (*fptr_vpi_handle_by_multi_index) (vpiHandle, PLI_INT32, PLI_INT32 *);

namespace {
class VpiTrampoline
{
    public:
        static vpiHandle  vpi_register_cb     (p_cb_data cb_data_p)                                                                 { static fptr_vpi_register_cb          f = reinterpret_cast<fptr_vpi_register_cb>          (resolve_function("vpi_register_cb"          )); return f(cb_data_p);                          }
        static PLI_INT32  vpi_remove_cb       (vpiHandle cb_obj)                                                                    { static fptr_vpi_remove_cb            f = reinterpret_cast<fptr_vpi_remove_cb>            (resolve_function("vpi_remove_cb"            )); return f(cb_obj);                             }
        static void       vpi_get_cb_info     (vpiHandle object, p_cb_data cb_data_p)                                               { static fptr_vpi_get_cb_info          f = reinterpret_cast<fptr_vpi_get_cb_info>          (resolve_function("vpi_get_cb_info"          ));        f(object, cb_data_p);                  }
        static vpiHandle  vpi_register_systf  (p_vpi_systf_data systf_data_p)                                                       { static fptr_vpi_register_systf       f = reinterpret_cast<fptr_vpi_register_systf>       (resolve_function("vpi_register_systf"       )); return f(systf_data_p);                       }
        static void       vpi_get_systf_info  (vpiHandle object, p_vpi_systf_data systf_data_p)                                     { static fptr_vpi_get_systf_info       f = reinterpret_cast<fptr_vpi_get_systf_info>       (resolve_function("vpi_get_systf_info"       ));        f(object, systf_data_p);               }
        static vpiHandle  vpi_handle_by_name  (PLI_BYTE8 *name,  vpiHandle scope)                                                   { static fptr_vpi_handle_by_name       f = reinterpret_cast<fptr_vpi_handle_by_name>       (resolve_function("vpi_handle_by_name"       )); return f(name, scope);                        }
        static vpiHandle  vpi_handle_by_index (vpiHandle object, PLI_INT32 indx)                                                    { static fptr_vpi_handle_by_index      f = reinterpret_cast<fptr_vpi_handle_by_index>      (resolve_function("vpi_handle_by_index"      )); return f(object, indx);                       }

        static vpiHandle  vpi_handle          (PLI_INT32 type, vpiHandle refHandle)                                                 { static fptr_vpi_handle               f = reinterpret_cast<fptr_vpi_handle>               (resolve_function("vpi_handle"               )); return f(type, refHandle);                    }
        static vpiHandle  vpi_handle_multi    (PLI_INT32 type, vpiHandle refHandle1, vpiHandle refHandle2, ...)                     { static fptr_vpi_handle_multi         f = reinterpret_cast<fptr_vpi_handle_multi>         (resolve_function("vpi_handle_multi"         )); return f(type, refHandle1, refHandle2);       } // Upto 1364-2005 all applicable types take a maximum of 2 refHandles
        static vpiHandle  vpi_iterate         (PLI_INT32 type, vpiHandle refHandle)                                                 { static fptr_vpi_iterate              f = reinterpret_cast<fptr_vpi_iterate>              (resolve_function("vpi_iterate"              )); return f(type, refHandle);                    }
        static vpiHandle  vpi_scan            (vpiHandle iterator)                                                                  { static fptr_vpi_scan                 f = reinterpret_cast<fptr_vpi_scan>                 (resolve_function("vpi_scan"                 )); return f(iterator);                           }

        static PLI_INT32  vpi_get             (PLI_INT32 property, vpiHandle object)                                                { static fptr_vpi_get                  f = reinterpret_cast<fptr_vpi_get>                  (resolve_function("vpi_get"                  )); return f(property, object);                   }
        static PLI_INT64  vpi_get64           (PLI_INT32 property, vpiHandle object)                                                { static fptr_vpi_get64                f = reinterpret_cast<fptr_vpi_get64>                (resolve_function("vpi_get64"                )); return f(property, object);                   }
        static PLI_BYTE8 *vpi_get_str         (PLI_INT32 property, vpiHandle object)                                                { static fptr_vpi_get_str              f = reinterpret_cast<fptr_vpi_get_str>              (resolve_function("vpi_get_str"              )); return f(property, object);                   }

        static void       vpi_get_delays      (vpiHandle object, p_vpi_delay delay_p)                                               { static fptr_vpi_get_delays           f = reinterpret_cast<fptr_vpi_get_delays>           (resolve_function("vpi_get_delays"           ));        f(object, delay_p);                    }
        static void       vpi_put_delays      (vpiHandle object, p_vpi_delay delay_p)                                               { static fptr_vpi_put_delays           f = reinterpret_cast<fptr_vpi_put_delays>           (resolve_function("vpi_put_delays"           ));        f(object, delay_p);                    }

        static void       vpi_get_value       (vpiHandle expr, p_vpi_value value_p)                                                 { static fptr_vpi_get_value            f = reinterpret_cast<fptr_vpi_get_value>            (resolve_function("vpi_get_value"            ));        f(expr, value_p);                      }
        static vpiHandle  vpi_put_value       (vpiHandle object, p_vpi_value value_p, p_vpi_time time_p, PLI_INT32 flags)           { static fptr_vpi_put_value            f = reinterpret_cast<fptr_vpi_put_value>            (resolve_function("vpi_put_value"            )); return f(object, value_p, time_p, flags);     }
        static void       vpi_get_value_array (vpiHandle expr, p_vpi_arrayvalue arrayvalue_p, PLI_INT32 *index_p, PLI_UINT32 num)   { static fptr_vpi_get_value_array      f = reinterpret_cast<fptr_vpi_get_value_array>      (resolve_function("vpi_get_value_array"      ));        f(expr, arrayvalue_p, index_p, num);   }

        static void       vpi_put_value_array (vpiHandle object, p_vpi_arrayvalue arrayvalue_p, PLI_INT32 *index_p, PLI_UINT32 num) { static fptr_vpi_put_value_array      f = reinterpret_cast<fptr_vpi_put_value_array>      (resolve_function("vpi_put_value_array"      ));        f(object, arrayvalue_p, index_p, num); }

        static void       vpi_get_time        (vpiHandle object, p_vpi_time time_p)                                                 { static fptr_vpi_get_time             f = reinterpret_cast<fptr_vpi_get_time>             (resolve_function("vpi_get_time"             ));        f(object, time_p);                     }

        static PLI_UINT32 vpi_mcd_open        (const PLI_BYTE8 *fileName)                                                           { static fptr_vpi_mcd_open             f = reinterpret_cast<fptr_vpi_mcd_open>             (resolve_function("vpi_mcd_open"             )); return f(fileName);                           }
        static PLI_UINT32 vpi_mcd_close       (PLI_UINT32 mcd)                                                                      { static fptr_vpi_mcd_close            f = reinterpret_cast<fptr_vpi_mcd_close>            (resolve_function("vpi_mcd_close"            )); return f(mcd);                                }
        static PLI_BYTE8 *vpi_mcd_name        (PLI_UINT32 cd)                                                                       { static fptr_vpi_mcd_name             f = reinterpret_cast<fptr_vpi_mcd_name>             (resolve_function("vpi_mcd_name"             )); return f(cd);                                 }
        static PLI_INT32  vpi_mcd_printf      (PLI_UINT32 mcd, const PLI_BYTE8 *format, ...)                                        { va_list ap; va_start(ap, format); PLI_INT32 ret = vpi_mcd_vprintf(mcd, format, ap); va_end(ap); return ret; }
        static PLI_INT32  vpi_printf          (const PLI_BYTE8 *format, ...)                                                        { va_list ap; va_start(ap, format); PLI_INT32 ret = vpi_vprintf(format, ap); va_end(ap); return ret; }

        static PLI_INT32  vpi_compare_objects (vpiHandle object1, vpiHandle object2)                                                { static fptr_vpi_compare_objects      f = reinterpret_cast<fptr_vpi_compare_objects>      (resolve_function("vpi_compare_objects"      )); return f(object1, object2);                   }
        static PLI_INT32  vpi_chk_error       (p_vpi_error_info error_info_p)                                                       { static fptr_vpi_chk_error            f = reinterpret_cast<fptr_vpi_chk_error>            (resolve_function("vpi_chk_error"            )); return f(error_info_p);                       }
        static PLI_INT32  vpi_free_object     (vpiHandle object)                                                                    { static fptr_vpi_free_object          f = reinterpret_cast<fptr_vpi_free_object>          (resolve_function("vpi_free_object"          )); return f(object);                             }
        static PLI_INT32  vpi_release_handle  (vpiHandle object)                                                                    { static fptr_vpi_release_handle       f = reinterpret_cast<fptr_vpi_release_handle>       (resolve_function("vpi_release_handle"       )); return f(object);                             }
        static PLI_INT32  vpi_get_vlog_info   (p_vpi_vlog_info vlog_info_p)                                                         { static fptr_vpi_get_vlog_info        f = reinterpret_cast<fptr_vpi_get_vlog_info>        (resolve_function("vpi_get_vlog_info"        )); return f(vlog_info_p);                        }

        /* Routines added with 1364-2001 */

        static PLI_INT32  vpi_get_data        (PLI_INT32 id, PLI_BYTE8 *dataLoc, PLI_INT32 numOfBytes)                             { static fptr_vpi_get_data              f = reinterpret_cast<fptr_vpi_get_data>             (resolve_function("vpi_get_data"             )); return f(id, dataLoc, numOfBytes);            }
        static PLI_INT32  vpi_put_data        (PLI_INT32 id, PLI_BYTE8 *dataLoc, PLI_INT32 numOfBytes)                             { static fptr_vpi_put_data              f = reinterpret_cast<fptr_vpi_put_data>             (resolve_function("vpi_put_data"             )); return f(id, dataLoc, numOfBytes);            }
        static void      *vpi_get_userdata    (vpiHandle obj)                                                                      { static fptr_vpi_get_userdata          f = reinterpret_cast<fptr_vpi_get_userdata>         (resolve_function("vpi_get_userdata"         )); return f(obj);                                }
        static PLI_INT32  vpi_put_userdata    (vpiHandle obj, void *userdata)                                                      { static fptr_vpi_put_userdata          f = reinterpret_cast<fptr_vpi_put_userdata>         (resolve_function("vpi_put_userdata"         )); return f(obj, userdata);                      }
        static PLI_INT32  vpi_vprintf         (const PLI_BYTE8 *format, va_list ap)                                                { static fptr_vpi_vprintf               f = reinterpret_cast<fptr_vpi_vprintf>              (resolve_function("vpi_vprintf"              )); return f(format, ap);                         }
        static PLI_INT32  vpi_mcd_vprintf     (PLI_UINT32 mcd, const PLI_BYTE8 *format, va_list ap)                                { static fptr_vpi_mcd_vprintf           f = reinterpret_cast<fptr_vpi_mcd_vprintf>          (resolve_function("vpi_mcd_vprintf"          )); return f(mcd, format, ap);                    }
        static PLI_INT32  vpi_flush           (void)                                                                               { static fptr_vpi_flush                 f = reinterpret_cast<fptr_vpi_flush>                (resolve_function("vpi_flush"                )); return f();                                   }
        static PLI_INT32  vpi_mcd_flush       (PLI_UINT32 mcd)                                                                     { static fptr_vpi_mcd_flush             f = reinterpret_cast<fptr_vpi_mcd_flush>            (resolve_function("vpi_mcd_flush"            )); return f(mcd);                                }
        static PLI_INT32  vpi_control         (PLI_INT32 operation, ...)                                                           { va_list ap; va_start(ap, operation); PLI_INT32 ret = vpi_vcontrol(operation, ap); va_end(ap); return ret; }
        static vpiHandle  vpi_handle_by_multi_index (vpiHandle obj, PLI_INT32 num_index, PLI_INT32 *index_array)                   { static fptr_vpi_handle_by_multi_index f = reinterpret_cast<fptr_vpi_handle_by_multi_index>(resolve_function("vpi_handle_by_multi_index")); return f(obj, num_index, index_array);        }

        static PLI_INT32 vpi_vcontrol         (PLI_INT32 operation, va_list ap)
        {
            static fptr_vpi_control f = reinterpret_cast<fptr_vpi_control>(resolve_function("vpi_control"));

            switch(operation)
            {
                case vpiStop:
                    return f(operation, va_arg(ap, PLI_INT32));
                case vpiFinish:
                    return f(operation, va_arg(ap, PLI_INT32));
                case vpiReset:
                    return f(operation, va_arg(ap, PLI_INT32), va_arg(ap, PLI_INT32), va_arg(ap, PLI_INT32));
                case vpiSetInteractiveScope:
                    return f(operation, va_arg(ap, vpiHandle));
                default:
                    LOG_CRITICAL("Unable to forward, operation %" PRId32 " unknown", operation);
            }
        }

    private:
        VpiTrampoline() {}

        VpiTrampoline(VpiTrampoline const&);
        void operator=(VpiTrampoline const&);

        static void *resolve_function(const char *name)
        {
#if defined(ALDEC)
            static HMODULE hModule = GetModuleHandle("aldecpli.dll");
#elif defined(GHDL)
            static HMODULE hModule = GetModuleHandle("libghdlvpi.dll");
#elif defined(ICARUS)
            static HMODULE hModule = GetModuleHandle("vvp.exe");
#elif defined(MODELSIM)
            static HMODULE hModule = GetModuleHandle("mtipli.dll");
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
   Redirect all API calls to VpiTrampoline to which resolves the function once on the first call
   and then passes execution on to the correct implementation
*/

vpiHandle  vpi_register_cb     (p_cb_data cb_data_p)                                                                 { return VpiTrampoline::vpi_register_cb(cb_data_p); }
PLI_INT32  vpi_remove_cb       (vpiHandle cb_obj)                                                                    { return VpiTrampoline::vpi_remove_cb(cb_obj); }
void       vpi_get_cb_info     (vpiHandle object, p_cb_data cb_data_p)                                               {        VpiTrampoline::vpi_get_cb_info(object, cb_data_p); }
vpiHandle  vpi_register_systf  (p_vpi_systf_data systf_data_p)                                                       { return VpiTrampoline::vpi_register_systf(systf_data_p); }
void       vpi_get_systf_info  (vpiHandle object, p_vpi_systf_data systf_data_p)                                     {        VpiTrampoline::vpi_get_systf_info(object, systf_data_p); }
vpiHandle  vpi_handle_by_name  (PLI_BYTE8 *name,  vpiHandle scope)                                                   { return VpiTrampoline::vpi_handle_by_name(name, scope); }
vpiHandle  vpi_handle_by_index (vpiHandle object, PLI_INT32 indx)                                                    { return VpiTrampoline::vpi_handle_by_index(object, indx); }

vpiHandle  vpi_handle          (PLI_INT32 type, vpiHandle refHandle)                                                 { return VpiTrampoline::vpi_handle(type, refHandle); }
vpiHandle  vpi_handle_multi    (PLI_INT32 type, vpiHandle refHandle1, vpiHandle refHandle2, ...)                     { return VpiTrampoline::vpi_handle_multi(type, refHandle1, refHandle2); } // Upto 1364-2005 all applicable types take a maximum of 2 refHandles
vpiHandle  vpi_iterate         (PLI_INT32 type, vpiHandle refHandle)                                                 { return VpiTrampoline::vpi_iterate(type, refHandle); }
vpiHandle  vpi_scan            (vpiHandle iterator)                                                                  { return VpiTrampoline::vpi_scan(iterator); }

PLI_INT32  vpi_get             (PLI_INT32 property, vpiHandle object)                                                { return VpiTrampoline::vpi_get(property, object); }
PLI_INT64  vpi_get64           (PLI_INT32 property, vpiHandle object)                                                { return VpiTrampoline::vpi_get64(property, object); }
PLI_BYTE8 *vpi_get_str         (PLI_INT32 property, vpiHandle object)                                                { return VpiTrampoline::vpi_get_str(property, object); }

void       vpi_get_delays      (vpiHandle object, p_vpi_delay delay_p)                                               {        VpiTrampoline::vpi_get_delays(object, delay_p); }
void       vpi_put_delays      (vpiHandle object, p_vpi_delay delay_p)                                               {        VpiTrampoline::vpi_put_delays(object, delay_p); }

void       vpi_get_value       (vpiHandle expr, p_vpi_value value_p)                                                 {        VpiTrampoline::vpi_get_value(expr, value_p); }
vpiHandle  vpi_put_value       (vpiHandle object, p_vpi_value value_p, p_vpi_time time_p, PLI_INT32 flags)           { return VpiTrampoline::vpi_put_value(object, value_p, time_p, flags); }
void       vpi_get_value_array (vpiHandle expr, p_vpi_arrayvalue arrayvalue_p, PLI_INT32 *index_p, PLI_UINT32 num)   {        VpiTrampoline::vpi_get_value_array(expr, arrayvalue_p, index_p, num); }

void       vpi_put_value_array (vpiHandle object, p_vpi_arrayvalue arrayvalue_p, PLI_INT32 *index_p, PLI_UINT32 num) {        VpiTrampoline::vpi_put_value_array(object, arrayvalue_p, index_p, num); }

void       vpi_get_time        (vpiHandle object, p_vpi_time time_p)                                                 {        VpiTrampoline::vpi_get_time(object, time_p); }

PLI_UINT32 vpi_mcd_open        (const PLI_BYTE8 *fileName)                                                           { return VpiTrampoline::vpi_mcd_open(fileName); }
PLI_UINT32 vpi_mcd_close       (PLI_UINT32 mcd)                                                                      { return VpiTrampoline::vpi_mcd_close(mcd); }
PLI_BYTE8 *vpi_mcd_name        (PLI_UINT32 cd)                                                                       { return VpiTrampoline::vpi_mcd_name(cd); }
PLI_INT32  vpi_mcd_printf      (PLI_UINT32 mcd, const PLI_BYTE8 *format, ...)                                        { va_list ap; va_start(ap, format); PLI_INT32 ret = VpiTrampoline::vpi_mcd_vprintf(mcd, format, ap); va_end(ap); return ret; }
PLI_INT32  vpi_printf          (const PLI_BYTE8 *format, ...)                                                        { va_list ap; va_start(ap, format); PLI_INT32 ret = vpi_vprintf(format, ap); va_end(ap); return ret; }

PLI_INT32  vpi_compare_objects (vpiHandle object1, vpiHandle object2)                                                { return VpiTrampoline::vpi_compare_objects(object1, object2); }
PLI_INT32  vpi_chk_error       (p_vpi_error_info error_info_p)                                                       { return VpiTrampoline::vpi_chk_error(error_info_p); }
PLI_INT32  vpi_free_object     (vpiHandle object)                                                                    { return VpiTrampoline::vpi_free_object(object); }
PLI_INT32  vpi_release_handle  (vpiHandle object)                                                                    { return VpiTrampoline::vpi_release_handle(object); }
PLI_INT32  vpi_get_vlog_info   (p_vpi_vlog_info vlog_info_p)                                                         { return VpiTrampoline::vpi_get_vlog_info(vlog_info_p); }

/* Routines added with 1364-2001 */

PLI_INT32  vpi_get_data        (PLI_INT32 id, PLI_BYTE8 *dataLoc, PLI_INT32 numOfBytes)                              { return VpiTrampoline::vpi_get_data(id, dataLoc, numOfBytes); }
PLI_INT32  vpi_put_data        (PLI_INT32 id, PLI_BYTE8 *dataLoc, PLI_INT32 numOfBytes)                              { return VpiTrampoline::vpi_put_data(id, dataLoc, numOfBytes); }
void      *vpi_get_userdata    (vpiHandle obj)                                                                       { return VpiTrampoline::vpi_get_userdata(obj); }
PLI_INT32  vpi_put_userdata    (vpiHandle obj, void *userdata)                                                       { return VpiTrampoline::vpi_put_userdata(obj, userdata); }
PLI_INT32  vpi_vprintf         (const PLI_BYTE8 *format, va_list ap)                                                 { return VpiTrampoline::vpi_vprintf(format, ap); }
PLI_INT32  vpi_mcd_vprintf     (PLI_UINT32 mcd, const PLI_BYTE8 *format, va_list ap)                                 { return VpiTrampoline::vpi_mcd_vprintf(mcd, format, ap); }
PLI_INT32  vpi_flush           (void)                                                                                { return VpiTrampoline::vpi_flush(); }
PLI_INT32  vpi_mcd_flush       (PLI_UINT32 mcd)                                                                      { return VpiTrampoline::vpi_mcd_flush(mcd); }
PLI_INT32  vpi_control         (PLI_INT32 operation, ...)                                                            { va_list ap; va_start(ap, operation); PLI_INT32 ret = VpiTrampoline::vpi_vcontrol(operation, ap); va_end(ap); return ret; }
vpiHandle  vpi_handle_by_multi_index (vpiHandle obj, PLI_INT32 num_index, PLI_INT32 *index_array)                    { return VpiTrampoline::vpi_handle_by_multi_index(obj, num_index, index_array); }
