Fixed many missing ``vpi_release_handle`` and ``vhpi_release_handle`` calls in the GPI, which leaked simulator handles for every discovered object, every iterated child, and (on some simulators) every fired one-shot callback.
Also fixed VHPI pseudo-handles into multi-dimensional arrays and nested VHDL ``for ... generate`` lookups releasing a handle borrowed from the parent object.
