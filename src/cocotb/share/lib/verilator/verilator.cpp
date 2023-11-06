// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <memory>

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
#else
#include <verilated_vcd_c.h>
#endif
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

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
#ifdef VERILATOR_SIM_DEBUG
    Verilated::debug(99);
#endif
    std::unique_ptr<Vtop> top(new Vtop(""));
    Verilated::fatalOnVpiError(false);  // otherwise it will fail on systemtf

#ifdef VERILATOR_SIM_DEBUG
    Verilated::internalsDump();
#endif

    vlog_startup_routines_bootstrap();
    VerilatedVpi::callCbs(cbStartOfSimulation);

#if VM_TRACE
    Verilated::traceEverOn(true);
#if VM_TRACE_FST
    std::unique_ptr<VerilatedFstC> tfp(new VerilatedFstC);
    top->trace(tfp.get(), 99);
    tfp->open("dump.fst");
#else
    std::unique_ptr<VerilatedVcdC> tfp(new VerilatedVcdC);
    top->trace(tfp.get(), 99);
    tfp->open("dump.vcd");
#endif
#endif

    while (!Verilated::gotFinish()) {
        // Call registered timed callbacks (e.g. clock timer)
        // These are called at the beginning of the time step
        // before the iterative regions (IEEE 1800-2012 4.4.1)
        VerilatedVpi::callTimedCbs();

        // Call Value Change callbacks triggered by Timer callbacks
        // These can modify signal values
        settle_value_callbacks();

        // We must evaluate whole design until we process all 'events'
        bool again = true;
        while (again) {
            // Evaluate design
            top->eval_step();

            // Call Value Change callbacks triggered by eval()
            // These can modify signal values
            again = settle_value_callbacks();

            // Call registered ReadWrite callbacks
            again |= VerilatedVpi::callCbs(cbReadWriteSynch);

            // Call Value Change callbacks triggered by ReadWrite callbacks
            // These can modify signal values
            again |= settle_value_callbacks();
        }
        top->eval_end_step();

        // Call ReadOnly callbacks
        VerilatedVpi::callCbs(cbReadOnlySynch);

#if VM_TRACE
        tfp->dump(main_time);
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

        // Call Value Change callbacks triggered by NextTimeStep callbacks
        // These can modify signal values
        settle_value_callbacks();
    }

    VerilatedVpi::callCbs(cbEndOfSimulation);

    top->final();

#if VM_TRACE
    tfp->close();
#endif

// VM_COVERAGE is a define which is set if Verilator is
// instructed to collect coverage (when compiling the simulation)
#if VM_COVERAGE
    VerilatedCov::write("coverage.dat");
#endif

    return 0;
}
