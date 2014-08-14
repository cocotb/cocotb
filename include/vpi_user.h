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

#ifndef COCOTB_VPI_USER_H_
#define COCOTB_VPI_USER_H_

/* This file (vpi_user.h) contains a limited subset of the IEEE 1394
 * standard that is required for the library to build against
 */

#include <stdarg.h>

#ifdef  __cplusplus
extern "C" {
#endif

typedef uint32_t *vpiHandle;

#define vpiNet                 36   /* scalar or vector net */
#define vpiModule              32   /* module instance */
#define vpiStructVar           618

#define vpiStop                66  /* execute simulator's $stop */
#define vpiFinish              67  /* execute simulator's $finish */
#define vpiReset               68  /* execute simulator's $reset */

#define vpiType                 1   /* type of object */
#define vpiName                 2   /* local name of object */
#define vpiFullName             3   /* full hierarchical name */

#define vpiNoDelay              1
#define vpiInertialDelay        2

typedef struct t_vpi_time
{
    int32_t type;              /* [vpiScaledRealTime,
                                   vpiSimTime,
                                   vpiSuppressTime] */
    int32_t high;              /* vpiSimTime, high */
    int32_t low;               /* vpiSimTime, low */
    double real;               /* vpiScaledRealTime */
} s_vpi_time, *p_vpi_time;

/* time types */
#define vpiScaledRealTime 1
#define vpiSimTime        2
#define vpiSuppressTime   3

/* VPI Simulator information */
typedef struct t_vpi_vlog_info
{
    int32_t   argc;
    char      **argv;
    char      *product;
    char      *version;
} s_vpi_vlog_info, *p_vpi_vlog_info;

/* generic value */
typedef struct t_vpi_value
{
    int32_t format;             /* vpi[[Bin,
                                          Oct,
                                          Dec,
                                          Hex]Str,
                                              Scalar,
                                              Int,
                                              Real,
                                              String,
                                              Vector,
                                              Strength,
                                              Suppress,
                                              Time,
                                              ObjType]Val */
    union
    {
        char                *str;       /* string value */
        int32_t                 scalar;    /* vpi[0,1,X,Z] */
        int32_t                 integer;   /* integer value */
        double                    real;      /* real value */
        struct t_vpi_time        *time;      /* time value */
        struct t_vpi_vecval      *vector;    /* vector value */
        struct t_vpi_strengthval *strength;  /* strength value */
        void                 *p_agg_value_handle; /* agg valHandle */
    } value;
} s_vpi_value, *p_vpi_value;

/* value formats */
#define vpiBinStrVal          1
#define vpiOctStrVal          2
#define vpiDecStrVal          3
#define vpiHexStrVal          4
#define vpiScalarVal          5
#define vpiIntVal             6
#define vpiRealVal            7
#define vpiStringVal          8
#define vpiVectorVal          9
#define vpiStrengthVal       10
#define vpiTimeVal           11
#define vpiObjTypeVal        12
#define vpiSuppressVal       13
#define vpiShortIntVal       14
#define vpiLongIntVal        15
#define vpiShortRealVal      16
#define vpiRawTwoStateVal    17
#define vpiRawFourStateVal   18

/* scalar values */
#define vpi0                  0
#define vpi1                  1
#define vpiZ                  2
#define vpiX                  3
#define vpiH                  4
#define vpiL                  5
#define vpiDontCare           6

/* properties */
#define vpiFile               5
#define vpiLineNo             6

/* normal callback structure */
typedef struct t_cb_data
{
    int32_t    reason;                        /* callback reason */
    int32_t    (*cb_rtn)(struct t_cb_data *); /* call routine */
    vpiHandle    obj;                           /* trigger object */
    p_vpi_time   time;                          /* callback time */
    p_vpi_value  value;                         /* trigger object value */
    int32_t    index;                         /* index of the memory word or
                                                   var select that changed */
    char   *user_data;
} s_cb_data, *p_cb_data;

#define cbValueChange             1
#define cbStmt                    2
#define cbForce                   3
#define cbRelease                 4

#define cbAtStartOfSimTime        5
#define cbReadWriteSynch          6
#define cbReadOnlySynch           7
#define cbNextSimTime             8
#define cbAfterDelay              9

#define cbEndOfCompile           10
#define cbStartOfSimulation      11
#define cbEndOfSimulation        12
#define cbError                  13
#define cbTchkViolation          14
#define cbStartOfSave            15
#define cbEndOfSave              16
#define cbStartOfRestart         17
#define cbEndOfRestart           18
#define cbStartOfReset           19
#define cbEndOfReset             20
#define cbEnterInteractive       21
#define cbExitInteractive        22
#define cbInteractiveScopeChange 23
#define cbUnresolvedSystf        24

/* Object Types */
#define vpiPort                 44
#define vpiMember               742

/* error severity levels */
#define vpiNotice               1
#define vpiWarning              2
#define vpiError                3
#define vpiSystem               4
#define vpiInternal             5

typedef struct t_vpi_error_info
{
    int32_t state;
    int32_t level;
    char *message;
    char *product;
    char *code;
    char *file;
    int32_t line;
} s_vpi_error_info, *p_vpi_error_info;


typedef struct t_vpi_systf_data {
      int32_t type;
      int32_t sysfunctype;
      const char *tfname;
      int32_t (*calltf)   (char*);
      int32_t (*compiletf)(char*);
      int32_t (*sizetf)   (char*);
      char *user_data;
} s_vpi_systf_data, *p_vpi_systf_data;

#define vpiSysTask  1
#define vpiSysFunc  2
#define vpiIntFunc  1
#define vpiSysTfCall   85
#define vpiArgument    89


extern vpiHandle  vpi_register_cb(p_cb_data cb_data_p);

extern int32_t    vpi_remove_cb(vpiHandle cb_obj);

extern vpiHandle  vpi_handle_by_name(char *name,
                                     vpiHandle scope);

extern vpiHandle  vpi_handle_by_index(vpiHandle object,
                                      int32_t indx);

extern vpiHandle  vpi_handle(int32_t type,
                             vpiHandle refHandle);

extern vpiHandle  vpi_iterate(int32_t type,
                              vpiHandle refHandle);

extern vpiHandle  vpi_scan(vpiHandle iterator);

extern char      *vpi_get_str(int32_t property,
                              vpiHandle object);

extern void       vpi_get_value(vpiHandle expr,
                                p_vpi_value value_p);

extern vpiHandle  vpi_put_value(vpiHandle object,
                                p_vpi_value value_p,
                                p_vpi_time time_p,
                                int32_t flags);

extern void       vpi_get_time(vpiHandle object,
                               p_vpi_time time_p);

extern int32_t    vpi_get(int property,
                          vpiHandle ref);

extern int32_t    vpi_free_object(vpiHandle object);

extern int32_t    vpi_control(int32_t operation, ...);
extern vpiHandle  vpi_handle_by_multi_index(vpiHandle obj,
                                            int32_t num_index,
                                            int32_t *index_array);


extern int32_t    vpi_chk_error(p_vpi_error_info);

extern int32_t    vpi_get_vlog_info(p_vpi_vlog_info info_p);

extern vpiHandle  vpi_register_systf(p_vpi_systf_data data_p);

extern int32_t    vpi_printf(const char *fmt, ...) __attribute__((format (printf,1,2)));

extern void (*vlog_startup_routines[])(void);

#ifdef  __cplusplus
}
#endif

#endif /* COCOTB_VPI_USER_H_ */
