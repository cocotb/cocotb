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

#if !defined(__linux__) && !defined(__APPLE__)
#ifndef VPI_DLLISPEC
#define VPI_DLLISPEC __declspec(dllimport)
#define VPI_DLL_LOCAL 1
#endif
#else
#ifndef VPI_DLLISPEC
#define VPI_DLLISPEC
#endif
#endif

typedef uint32_t *vpiHandle;

/******************************** OBJECT TYPES ********************************/

#define vpiAlways                1   /* always procedure */
#define vpiAssignStmt            2   /* quasi-continuous assignment */
#define vpiAssignment            3   /* procedural assignment */
#define vpiBegin                 4   /* block statement */
#define vpiCase                  5   /* case statement */
#define vpiCaseItem              6   /* case statement item */
#define vpiConstant              7   /* numerical constant or string literal */
#define vpiContAssign            8   /* continuous assignment */
#define vpiDeassign              9   /* deassignment statement */
#define vpiDefParam             10   /* defparam */
#define vpiDelayControl         11   /* delay statement (e.g., #10) */
#define vpiDisable              12   /* named block disable statement */
#define vpiEventControl         13   /* wait on event, e.g., @e */
#define vpiEventStmt            14   /* event trigger, e.g., ->e */
#define vpiFor                  15   /* for statement */
#define vpiForce                16   /* force statement */
#define vpiForever              17   /* forever statement */
#define vpiFork                 18   /* fork-join block */
#define vpiFuncCall             19   /* function call */
#define vpiFunction             20   /* function */
#define vpiGate                 21   /* primitive gate */
#define vpiIfElse               23   /* if-else statement */
#define vpiInitial              24   /* initial procedure */
#define vpiIntegerVar           25   /* integer variable */
#define vpiInterModPath         26   /* intermodule wire delay */
#define vpiIterator             27   /* iterator */
#define vpiIODecl               28   /* input/output declaration */
#define vpiMemory               29   /* behavioral memory */
#define vpiMemoryWord           30   /* single word of memory */
#define vpiModPath              31   /* module path for path delays */
#define vpiModule               32   /* module instance */
#define vpiNamedBegin           33   /* named block statement */
#define vpiNamedEvent           34   /* event variable */
#define vpiNamedFork            35   /* named fork-join block */
#define vpiNet                  36   /* scalar or vector net */
#define vpiNetBit               37   /* bit of vector net */
#define vpiNullStmt             38   /* a semicolon. Ie. #10 ; */
#define vpiOperation            39   /* behavioral operation */
#define vpiParamAssign          40   /* module parameter assignment */
#define vpiParameter            41   /* module parameter */
#define vpiPartSelect           42   /* part-select */
#define vpiPathTerm             43   /* terminal of module path */
#define vpiPort                 44   /* module port */
#define vpiPortBit              45   /* bit of vector module port */
#define vpiPrimTerm             46   /* primitive terminal */
#define vpiRealVar              47   /* real variable */
#define vpiReg                  48   /* scalar or vector reg */
#define vpiRegBit               49   /* bit of vector reg */
#define vpiRelease              50   /* release statement */
#define vpiRepeat               51   /* repeat statement */
#define vpiRepeatControl        52   /* repeat control in an assign stmt */
#define vpiSchedEvent           53   /* vpi_put_value() event */
#define vpiSpecParam            54   /* specparam */
#define vpiSwitch               55   /* transistor switch */
#define vpiSysFuncCall          56   /* system function call */
#define vpiSysTaskCall          57   /* system task call */
#define vpiTableEntry           58   /* UDP state table entry */
#define vpiTask                 59   /* task */
#define vpiTaskCall             60   /* task call */
#define vpiTchk                 61   /* timing check */
#define vpiTchkTerm             62   /* terminal of timing check */
#define vpiTimeVar              63   /* time variable */
#define vpiTimeQueue            64   /* simulation event queue */
#define vpiUdp                  65   /* user-defined primitive */
#define vpiUdpDefn              66   /* UDP definition */
#define vpiUserSystf            67   /* user-defined system task/function */
#define vpiVarSelect            68   /* variable array selection */
#define vpiWait                 69   /* wait statement */
#define vpiWhile                70   /* while statement */


#define vpiPrimitive           103   /* primitive (gate, switch, UDP) */

/********************** object types added with 1364-2001 *********************/

#define vpiAttribute           105   /* attribute of an object */
#define vpiBitSelect           106   /* Bit-select of parameter, var select */
#define vpiCallback            107   /* callback object */
#define vpiDelayTerm           108   /* Delay term which is a load or driver */
#define vpiDelayDevice         109   /* Delay object within a net */
#define vpiFrame               110   /* reentrant task/func frame */
#define vpiGateArray           111   /* gate instance array */
#define vpiModuleArray         112   /* module instance array */
#define vpiPrimitiveArray      113   /* vpiprimitiveArray type */
#define vpiNetArray            114   /* multidimensional net */
#define vpiRange               115   /* range declaration */
#define vpiRegArray            116   /* multidimensional reg */
#define vpiSwitchArray         117   /* switch instance array */
#define vpiUdpArray            118   /* UDP instance array */
#define vpiContAssignBit       128   /* Bit of a vector continuous assignment */
#define vpiNamedEventArray     129   /* multidimensional named event */

