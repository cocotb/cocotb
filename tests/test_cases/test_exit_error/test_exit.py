import cocotb
from cocotb.triggers import Timer

@cocotb.test()
def typosyntax_error():
	# this syntax error makes the whole file unimportable, so the file contents
	# don't really matter.
    yield Timer(100)a
