PYTHON_BIN ?= $(realpath $(shell cocotb-config --python-bin))

PYTHON_LIBDIR := $(shell $(PYTHON_BIN) -c 'from distutils import sysconfig; print( sysconfig.get_config_var("LIBDIR") )')
ifeq ($(PYTHON_LIBDIR),None)
    PYTHON_LIBDIR := $(shell dirname $(PYTHON_BIN))/libs
endif

PYTHON_INCLUDEDIR := $(shell $(PYTHON_BIN) -c 'import distutils.sysconfig; print( distutils.sysconfig.get_python_inc() )')

SWIG ?= swig
CC ?= gcc

OS := $(shell uname)

ifeq ($(OS),Darwin)
    CFLAGS += -undefined dynamic_lookup
endif

.PHONY: all
all: io_module.so _hal.so

io_module.o: io.c io_module.h io.h
	$(CC) $(CFLAGS) -fPIC -pthread -fno-strict-aliasing -O2 -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 \
	-fexceptions --param=ssp-buffer-size=4 -D_GNU_SOURCE \
	-fwrapv -I$(PYTHON_INCLUDEDIR) -c $< -o $@

io_module.so: io_module.o
	$(CC) $(CFLAGS) -pthread -shared  $< -L$(PYTHON_LIBDIR)  -o $@

_hal.so: ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so
	$(CC) $(CFLAGS) -g -ldl -shared -fPIC -I$(shell pwd) -I$(PYTHON_INCLUDEDIR) -I../hal ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so -o $@
	if [ $(OS) = Darwin ]; then \
		install_name_tool -change io_module.so $(shell pwd)/io_module.so $@; \
	fi

endian_swapper_hal_wrap.c: ../hal/endian_swapper_hal.h
	$(SWIG) -python -outcurrentdir ../hal/endian_swapper_hal.h

.PHONY: clean
clean:
	-rm -rf hal.py*
	-rm -rf _hal.so.*
	-rm -rf *.so
	-rm -rf *.o
	-rm -rf endian_swapper_hal_wrap.c
