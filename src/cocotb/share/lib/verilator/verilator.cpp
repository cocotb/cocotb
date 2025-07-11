// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <libgen.h>  // basename
#include <stdio.h>   // stderr, fprintf

#include <memory>  // std::unique_ptr
#include <string>  // std::string

#include "Vtop.h"
#include "verilated.h"
#include "verilated_vpi.h"

#ifndef VM_TRACE_FST
// emulate new verilator behavior for legacy versions
#define VM_TRACE_FST 0
#endif

#if VM_TRACE
#if VM_TRACE_FST
#include <verilated_fst_c.h>
using verilated_trace_t = VerilatedFstC;
#else
#include <verilated_vcd_c.h>
using verilated_trace_t = VerilatedVcdC;
#endif
static verilated_trace_t* tfp;
#endif

static vluint64_t main_time = 0;  // Current simulation time

double sc_time_stamp() {  // Called by $time in Verilog
    return main_time;     // converts to double, to match
                          // what SystemC does
}

extern "C" {
void vlog_startup_routines_bootstrap(void);
}

static inline bool settle_value_callbacks() {
    bool cbs_called, again;

    // Call Value Change callbacks
    // These can modify signal values so we loop
    // until there are no more changes
    cbs_called = again = VerilatedVpi::callValueCbs();
    while (again) {
        again = VerilatedVpi::callValueCbs();
    }

    return cbs_called;
}

void wrap_up() {
    VerilatedVpi::callCbs(cbEndOfSimulation);

#if VM_TRACE
    if (tfp) {
        delete tfp;
        tfp = nullptr;
    }
#endif

    // VM_COVERAGE is a define which is set if Verilator is
    // instructed to collect coverage (when compiling the simulation)
#if VM_COVERAGE
    VerilatedCov::write();  // Uses +verilator+coverage+file+<filename>,
                            // defaults to coverage.dat
#endif
}

int main(int argc, char** argv) {
#if VM_TRACE_FST
    const char* traceFile = "dump.fst";
#else
    const char* traceFile = "dump.vcd";
#endif
    bool traceOn = false;

    for (int i = 1; i < argc; i++) {
        std::string arg = std::string(argv[i]);
        if (arg == "--trace") {
#if VM_TRACE
            traceOn = true;
#else
            fprintf(stderr,
                    "Error: --trace requires the design to be built with trace "
                    "support\n");
            return -1;
#endif
        } else if (arg == "--trace-file") {
            if (++i < argc) {
                traceFile = argv[i];
            } else {
                fprintf(stderr, "Error: --trace-file requires a parameter\n");
                return -1;
            }
        } else if (arg == "--help") {
            fprintf(stderr,
                    "usage: %s [--trace] [--trace-file TRACEFILE]\n"
                    "\n"
                    "Cocotb + Verilator sim\n"
                    "\n"
                    "options:\n"
                    "  --trace      Enables tracing (VCD or FST)\n"
                    "  --trace-file Specifies the trace file name (%s by "
                    "default)\n",
                    basename(argv[0]), traceFile);
            return 0;
        }
    }

    Verilated::commandArgs(argc, argv);
#ifdef VERILATOR_SIM_DEBUG
    Verilated::debug(99);
#endif
    std::unique_ptr<Vtop> top(new Vtop(""));
    Verilated::fatalOnVpiError(false);  // otherwise it will fail on systemtf

#ifdef VERILATOR_SIM_DEBUG
    Verilated::internalsDump();
#endif

#if VM_TRACE
    Verilated::traceEverOn(true);
    if (traceOn) {
        tfp = new verilated_trace_t;
        top->trace(tfp, 99);
        tfp->open(traceFile);
    }
#endif

    vlog_startup_routines_bootstrap();
    Verilated::addExitCb([](void*) { wrap_up(); }, nullptr);
    VerilatedVpi::callCbs(cbStartOfSimulation);
    settle_value_callbacks();

    while (!Verilated::gotFinish()) {
        do {
            // We must evaluate whole design until we process all 'events' for
            // this time step
            do {
                top->eval_step();
                VerilatedVpi::clearEvalNeeded();
                VerilatedVpi::doInertialPuts();
                settle_value_callbacks();
            } while (VerilatedVpi::evalNeeded());

            // Run ReadWrite callback as we are done processing this eval step
            VerilatedVpi::callCbs(cbReadWriteSynch);
            VerilatedVpi::doInertialPuts();
            settle_value_callbacks();
        } while (VerilatedVpi::evalNeeded());

        top->eval_end_step();

        // Call ReadOnly callbacks
        VerilatedVpi::callCbs(cbReadOnlySynch);

#if VM_TRACE
        if (tfp) {
            tfp->dump(main_time);
        }
#endif
        // cocotb controls the clock inputs using cbAfterDelay so
        // skip ahead to the next registered callback
        const vluint64_t NO_TOP_EVENTS_PENDING = static_cast<vluint64_t>(~0ULL);
        vluint64_t next_time_cocotb = VerilatedVpi::cbNextDeadline();
        vluint64_t next_time_timing =
            top->eventsPending() ? top->nextTimeSlot() : NO_TOP_EVENTS_PENDING;
        vluint64_t next_time = std::min(next_time_cocotb, next_time_timing);

        // If there are no more cbAfterDelay callbacks,
        // the next deadline is max value, so end the simulation now
        if (next_time == NO_TOP_EVENTS_PENDING) {
            break;
        } else {
            main_time = next_time;
        }

        // Call registered NextSimTime
        // It should be called in simulation cycle before everything else
        // but not on first cycle
        VerilatedVpi::callCbs(cbNextSimTime);
        settle_value_callbacks();

        // Call registered timed callbacks (e.g. clock timer)
        // These are called at the beginning of the time step
        // before the iterative regions (IEEE 1800-2012 4.4.1)
        VerilatedVpi::callTimedCbs();
        settle_value_callbacks();
    }

    top->final();

    wrap_up();

    return 0;
}
