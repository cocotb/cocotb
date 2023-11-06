/*****************************************************************************
 * acc_user.h
 *
 * IEEE 1364-2001 Verilog HDL Programming Language Interface (PLI).
 *
 * This file contains the constant definitions, structure definitions, and
 * routine declarations for the Verilog Programming Language Interface ACC
 * access routines.
 *
 ****************************************************************************/

/* $Id: //dvt/mti/rel/2021.4/src/vsim/acc_user.h#1 $ */

#ifndef ACC_USER_H
#define ACC_USER_H

#ifdef  __cplusplus
extern "C" {
#endif

/*---------------------------------------------------------------------------*/
/*--------------------------- Portability Help ------------------------------*/
/*---------------------------------------------------------------------------*/
/* Sized variables */
#ifndef PLI_TYPES
#define PLI_TYPES
typedef int             PLI_INT32;
typedef unsigned int    PLI_UINT32;
typedef short           PLI_INT16;
typedef unsigned short  PLI_UINT16;
typedef char            PLI_BYTE8;
typedef unsigned char   PLI_UBYTE8;
#endif

/* import a symbol into dll */
#if (defined(_MSC_VER) || defined(__MINGW32__) || defined(__CYGWIN__)) 
#ifndef PLI_DLLISPEC
#define PLI_DLLISPEC __declspec(dllimport)
#define ACC_USER_DEFINED_DLLISPEC 1
#endif
#else
#ifndef PLI_DLLISPEC
#define PLI_DLLISPEC
#endif
#endif

/* export a symbol from dll */
#if (defined(_MSC_VER) || defined(__MINGW32__) || defined(__CYGWIN__))
#ifndef PLI_DLLESPEC
#define PLI_DLLESPEC __declspec(dllexport)
#define ACC_USER_DEFINED_DLLESPEC 1
#endif
#else
#ifndef PLI_DLLESPEC
#define PLI_DLLESPEC
#endif
#endif

/* mark a function as external */
#ifndef PLI_EXTERN
#define PLI_EXTERN
#endif

/* mark a variable as external */
#ifndef PLI_VEXTERN
#define PLI_VEXTERN extern
#endif

#ifndef PLI_PROTOTYPES
#define PLI_PROTOTYPES
#define PROTO_PARAMS(params) params
/* object is imported by the dll */
#define XXTERN PLI_EXTERN PLI_DLLISPEC
/* object is exported by the dll */
#define EETERN PLI_EXTERN PLI_DLLESPEC
#endif

/*
 * The following group of defines exists purely for backwards compatibility
 */
#ifndef PLI_EXTRAS
#define PLI_EXTRAS
/* guard bool/true/false when compiling with C++, C99 or later */
#if !defined(__cplusplus) && (!defined(__STDC_VERSION__) || (__STDC_VERSION__ < 199901L))
#define bool                   int
#define true                   1
#define TRUE                   1
#define false                  0
#define FALSE                  0
#endif
#define null                   0L
#define global extern
#define local  static
#define exfunc
#endif


/*---------------------------------------------------------------------------*/
/*------------------------------- definitions -------------------------------*/
/*---------------------------------------------------------------------------*/

/*----------------------------- general defines -----------------------------*/
typedef void   *HANDLE;
#ifndef VPI_USER_CDS_H
typedef void   *handle;
#endif

#define OPEN_HANDLE_REP ((handle)0x1)

#define HANDLE_IS_OPEN(hand) ((hand) == OPEN_HANDLE_REP)

/*------------------------------- object types ------------------------------*/
#define    accModule               20
#define    accScope                21
#define    accNet                  25
#define    accReg                  30
#define    accRegister             accReg
#define    accPort                 35
#define    accTerminal             45
#define    accInputTerminal        46
#define    accOutputTerminal       47
#define    accInoutTerminal        48
#define    accCombPrim            140
#define    accSeqOptPrim          141
#define    accSeqPrim             142
#define    accAndGate             144
#define    accNandGate            146
#define    accNorGate             148
#define    accOrGate              150
#define    accXorGate             152
#define    accXnorGate            154
#define    accBufGate             156
#define    accNotGate             158
#define    accBufif0Gate          160
#define    accBufif1Gate          162
#define    accNotif0Gate          164
#define    accNotif1Gate          166
#define    accNmosGate            168
#define    accPmosGate            170
#define    accCmosGate            172
#define    accRnmosGate           174
#define    accRpmosGate           176
#define    accRcmosGate           178
#define    accRtranGate           180
#define    accRtranif0Gate        182
#define    accRtranif1Gate        184
#define    accTranGate            186
#define    accTranif0Gate         188
#define    accTranif1Gate         190
#define    accPullupGate          192
#define    accPulldownGate        194
#define    accIntegerParam        200
#define    accIntParam            accIntegerParam
#define    accRealParam           202
#define    accStringParam         204
#define    accPath                206
#define    accTchk                208
#define    accPrimitive           210
#define    accBit                 212
#define    accPortBit             214
#define    accNetBit              216
#define    accRegBit              218
#define    accParameter           220
#define    accSpecparam           222
#define    accSpecParam           accSpecparam
#define    accTopModule           224
#define    accModuleInstance      226
#define    accCellInstance        228
#define    accModPath             230
#define    accWirePath            234
#define    accInterModPath        236
#define    accScalarPort          250
#define    accBitSelectPort       252
#define    accPartSelectPort      254
#define    accVectorPort          256
#define    accConcatPort          258
#define    accWire                260
#define    accWand                261
#define    accWor                 262
#define    accTri                 263
#define    accTriand              264
#define    accTrior               265
#define    accTri0                266
#define    accTri1                267
#define    accTrireg              268
#define    accSupply0             269
#define    accSupply1             270
#define    accNamedEvent          280
#define    accEventVar            accNamedEvent
#define    accIntegerVar          281
#define    accIntVar              281
#define    accRealVar             282
#define    accTimeVar             283
#define    accScalar              300
#define    accVector              302
#define    accCollapsedNet        304
#define    accExpandedVector      306
#define    accUnExpandedVector    307
#define    accProtected           308
#define    accSetup               366
#define    accHold                367
#define    accWidth               368
#define    accPeriod              369
#define    accRecovery            370
#define    accSkew                371
#define    accTimeSkew            381
#define    accFullSkew            382
#define    accRemoval             372
#define    accRecrem              373
#define    accNochange            376
#define    accNoChange            accNochange
#define    accSetuphold           377
#define    accInput               402
#define    accOutput              404
#define    accInout               406
#define    accMixedIo             407
#define    accPositive            408
#define    accNegative            410
#define    accUnknown             412
#define    accPathTerminal        420
#define    accPathInput           422
#define    accPathOutput          424
#define    accDataPath            426
#define    accTchkTerminal        428
#define    accBitSelect           500
#define    accPartSelect          502
#define    accTask                504
#define    accFunction            506
#define    accStatement           508
#define    accTaskCall            510
#define    accFunctionCall        512
#define    accSystemTask          514
#define    accSystemFunction      516
#define    accSystemRealFunction  518
#define    accUserTask            520
#define    accUserFunction        522
#define    accUserRealFunction    524
#define    accNamedBeginStat      560
#define    accNamedForkStat       564
#define    accNamedForeachStmt    565
#define    accConstant            600
#define    accConcat              610
#define    accOperator            620
#define    accMinTypMax           696
#define    accModPathHasIfnone    715
#define    accSeqOptFastPrim_1    801
#define    accSeqOptFastPrim_2    802
#define    accSeqOptFastPrim_3    803
#define    accSeqOptFastPrim_4    804
#define    accSeqOptFastPrim_5    805
#define    accSeqOptFastPrim_6    806
#define    accSeqOptFastPrim_7    807
#define    accSeqOptFastPrim_8    808
#define    accModportTask         809

/*------------------ parameter values for acc_configure() -------------------*/
#define    accPathDelayCount        1
#define    accPathDelimStr          2
#define    accDisplayErrors         3
#define    accDefaultAttr0          4
#define    accToHiZDelay            5
#define    accEnableArgs            6
#define    accDisplayWarnings       8
#define    accDevelopmentVersion   11
#define    accMapToMipd            17
#define    accMinTypMaxDelays      19

/*------------ edge information used by acc_handle_tchk(), etc.  ------------*/
#define accNoedge                   0
#define accNoEdge                   0
#define accEdge01                   1
#define accEdge10                   2
#define accEdge0x                   4
#define accEdgex1                   8
#define accEdge1x                  16
#define accEdgex0                  32
#define accPosedge                 13
#define accPosEdge                 accPosedge
#define accNegedge                 50
#define accNegEdge                 accNegedge

/*------------------------------- delay modes -------------------------------*/
#define accDelayModeNone            0
#define accDelayModePath            1
#define accDelayModeDistrib         2
#define accDelayModeUnit            3
#define accDelayModeZero            4
#define accDelayModeMTM             5
#define accDelayModeSUDP            6

/*------------ values for type field in t_setval_delay structure ------------*/
#define accNoDelay                  0
#define accInertialDelay            1
#define accTransportDelay           2
#define accPureTransportDelay       3
#define accForceFlag                4
#define accReleaseFlag              5
#define accAssignFlag               6
#define accDeassignFlag             7

/*------------ values for type field in t_setval_value structure ------------*/
#define accBinStrVal                1
#define accOctStrVal                2
#define accDecStrVal                3
#define accHexStrVal                4
#define accScalarVal                5
#define accIntVal                   6
#define accRealVal                  7
#define accStringVal                8
#define accVectorVal               10

/*------------------------------ scalar values ------------------------------*/
#define acc0                        0
#define acc1                        1
#define accX                        2
#define accZ                        3

/*---------------------------- VCL scalar values ----------------------------*/
#define vcl0                        acc0
#define vcl1                        acc1
#define vclX                        accX
#define vclx                        vclX
#define vclZ                        accZ
#define vclz                        vclZ

/*----------- values for vc_reason field in t_vc_record structure -----------*/
#define logic_value_change          1
#define strength_value_change       2
#define real_value_change           3
#define vector_value_change         4
#define event_value_change          5
#define integer_value_change        6
#define time_value_change           7
#define sregister_value_change      8
#define vregister_value_change      9
#define realtime_value_change      10

/*--------------------------- VCL strength values ---------------------------*/
#define vclSupply                   7
#define vclStrong                   6
#define vclPull                     5
#define vclLarge                    4
#define vclWeak                     3
#define vclMedium                   2
#define vclSmall                    1
#define vclHighZ                    0

/*----------------------- vcl bit flag definitions -------------------------*/
#define vcl_strength_flag           1
#define vcl_verilog_flag            2

/*----------------------- flags used with acc_vcl_add -----------------------*/
#define vcl_verilog_logic           2
#define VCL_VERILOG_LOGIC           vcl_verilog_logic
#define vcl_verilog_strength        3
#define VCL_VERILOG_STRENGTH        vcl_verilog_strength

/*---------------------- flags used with acc_vcl_delete ---------------------*/
#define vcl_verilog                 vcl_verilog_logic
#define VCL_VERILOG                 vcl_verilog

/*---------- values for the type field in the t_acc_time structure --------- */
#define accTime                     1
#define accSimTime                  2
#define accRealTime                 3

/*------------------------------ product types ------------------------------*/
#define accSimulator                1
#define accTimingAnalyzer           2
#define accFaultSimulator           3
#define accOther                    4


/*---------------------------------------------------------------------------*/
/*-------------------------- structure definitions --------------------------*/
/*---------------------------------------------------------------------------*/

typedef struct t_vc_record *p_vc_record;

typedef PLI_INT32 (*consumer_function)(p_vc_record);

/*----------------- data structure used with acc_set_value() ----------------*/
typedef struct t_acc_time
{
  PLI_INT32 type;
  PLI_INT32 low,
            high;
  double    real;
} s_acc_time, *p_acc_time;

/*----------------- data structure used with acc_set_value() ----------------*/
typedef struct t_setval_delay
{
  s_acc_time time;
  PLI_INT32  model;
} s_setval_delay, *p_setval_delay;

/*--------------------- data structure of vector values ---------------------*/
typedef struct t_acc_vecval
{
  PLI_INT32 aval;
  PLI_INT32 bval;
} s_acc_vecval, *p_acc_vecval;

/*------ data structure used with acc_set_value() and acc_fetch_value() -----*/
typedef struct t_setval_value
{
  PLI_INT32 format;
  union
    {
      PLI_BYTE8    *str;
      PLI_INT32     scalar;
      PLI_INT32     integer;
      double        real;
      p_acc_vecval  vector;
    } value;
} s_setval_value, *p_setval_value, s_acc_value, *p_acc_value;

/*----------------------- structure for VCL strengths -----------------------*/
typedef struct t_strengths
{
  PLI_UBYTE8 logic_value;
  PLI_UBYTE8 strength1;
  PLI_UBYTE8 strength2;
} s_strengths, *p_strengths;

/*--------------- structure passed to callback routine for VCL --------------*/
typedef struct t_vc_record
{
  PLI_INT32  vc_reason;
  PLI_INT32  vc_hightime;
  PLI_INT32  vc_lowtime;
  PLI_BYTE8 *user_data;
  union
    {
      PLI_UBYTE8  logic_value;
      double      real_value;
      handle      vector_handle;
      s_strengths strengths_s;
    } out_value;
} s_vc_record;

/*------------- structure used with acc_fetch_location() routine ------------*/
typedef struct t_location
{
  PLI_INT32  line_no;
  PLI_BYTE8 *filename;
} s_location, *p_location;

/*---------- structure used with acc_fetch_timescale_info() routine ---------*/
typedef struct t_timescale_info
{
  PLI_INT16 unit;
  PLI_INT16 precision;
} s_timescale_info, *p_timescale_info;


/*---------------------------------------------------------------------------*/
/*-------------------------- routine declarations ---------------------------*/
/*---------------------------------------------------------------------------*/

XXTERN PLI_INT32   acc_append_delays PROTO_PARAMS((handle object, ...));
XXTERN PLI_INT32   acc_append_pulsere PROTO_PARAMS((handle object, double val1r, double val1x, ...));
XXTERN void        acc_close PROTO_PARAMS((void));
XXTERN handle     *acc_collect PROTO_PARAMS((handle (*p_next_routine)(handle object_handle, handle obj), handle scope_object, PLI_INT32 *aof_count));
XXTERN PLI_INT32   acc_compare_handles PROTO_PARAMS((handle h1, handle h2));
XXTERN PLI_INT32   acc_configure PROTO_PARAMS((PLI_INT32 item, PLI_BYTE8 *value));
XXTERN PLI_INT32   acc_count PROTO_PARAMS((handle (*next_func)(handle object_handle, handle obj), handle object_handle));
XXTERN char       *acc_decompile_exp PROTO_PARAMS((handle condition ));
XXTERN PLI_INT32  *acc_error_flag_address PROTO_PARAMS((void));
XXTERN PLI_INT32   acc_fetch_argc PROTO_PARAMS((void));
XXTERN PLI_BYTE8 **acc_fetch_argv PROTO_PARAMS((void));
XXTERN double      acc_fetch_attribute PROTO_PARAMS((handle object, PLI_BYTE8 *attribute_string, ...));
XXTERN PLI_INT32   acc_fetch_attribute_int PROTO_PARAMS((handle object, PLI_BYTE8 *attribute_string, ...));
XXTERN PLI_BYTE8  *acc_fetch_attribute_str PROTO_PARAMS((handle object, PLI_BYTE8 *attribute_string, ...));
XXTERN PLI_BYTE8  *acc_fetch_defname PROTO_PARAMS((handle object_handle));
XXTERN PLI_INT32   acc_fetch_delay_mode PROTO_PARAMS((handle object_p));
XXTERN PLI_INT32   acc_fetch_delays PROTO_PARAMS((handle object, ...));
XXTERN PLI_INT32   acc_fetch_direction PROTO_PARAMS((handle object_handle));
XXTERN PLI_INT32   acc_fetch_edge PROTO_PARAMS((handle acc_obj));
XXTERN PLI_BYTE8  *acc_fetch_fullname PROTO_PARAMS((handle object_handle));
XXTERN PLI_INT32   acc_fetch_fulltype PROTO_PARAMS((handle object_h));
XXTERN PLI_INT32   acc_fetch_index PROTO_PARAMS((handle object_handle));
XXTERN double      acc_fetch_itfarg PROTO_PARAMS((PLI_INT32 n, handle tfinst));
XXTERN PLI_INT32   acc_fetch_itfarg_int PROTO_PARAMS((PLI_INT32 n, handle tfinst));
XXTERN PLI_BYTE8  *acc_fetch_itfarg_str PROTO_PARAMS((PLI_INT32 n, handle tfinst));
XXTERN PLI_INT32   acc_fetch_location PROTO_PARAMS((p_location location_p, handle object));
XXTERN PLI_BYTE8  *acc_fetch_name PROTO_PARAMS((handle object_handle));
XXTERN PLI_INT32   acc_fetch_paramtype PROTO_PARAMS((handle param_p));
XXTERN double      acc_fetch_paramval PROTO_PARAMS((handle param));
XXTERN char       *acc_fetch_paramval_str PROTO_PARAMS((handle param));
XXTERN PLI_INT32   acc_fetch_polarity PROTO_PARAMS((handle path));
XXTERN PLI_INT32   acc_fetch_precision PROTO_PARAMS((void));
XXTERN PLI_INT32   acc_fetch_pulsere PROTO_PARAMS((handle path_p, double *val1r, double *val1e, ...));
XXTERN PLI_INT32   acc_fetch_range PROTO_PARAMS((handle node, PLI_INT32 *msb, PLI_INT32 *lsb));
XXTERN PLI_INT32   acc_fetch_size PROTO_PARAMS((handle obj_h));
XXTERN double      acc_fetch_tfarg PROTO_PARAMS((PLI_INT32 n));
XXTERN PLI_INT32   acc_fetch_tfarg_int PROTO_PARAMS((PLI_INT32 n));
XXTERN PLI_BYTE8  *acc_fetch_tfarg_str PROTO_PARAMS((PLI_INT32 n));
XXTERN void        acc_fetch_timescale_info PROTO_PARAMS((handle obj, p_timescale_info aof_timescale_info));
XXTERN PLI_INT32   acc_fetch_type PROTO_PARAMS((handle object_handle));
XXTERN PLI_BYTE8  *acc_fetch_type_str PROTO_PARAMS((PLI_INT32 type));
XXTERN PLI_BYTE8  *acc_fetch_value PROTO_PARAMS((handle object_handle, PLI_BYTE8 *format_str, p_acc_value acc_value_p));
XXTERN void        acc_free PROTO_PARAMS((handle *array_ptr));
XXTERN handle      acc_handle_by_name PROTO_PARAMS((PLI_BYTE8 *inst_name, handle scope_p));
XXTERN handle      acc_handle_condition PROTO_PARAMS((handle obj));
XXTERN handle      acc_handle_conn PROTO_PARAMS((handle term_p));
XXTERN handle      acc_handle_datapath PROTO_PARAMS((handle path));
XXTERN handle      acc_handle_hiconn PROTO_PARAMS((handle port_ref));
XXTERN handle      acc_handle_interactive_scope PROTO_PARAMS((void));
XXTERN handle      acc_handle_itfarg PROTO_PARAMS((PLI_INT32 n, handle tfinst));
XXTERN handle      acc_handle_loconn PROTO_PARAMS((handle port_ref));
XXTERN handle      acc_handle_modpath PROTO_PARAMS((handle mod_p, PLI_BYTE8 *pathin_name, PLI_BYTE8 *pathout_name, ...));
XXTERN handle      acc_handle_notifier PROTO_PARAMS((handle tchk));
XXTERN handle      acc_handle_object PROTO_PARAMS((PLI_BYTE8 *inst_name));
XXTERN handle      acc_handle_parent PROTO_PARAMS((handle object_p));
XXTERN handle      acc_handle_path PROTO_PARAMS((handle source, handle destination));
XXTERN handle      acc_handle_pathin PROTO_PARAMS((handle path_p));
XXTERN handle      acc_handle_pathout PROTO_PARAMS((handle path_p));
XXTERN handle      acc_handle_port PROTO_PARAMS((handle mod_handle, PLI_INT32 port_num));
XXTERN handle      acc_handle_scope PROTO_PARAMS((handle object));
XXTERN handle      acc_handle_simulated_net PROTO_PARAMS((handle net_h));
XXTERN handle      acc_handle_tchk PROTO_PARAMS((handle mod_p, PLI_INT32 tchk_type, PLI_BYTE8 *arg1_conn_name, PLI_INT32 arg1_edgetype, ...));
XXTERN handle      acc_handle_tchkarg1 PROTO_PARAMS((handle tchk));
XXTERN handle      acc_handle_tchkarg2 PROTO_PARAMS((handle tchk));
XXTERN handle      acc_handle_terminal PROTO_PARAMS((handle gate_handle, PLI_INT32 terminal_index));
XXTERN handle      acc_handle_tfarg PROTO_PARAMS((PLI_INT32 n));
XXTERN handle      acc_handle_tfinst PROTO_PARAMS((void));
XXTERN PLI_INT32   acc_initialize PROTO_PARAMS((void));
XXTERN handle      acc_next PROTO_PARAMS((PLI_INT32 *type_list, handle h_scope, handle h_object));
XXTERN handle      acc_next_bit PROTO_PARAMS ((handle vector, handle bit));
XXTERN handle      acc_next_cell PROTO_PARAMS((handle scope, handle cell));
XXTERN handle      acc_next_cell_load PROTO_PARAMS((handle net_handle, handle load));
XXTERN handle      acc_next_child PROTO_PARAMS((handle mod_handle, handle child));
XXTERN handle      acc_next_driver PROTO_PARAMS((handle net, handle driver));
XXTERN handle      acc_next_hiconn PROTO_PARAMS((handle port, handle hiconn));
XXTERN handle      acc_next_input PROTO_PARAMS((handle path, handle pathin));
XXTERN handle      acc_next_load PROTO_PARAMS((handle net, handle load));
XXTERN handle      acc_next_loconn PROTO_PARAMS((handle port, handle loconn));
XXTERN handle      acc_next_modpath PROTO_PARAMS((handle mod_p, handle path));
XXTERN handle      acc_next_net PROTO_PARAMS((handle mod_handle, handle net));
XXTERN handle      acc_next_output PROTO_PARAMS((handle path, handle pathout));
XXTERN handle      acc_next_parameter PROTO_PARAMS((handle module_p, handle param));
XXTERN handle      acc_next_port PROTO_PARAMS((handle ref_obj_p, handle port));
XXTERN handle      acc_next_portout PROTO_PARAMS((handle mod_p, handle port));
XXTERN handle      acc_next_primitive PROTO_PARAMS((handle mod_handle, handle prim));
XXTERN handle      acc_next_scope PROTO_PARAMS((handle ref_scope_p, handle scope));
XXTERN handle      acc_next_specparam PROTO_PARAMS((handle module_p, handle sparam));
XXTERN handle      acc_next_tchk PROTO_PARAMS((handle mod_p, handle tchk));
XXTERN handle      acc_next_terminal PROTO_PARAMS((handle gate_handle, handle term));
XXTERN handle      acc_next_topmod PROTO_PARAMS((handle topmod));
XXTERN PLI_INT32   acc_object_in_typelist PROTO_PARAMS((handle object, PLI_INT32 *type_list));
XXTERN PLI_INT32   acc_object_of_type PROTO_PARAMS((handle object, PLI_INT32 type));
XXTERN PLI_INT32   acc_product_type PROTO_PARAMS((void));
XXTERN PLI_BYTE8  *acc_product_version PROTO_PARAMS((void));
XXTERN PLI_INT32   acc_release_object PROTO_PARAMS((handle obj));
XXTERN PLI_INT32   acc_replace_delays PROTO_PARAMS((handle object, ...));
XXTERN PLI_INT32   acc_replace_pulsere PROTO_PARAMS((handle object, double val1r, double val1x, ...));
XXTERN void        acc_reset_buffer PROTO_PARAMS((void));
XXTERN PLI_INT32   acc_set_interactive_scope PROTO_PARAMS((handle scope, PLI_INT32 callback_flag));
XXTERN PLI_INT32   acc_set_pulsere PROTO_PARAMS((handle path_p, double val1r, double val1e));
XXTERN PLI_BYTE8  *acc_set_scope PROTO_PARAMS((handle object, ...));
XXTERN PLI_INT32   acc_set_value PROTO_PARAMS((handle obj, p_setval_value setval_p, p_setval_delay delay_p));
XXTERN void        acc_vcl_add PROTO_PARAMS((handle object_p, PLI_INT32 (*consumer)(p_vc_record), PLI_BYTE8 *user_data, PLI_INT32 vcl_flags));
XXTERN void        acc_vcl_delete PROTO_PARAMS((handle object_p, PLI_INT32 (*consumer)(p_vc_record), PLI_BYTE8 *user_data, PLI_INT32 vcl_flags));
XXTERN PLI_BYTE8  *acc_version PROTO_PARAMS((void));


/*---------------------------------------------------------------------------*/
/*----------------------- global variable definitions -----------------------*/
/*---------------------------------------------------------------------------*/

#if (!defined(VSIM) && !defined(VOPT)) && (defined(WIN32) || defined(_WIN32) || defined(__WIN32__) || defined(__NT__))
#define acc_error_flag (*acc_error_flag_address())
#else
PLI_VEXTERN PLI_DLLISPEC PLI_INT32 acc_error_flag;
#endif


/*---------------------------------------------------------------------------*/
/*---------------------------- macro definitions ----------------------------*/
/*---------------------------------------------------------------------------*/

#define  acc_handle_calling_mod_m  acc_handle_parent((handle)tf_getinstance())

#undef PLI_EXTERN
#undef PLI_VEXTERN

#ifdef ACC_USER_DEFINED_DLLISPEC
#undef ACC_USER_DEFINED_DLLISPEC
#undef PLI_DLLISPEC
#endif
#ifdef ACC_USER_DEFINED_DLLESPEC
#undef ACC_USER_DEFINED_DLLESPEC
#undef PLI_DLLESPEC
#endif

#ifdef PLI_PROTOTYPES
#undef PLI_PROTOTYPES
#undef PROTO_PARAMS
#undef XXTERN
#undef EETERN
#endif

#ifdef  __cplusplus
}
#endif

#endif /* ACC_USER_H */
