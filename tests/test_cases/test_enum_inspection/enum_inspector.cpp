// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

// Standalone VPI prototype: probes each simulator's coverage of the
// SystemVerilog enum type-inspection model. Two probes per run:
//
//   1. For each *named* signal we declared in enums.sv, call
//      vpi_handle_by_name and dump what vpiType the simulator reports +
//      whether vpiTypespec / vpiBaseTypespec / vpiEnumConst resolve.
//
//   2. For each plausible one-to-many iteration off the top module
//      (vpiReg, vpiNet, vpiVariables, vpiEnumVar, vpiEnumNet, ...), list
//      every name the iteration yields. Different simulators put the
//      same enum signal in different iterations; this tells us which.
//
// CI's compare_log.py parses the dump into a per-signal categorization
// table so we can see at a glance what each simulator exposes.
//
// The library is loaded by cocotb's GPI_USERS mechanism (libgpi parses the
// "lib,func" pair, dlopens the lib, calls func). The function registers a
// cbStartOfSimulation VPI callback that does the work post-elaboration, then
// calls vpi_control(vpiFinish, ...).
//
// No cocotb headers are used -- this is intentionally a "pure VPI" probe.

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "sv_vpi_user.h"
#include "vpi_user.h"

namespace {

const char *kOutputEnv = "ENUM_INSPECTOR_LOG";
const char *kDefaultOutput = "enum_inspection.log";

// Names of every signal in enums.sv that we want to probe by name.
const char *const kKnownSignals[] = {
    "bvec_enum_signal",
    "lvec_enum_signal",
    "int_enum_signal",
    "byte_enum_signal",
    "default_enum_signal",
    "plain_logic_signal",
    nullptr,
};

// One-to-many iteration kinds we want to try off the top module. The set
// covers everything IEEE 1800-2023 says could plausibly contain an enum
// var/net plus the legacy 1364 kinds (vpiReg/vpiNet) since most simulators
// still put SV vars under those.
struct IterKind {
    int32_t code;
    const char *name;
};
const IterKind kIterKinds[] = {
    {vpiReg, "vpiReg"},
    {vpiNet, "vpiNet"},
    {vpiVariables, "vpiVariables"},
    {vpiEnumVar, "vpiEnumVar"},
    {vpiEnumNet, "vpiEnumNet"},
    {vpiBitVar, "vpiBitVar"},
    {vpiIntVar, "vpiIntVar"},
    {vpiByteVar, "vpiByteVar"},
    {vpiTypedef, "vpiTypedef"},
};

FILE *open_output() {
    const char *path = getenv(kOutputEnv);
    if (!path || !path[0]) path = kDefaultOutput;
    FILE *fp = fopen(path, "w");
    if (!fp) {
        vpi_printf((PLI_BYTE8 *)"ENUM_INSPECTOR: failed to open %s\n",
                   (char *)path);
        return stderr;
    }
    return fp;
}

const char *base_typespec_name(int32_t t) {
    switch (t) {
        case vpiBitTypespec:
            return "bit";
        case vpiLogicTypespec:
            return "logic";
        case vpiByteTypespec:
            return "byte";
        case vpiShortIntTypespec:
            return "shortint";
        case vpiIntTypespec:
            return "int";
        case vpiIntegerTypespec:
            return "integer";
        case vpiLongIntTypespec:
            return "longint";
        case vpiStringTypespec:
            return "string";
        default:
            return "unknown";
    }
}

// One-shot dump of a signal handle. Used by both the by-name probe and the
// iteration probe; the leading label is provided by the caller.
//
// We intentionally do NOT call vpi_release_handle on anything here.
// Verilator 5.x does not implement vpi_release_handle and crashes at load
// if you so much as reference the symbol. The handles we acquire are
// short-lived (the simulator exits at the end of start_of_sim_cb) so
// leaking them is fine.
void dump_handle(const char *label, vpiHandle sig, FILE *out) {
    int32_t obj_type = vpi_get(vpiType, sig);
    const char *obj_type_str = vpi_get_str(vpiType, sig);
    if (!obj_type_str) obj_type_str = "<no-type-str>";

    fprintf(out, "%s vpiType=%s", label, obj_type_str);

    // Always try the typespec walk. Per IEEE 1800-2023 the vpiTypespec
    // relation is defined on all variables and nets; a simulator may unwrap
    // the enum and report vpiType=vpiBitVar/vpiIntVar/etc. while still
    // exposing the enum typespec via this path.
    vpiHandle ts = vpi_handle(vpiTypespec, sig);
    if (!ts) {
        fprintf(out, " typespec=NULL\n");
        return;
    }

    int32_t ts_type = vpi_get(vpiType, ts);
    const char *ts_type_str = vpi_get_str(vpiType, ts);
    if (!ts_type_str) ts_type_str = "<no-typespec-str>";
    const char *ts_name = vpi_get_str(vpiName, ts);

    fprintf(out, " typespec=%s typedef=%s", ts_type_str,
            ts_name ? ts_name : "");

    if (ts_type != vpiEnumTypespec) {
        fprintf(out, "\n");
        return;
    }

    vpiHandle base_ts = vpi_handle(vpiBaseTypespec, ts);
    if (!base_ts) {
        fprintf(out, " base=NULL");
    } else {
        int32_t base_ts_type = vpi_get(vpiType, base_ts);
        int base_size = vpi_get(vpiSize, base_ts);
        fprintf(out, " base=%s base_size=%d", base_typespec_name(base_ts_type),
                base_size);
    }

    vpiHandle it = vpi_iterate(vpiEnumConst, ts);
    if (!it) {
        fprintf(out, " members=NULL\n");
        return;
    }
    fprintf(out, " members=[");
    int count = 0;
    vpiHandle m;
    while ((m = vpi_scan(it)) != NULL) {
        const char *mn = vpi_get_str(vpiName, m);
        s_vpi_value v;
        v.format = vpiBinStrVal;
        vpi_get_value(m, &v);
        const char *mv =
            (v.format == vpiBinStrVal && v.value.str) ? v.value.str : "?";
        if (count++) fprintf(out, ",");
        fprintf(out, "%s=%s", mn ? mn : "<noname>", mv);
    }
    fprintf(out, "] count=%d\n", count);
}

void probe_by_name(const char *top_name, FILE *out) {
    char fqn[256];
    for (size_t i = 0; kKnownSignals[i] != nullptr; i++) {
        snprintf(fqn, sizeof(fqn), "%s.%s", top_name, kKnownSignals[i]);
        vpiHandle h = vpi_handle_by_name(fqn, NULL);
        char label[320];
        snprintf(label, sizeof(label), "by-name %s", kKnownSignals[i]);
        if (!h) {
            fprintf(out, "%s NOT_FOUND\n", label);
            continue;
        }
        dump_handle(label, h, out);
    }
}

void probe_iterations(vpiHandle top, FILE *out) {
    for (const auto &k : kIterKinds) {
        vpiHandle it = vpi_iterate(k.code, top);
        if (!it) {
            fprintf(out, "iter %s NULL\n", k.name);
            continue;
        }
        fprintf(out, "iter %s found=[", k.name);
        int count = 0;
        vpiHandle h;
        while ((h = vpi_scan(it)) != NULL) {
            const char *n = vpi_get_str(vpiName, h);
            const char *ts = vpi_get_str(vpiType, h);
            if (count++) fprintf(out, ",");
            fprintf(out, "%s(%s)", n ? n : "<noname>",
                    ts ? ts : "<no-type-str>");
        }
        fprintf(out, "] count=%d\n", count);
    }
}

int start_of_sim_cb(p_cb_data) {
    FILE *out = open_output();

    // Walk every module instance; for each, run both probes.
    vpiHandle top_iter = vpi_iterate(vpiModule, NULL);
    if (!top_iter) {
        fprintf(out, "ENUM_INSPECTOR: no top module iterator\n");
        fclose(out);
        vpi_control(vpiFinish, 0);
        return 0;
    }

    vpiHandle top;
    while ((top = vpi_scan(top_iter)) != NULL) {
        const char *top_name = vpi_get_str(vpiName, top);
        if (!top_name) top_name = "<noname>";
        fprintf(out, "module %s\n", top_name);

        probe_by_name(top_name, out);
        probe_iterations(top, out);
    }

    fclose(out);
    vpi_control(vpiFinish, 0);
    return 0;
}

}  // namespace

extern "C" void enum_inspector_entry(void) {
    s_cb_data cb;
    memset(&cb, 0, sizeof(cb));
    cb.reason = cbStartOfSimulation;
    cb.cb_rtn = start_of_sim_cb;
    vpiHandle h = vpi_register_cb(&cb);
    if (!h) {
        vpi_printf((
            PLI_BYTE8
                *)"ENUM_INSPECTOR: vpi_register_cb(cbStartOfSimulation) "
                  "failed\n");
    }
}
