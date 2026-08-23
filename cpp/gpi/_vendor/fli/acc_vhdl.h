
/*****************************************************************************
 *
 * acc_vhdl.h
 *
 * List of all predefined type and fulltype constants for VHDL objects.
 *
 * Type Constant       Fulltype Constant       Description
 * ===========================================================================
 *
 * accAlias            accAlias                Object is a VHDL object alias.
 * accAlias            accAliasSignal          ??
 * accAlias            accAliasConstant        ??
 * accAlias            accAliasGeneric         ??
 * accAlias            accAliasVariable        ??
 * ---------------------------------------------------------------------------
 * accArchitecture     accArchitecture         Object is a VHDL architecture.
 *
 *                     accEntityVitalLevel0    Object is an architecture
 *                                             whose entity is decorated with
 *                                             the attribute VITAL_Level0.
 *
 *                     accArchVitalLevel0      Object is an architecture
 *                                             that is decorated with the
 *                                             attribute VITAL_Level0.
 *
 *                     accArchVitalLevel1      Object is an architecture
 *                                             that is decorated with the
 *                                             attribute VITAL_Level1.
 *
 *                     accForeignArch          Object is an architecture
 *                                             that is decorated with the
 *                                             attribute FOREIGN and that
 *                                             does not contain any VHDL
 *                                             statements or objects other
 *                                             than generics and/or ports.
 *
 *                     accForeignArchMixed     Object is an architecture
 *                                             that is decorated with the
 *                                             attribute FOREIGN and that
 *                                             contains at least one VHDL
 *                                             statement and/or object in
 *                                             addition to any generics
 *                                             and/or ports.
 *
 *                     accForeignArchContext   Object is an architecture
 *                                             inserted into the context
 *                                             tree by a 3rd party
 *                                             that is decorated with the
 *                                             attribute FOREIGN and that
 *                                             does not contain any VHDL
 *                                             statements or objects other
 *                                             than generics and/or ports.
 *
 *                     accForeignArchContextMixed  Object is an architecture
 *                                                 inserted into the context
 *                                                 tree by a 3rd party that
 *                                                 is decorated with the
 *                                                 attribute FOREIGN and that
 *                                                 contains at least one VHDL
 *                                                 statement and/or object in
 *                                                 addition to any generics
 *                                                 and/or ports.
 * ---------------------------------------------------------------------------
 * accBlock            accBlock                Object is a VHDL block.
 * ---------------------------------------------------------------------------
 * accConfiguration    accConfiguration        Object is a VHDL configuration.
 * ---------------------------------------------------------------------------
 * accVHDLFile         accVHDLFile             Object is a FILE (1993 and later)
 *                                             or a variable of a file type (1987).
 * ---------------------------------------------------------------------------
 * accForeign          accShadow               Object is a region created
 *                                             with the FLI function
 *                                             mti_CreateRegion().
 * ---------------------------------------------------------------------------
 * accForeignObject    accForeignObject        Object is a 3rd party object.
 * ---------------------------------------------------------------------------
 * accForeignScope     accForeignScope         Object is a 3rd party scope.
 * ---------------------------------------------------------------------------
 * accForLoop          accForLoop              Object is a VHDL for loop.
 * ---------------------------------------------------------------------------
 * accGenerate         accGenerate             Object is a VHDL generate
 *                                             statement.
 *
 *                     accForGenerate          FOR generate statement.
 *
 *                     accIfGenerate           IF generate statement.
 *
 *                     accElsifGenerate        ELSIF generate substatement.
 *
 *                     accElseGenerate         ELSE generate substatement.
 *
 *                     accCaseGenerate         CASE generate statement.
 *
 *                     accCaseOTHERSGenerate   CASE generate (OTHERS choice)
 *                                             substatement.
 * ---------------------------------------------------------------------------
 * accGeneric          accGeneric              Object is a VHDL generic on an
 *                                             entity.
 *
 *                     accGenericConstant      Same as above except that it
 *                                             cannot be modified after design
 *                                             elaboration, presumably because it
 *                                             affects the structural makeup of
 *                                             the design.
 *
 *                     accGenericNotEntity     Object is a VHDL generic on a
 *                                             package or a subprogram.
 *
 *                     accGenericNotEntityConstant Same as above, and it can't
 *                                                 be changed for the same
 *                                                 reasons.
 *
 *                     accInterfacePackage     Object is an interface package on
 *                                             an entity.
 *
 *                     accInterfacePackageNotEntity Object is an interface package
 *                                                  on a package or subprogram.
 *
 *                     accInterfaceSubpgm      Object is an interface subprogram on
 *                                             an entity.
 *
 *                     accInterfaceSubpgmNotEntity Object is an interface subprogram on
 *                                             a package or subprogram.
 #
 *                     accInterfaceType        Object is an interface type on an entity.
 *
 *                     accInterfaceTypeNotEntity Object is an interface type on
 *                                             a package or subprogram.
 *
 * ---------------------------------------------------------------------------
 * accPackage          accPackage              Object is a VHDL package.
 * ---------------------------------------------------------------------------
 * accProcess          accProcess              Object is a VHDL process.
 * ---------------------------------------------------------------------------
 * accSignal           accSignal               Object is a VHDL signal.
 * ---------------------------------------------------------------------------
 * accSubprogram       accSubprogram           Object is a VHDL subprogram.
 * ---------------------------------------------------------------------------
 * accVariable         accVariable             Object is a VHDL variable.
 * ---------------------------------------------------------------------------
 * accVHDLConstant     accVHDLConstant         Object is a VHDL constant.
 * ---------------------------------------------------------------------------
 * accAccessObject     accAccessObject         Object was created with 'new'.
 *                                             Exists only in simulator and when
 *                                             viewing a WLF file.
 *
 *****************************************************************************/

