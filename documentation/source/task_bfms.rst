###############
Task-Based BFMs
###############

Overview
========

Cocotb supports a task-based bus functional model (BFM) interface between 
Python, Verilog, and SystemVerilog (VHDL is TBD). 

BFM Implementation (Python)
===========================

The Python aspect of a BFM is captured as a Python class with the @cocotb.bfm 
decorator. The Python class provides both the user-facing and implementation
API. In addition to identifying the class as a BFM class, the @cocotb.bfm
decorator associates HDL template files with the BFM class.


.. code-block:: python3
        @cocotb.bfm(hdl={
            cocotb.bfm_vlog : cocotb.bfm_hdl_path(__file__, "hdl/rv_data_out_bfm.v"),
            cocotb.bfm_sv   : cocotb.bfm_hdl_path(__file__, "hdl/rv_data_out_bfm.v")
        })
        class ReadyValidDataOutBFM():

            def __init__(self):
                self.busy = Lock()
                self.ack_ev = Event()

            @cocotb.coroutine
            def write_c(self, data):
                '''
                Writes the specified data word to the interface
                '''
        
                yield self.busy.acquire()
                self.write_req(data)

                # Wait for acknowledge of the transfer
                yield self.ack_ev.wait()
                self.ack_ev.clear()

                self.busy.release()

            @cocotb.bfm_import(cocotb.bfm_uint64_t)
            def write_req(self, d):
                pass
    
            @cocotb.bfm_export()
            def write_ack(self):
                self.ack_ev.set()

Python methods that will result in task calls in the HDL are 
decorated with the @cocotb.bfm_import decorator, while 
Python methods that will be called from the HDL are decoarated
with the @cocotb.bfm_export decorator. 

The types of method parameters for import and export methods
are specified via the decorator. In the example above, the
imported method accepts a 64-bit unsigned integer.

It is typical, as shown in the example above, to provide 
convenience methods on top of the implementation methods. In 
the example above, the ``write_c`` method provides a blocking
coroutine that sends a write request and waits for the DUT
to accept it.

BFM Implementation (HDL)
========================

The HDL implementation of the BFM is specified using an HDL-language file
that is co-located with the Python class. The HDL file specifies 
implementations for the ``import`` tasks. Implementations of the
``export`` tasks are automatically generated, and are called from 
the HDL code. 

.. code-block:: verilog
      module rv_data_out_bfm #(
            parameter DATA_WIDTH = 8
            ) (
               input                clock,
               input                reset,
               output reg[DATA_WIDTH-1:0] data,
               output reg              data_valid,
               input                data_ready
            );
         
         reg[DATA_WIDTH-1:0]     data_v = 0;
         reg                  data_valid_v = 0;
         
         initial begin
            if (DATA_WIDTH > 64) begin
               $display("Error: rv_data_out_bfm %m -- DATA_WIDTH>64 (%0d)", DATA_WIDTH);
               $finish();
            end
         end
         
         always @(posedge clock) begin
            if (reset) begin
               data_valid <= 0;
               data <= 0;
            end else begin
               data_valid <= data_valid_v;
               data <= data_v;
               if (data_valid && data_ready) begin
                  write_ack();
                  data_valid_v = 0;
               end
            end
         end
         
         task write_req(reg[63:0] d);
            begin
               data_v = d;
               data_valid_v = 1;
            end
         endtask
      
         // Auto-generated code to implement the BFM API
      ${cocotb_bfm_api_impl}
      
      endmodule
      
The implementation of ``export`` tasks (Python methods called from HDL) 
and the machinery to call ``import`` tasks is substituted into the
template via where the ``${cocotb_bfm_api_impl}`` macro is referenced.

Using BFMs from HDL
===================
The HDL portion of the testbench must instantiate BFMs where needed.
These instances will register their existence with Cocotb when simulation
starts. 


Using BFMs from Python
======================
Available BFM instances are registered with the ``cocotb.BfmMgr`` class. 
Static methods provide access to the list of available BFMs, and the
``find_bfm`` method accepts a regular expression to find a BFM based
on its HDL instance path.

.. code-block:: python3
    @cocotb.coroutine
    def run_c(self):
        out_bfm = BfmMgr.find_bfm(".*u_bfm")
        
        for i in range(1,101):
            yield out_bfm.write_c(i)

The code snippet above shows typical use within a test. The ``find_bfm``
method is used to find a BFM with the expected instance path. Then,
methods on the BFM object are called to send data via the BFM.

Cocotb Makefile Interface
=========================
If you are using the Cocotb Makefiles, simply append the BFM packages
used by your testbench to the COCOTB_BFM_MODULES variable

.. code-block:: make
    COCOTB_BFM_MODULES += rv_bfms
    
The Makefiles will automatically generate and compile the interface
files along with the rest of your testbench.

Manually Generating BFM Interface Files
=======================================
The interface code that allows Cocotb to call HDL tasks, and to enable
HDL to call Python methods is auto-generated. This ensures that the 
HDL interface is always up-to-date with the Python definition of the
BFM API.

The ``cocotb-bfmgen`` script generates the appropriate BFM interface
files based on the BFMs required for a given testbench.

The ``cocotb-bfmgen`` script accepts the following options:
- -m <module> -- Specifies a Python module to load. Typically, this will
be a BFM package.
- -language <target> -- Specifies the target testbench language. ``vlog`` and ``sv`` 
are currently accepted.
- -o <file> -- Specifies the output file. By default, the name will 
be cocotb_bfms.v.

For pure-Verilog (VPI) targets, a single Verilog file is generated that contains
all available BFM modules. For SystemVerilog (DPI) targets, a C file is also 
generated that contains the implementation of two DPI methods required for
each BFM type.

These generated files must be compiled along with the other testbench and
design HDL files.

      