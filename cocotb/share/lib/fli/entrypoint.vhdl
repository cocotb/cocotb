-- The FLI doesn't appear to support an entrypoint defined from the
-- command line parameters or using a pre-defined symbol in a library
-- (unlike VPI or VHPI).  Therefore an entrypoint has to come from
-- the VHDL side.  Because we require access to the FLI at elaboration
-- to register the start of sim callback, we need to use a foreign
-- architecture rather than a foreign procedure.

entity cocotb_entrypoint is
end cocotb_entrypoint;

architecture cocotb_arch of cocotb_entrypoint is
    attribute foreign of cocotb_arch : architecture is "cocotb_fli_init fli.so";
begin
end cocotb_arch;