/* $Id: //dvt/mti/rel/2021.4/src/vsim/acc_vhdl.h#1 $ */

#ifndef ACC_VHDL_H
#define ACC_VHDL_H

/* ATTENTION: Do not define values here below 1010 or above 1499. */

#define    accArchitecture            1010
#define    VHDL_FIRST_ACC_ID          accArchitecture

#define    accEntityVitalLevel0       1011
#define    accArchVitalLevel0         1012
#define    accArchVitalLevel1         1013
#define    accForeignArch             1014
#define    accForeignArchMixed        1015
#define    accArchArray               1016
#define    accEntity                  1017
#define    accForeignArchContext      1018
#define    accForeignArchContextMixed 1019
#define    accBlock                   1020
#define    accCompInst                1021
#define    accDirectInst              1022
#define    accinlinedBlock            1023
#define    accinlinedinnerBlock       1024
#define    accGenerate                1030
#define    accIfGenerate              1031
#define    accElsifGenerate           1032
#define    accElseGenerate            1033
#define    accForGenerate             1034
#define    accCaseGenerate            1035
#define    accCaseOTHERSGenerate      1036
#define    accPackage                 1040
#define    accPackageUninstantiated   1041
#define    accPackageInstantiated     1042
#define    accPackageAmsEntry         1043
#define    accConfiguration           1050
#define    accSubprogram              1060
#define    accProcess                 1070
#define    accForLoop                 1080
#define    accForeign                 1090
#define    accShadow                  1091
#define    accShadowConv              1092
#define    accSignal                  1100
#define    accSignalBit               1101
#define    accSignalSubComposite      1102
#define    accVariable                1110
#define    accGeneric                 1120
#define    accGenericConstant         1121
#define    accGenericNotEntity        1122
#define    accGenericNotEntityConstant 1123
#define    accInterfacePackage        1124
#define    accInterfacePackageNotEntity 1125
#define    accInterfaceSubprogram     1126
#define    accInterfaceSubprogramNotEntity 1127
#define    accInterfaceType           1128
#define    accInterfaceTypeNotEntity  1129
#define    accAlias                   1130
#define    accAliasSignal             1131
#define    accAliasConstant           1132
#define    accAliasGeneric            1133
#define    accAliasVariable           1134
#define    accAliasAMSTerminal        1135
#define    accAliasLWS                1136
#define    accVHDLConstant            1140
#define    accVHDLFile                1150
#define    accForeignObject           1160
#define    accAccessObject            1170
#define    VHDL_LAST_ACC_ID           accAccessObject

#define    accForeignScope            1180
#define    accAMSArchitecture         1181
#define    accAMSTerminal             1182
#define    accAMSQuantity             1183
#define    accAMSPackage              1184


#define	 VS_TYPE_IS_VHDL(a) (((a) <= VHDL_LAST_ACC_ID) && (a) >= VHDL_FIRST_ACC_ID)

#endif /* ACC_VHDL_H */


