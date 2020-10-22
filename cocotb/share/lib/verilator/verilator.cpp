// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include "Vtop.h"
#include "verilated.h"
#include "verilated_vpi.h"

#include <memory>

#ifndef VM_TRACE_FST
    //emulate new verilator behavior for legacy versions
    #define VM_TRACE_FST 0
#endif

#if VM_TRACE
#if VM_TRACE_FST
#include <verilated_fst_c.h>
#else
#include <verilated_vcd_c.h>
#endif
#endif

vluint64_t main_time = 0;       // Current simulation time

double sc_time_stamp() {       // Called by $time in Verilog
    return main_time;           // converts to double, to match
                                // what SystemC does
}

extern "C" {
void vlog_startup_routines_bootstrap(void);
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
#ifdef VERILATOR_SIM_DEBUG
    Verilated::debug(99);
#endif
    std::unique_ptr<Vtop> top(new Vtop(""));
    Verilated::fatalOnVpiError(false); // otherwise it will fail on systemtf

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
        bool again = true;

        // We must evaluate whole design until we process all 'events'
        while (again) {
            // Evaluate design
            top->eval();

            // Call Value Change callbacks as eval()
            // can modify signals values
            VerilatedVpi::callValueCbs();

            // Call registered Read-Write callbacks
            again = VerilatedVpi::callCbs(cbReadWriteSynch);

            // Call Value Change callbacks as cbReadWriteSynch
            // can modify signals values
            VerilatedVpi::callValueCbs();
        }

        // Call ReadOnly callbacks
        VerilatedVpi::callCbs(cbReadOnlySynch);

        // Call registered timed callbacks (e.g. clock timer)
        VerilatedVpi::callTimedCbs();

#if VM_TRACE
        tfp->dump(main_time);
#endif
        main_time++;

        // Call registered NextSimTime
        // It should be called in new slot before everything else
        VerilatedVpi::callCbs(cbNextSimTime);
    }

    VerilatedVpi::callCbs(cbEndOfSimulation);

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
