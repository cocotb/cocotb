PYTHON_INCDIR ?= /usr/include/python2.7
PYTHON_LIBDIR ?= /usr/lib64
SWIG ?= swig

.PHONY: all
all: io_module.so _hal.so

io_module.o: io.c io_module.h io.h
	gcc -pthread -fno-strict-aliasing -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions --param=ssp-buffer-size=4 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -DNDEBUG -I$(PYTHON_INCDIR) -c $< -o $@

io_module.so: io_module.o
	gcc -pthread -shared -Wl,-z,relro $< -L$(PYTHON_LIBDIR) -lpython2.7 -o $@

_hal.so: ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so
	gcc -g -ldl -shared -fPIC -I$(shell pwd) -I$(PYTHON_INCDIR) -I../hal ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so -o $@

endian_swapper_hal_wrap.c: ../hal/endian_swapper_hal.h
	$(SWIG) -python -outcurrentdir ../hal/endian_swapper_hal.h

.PHONY: clean
clean:
	-rm -rf hal.py*
	-rm -rf *.so
	-rm -rf *.o
	-rm -rf endian_swapper_hal_wrap.c