#define vpiInterface           601
#define vpiInterfaceArray      603
#define vpiModport             606
#define vpiRefObj              608
#define vpiIntVar              612
#define vpiEnumVar             617
#define vpiStructVar           618
#define vpiPackedArrayVar      623
#define vpiEnumNet             680  /* SystemVerilog */
#define vpiIntegerNet          681
#define vpiStructNet           683


#define vpiStop                 66  /* execute simulator's $stop */
#define vpiFinish               67  /* execute simulator's $finish */
#define vpiReset                68  /* execute simulator's $reset */

/********************** object types added with 1364-2005 *********************/

#define vpiIndexedPartSelect   130   /* Indexed part-select object */
#define vpiGenScopeArray       133   /* array of generated scopes */
#define vpiGenScope            134   /* A generated scope */
#define vpiGenVar              135   /* Object used to instantiate gen scopes */

#define vpiType                  1   /* type of object */
#define vpiName                  2   /* local name of object */
#define vpiFullName              3   /* full hierarchical name */
#define vpiSize                  4   /* size of gate, net, port, etc. */

#define vpiNoDelay               1
#define vpiInertialDelay         2

/* One 2 many relationships */
#define vpiArgument             89   /* argument to (system) task/function */
#define vpiBit                  90   /* bit of vector net or port */
#define vpiDriver               91   /* driver for a net */
#define vpiInternalScope        92   /* internal scope in module */
#define vpiLoad                 93   /* load on net or reg */
#define vpiModDataPathIn        94   /* data terminal of a module path */
#define vpiModPathIn            95   /* Input terminal of a module path */
#define vpiModPathOut           96   /* output terminal of a module path */
#define vpiOperand              97   /* operand of expression */
#define vpiPortInst             98   /* connected port instance */
#define vpiProcess              99   /* process in module */
#define vpiVariables           100   /* variables in module */
#define vpiUse                 101   /* usage */

#define vpiStop                 66  /* execute simulator's $stop */
#define vpiFinish               67  /* execute simulator's $finish */
#define vpiReset                68  /* execute simulator's $reset */



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

#define vpiUnknown            3

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


extern VPI_DLLISPEC vpiHandle  vpi_register_cb(p_cb_data cb_data_p);

extern VPI_DLLISPEC int32_t    vpi_remove_cb(vpiHandle cb_obj);

extern VPI_DLLISPEC vpiHandle  vpi_handle_by_name(char *name,
                                     vpiHandle scope);

extern VPI_DLLISPEC vpiHandle  vpi_handle_by_index(vpiHandle object,
                                      int32_t indx);

extern VPI_DLLISPEC vpiHandle  vpi_handle(int32_t type,
                             vpiHandle refHandle);

extern VPI_DLLISPEC vpiHandle  vpi_iterate(int32_t type,
                              vpiHandle refHandle);

extern VPI_DLLISPEC vpiHandle  vpi_scan(vpiHandle iterator);

extern VPI_DLLISPEC char      *vpi_get_str(int32_t property,
                              vpiHandle object);

extern VPI_DLLISPEC void       vpi_get_value(vpiHandle expr,
                                p_vpi_value value_p);

extern VPI_DLLISPEC vpiHandle  vpi_put_value(vpiHandle object,
                                p_vpi_value value_p,
                                p_vpi_time time_p,
                                int32_t flags);

extern VPI_DLLISPEC void       vpi_get_time(vpiHandle object,
                               p_vpi_time time_p);

extern VPI_DLLISPEC int32_t    vpi_get(int property,
                          vpiHandle ref);

extern VPI_DLLISPEC int32_t    vpi_free_object(vpiHandle object);

extern VPI_DLLISPEC int32_t    vpi_control(int32_t operation, ...);
extern VPI_DLLISPEC vpiHandle  vpi_handle_by_multi_index(vpiHandle obj,
                                            int32_t num_index,
                                            int32_t *index_array);


extern VPI_DLLISPEC int32_t    vpi_chk_error(p_vpi_error_info);

extern VPI_DLLISPEC int32_t    vpi_get_vlog_info(p_vpi_vlog_info info_p);

extern VPI_DLLISPEC vpiHandle  vpi_register_systf(p_vpi_systf_data data_p);

extern VPI_DLLISPEC int32_t    vpi_printf(const char *fmt, ...) __attribute__((format (printf,1,2)));

extern VPI_DLLISPEC void (*vlog_startup_routines[])(void);

#ifdef VPI_DLL_LOCAL
#undef VPI_DLL_LOCAL
#undef VPI_DLLISPEC
#endif

#ifdef  __cplusplus
}
#endif

#endif /* COCOTB_VPI_USER_H_ */
