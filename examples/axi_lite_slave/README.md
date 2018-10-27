# AXI Lite Demo

Description: In order to simplify AXI Lite Transactions we use an module that
translates AXI Lite Slave transactions to a simple register read/write.

There are other projects that translate AXI Slave signals to wishbone.


## Source Files

* tb\_axi\_lite\_slave: Testbench interface, primarily used to translate
    the cocotb AXI Lite bus signals to the signals within axi_lite_demo core

* axi\_lite\_demo: demonstration module, anyone who wishes to interact
    with an AXI Lite slave core can use this as a template.

* axi\_lite\_slave: Performs all the low level AXI Translactions.
    * Addresses and data sent from the master are decoded from the AXI Bus and
        sent to the user with a simple 'ready', 'acknowledge' handshake.
    * Address and data are read from the slave using a simple
        'request', 'ready' handshake.

## NOTE: Test ID

If you use a logic analyzer wave viewer it's hard to determine which test is
currently running so I added a value called 'test\_id' in the test bench
so when viewing the waveforms the individual tests can easily be identified
