
all: io_module.so _hal.so

io_module.o: io.c io_module.h io.h
	gcc -pthread -fno-strict-aliasing -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -DNDEBUG -I/usr/include/python2.7 -c $< -o $@

io_module.so: io_module.o
	gcc -pthread -shared -Wl,-z,relro $< -L/usr/lib64 -lpython2.7 -o $@

_hal.so : ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so
	gcc -g -ldl -shared -fPIC -I$(shell pwd) -I/usr/include/python2.7 -I../hal ../hal/endian_swapper_hal.c endian_swapper_hal_wrap.c io_module.so -o $@

endian_swapper_hal_wrap.c: ../hal/endian_swapper_hal.h
	swig -python -outcurrentdir ../hal/endian_swapper_hal.h

.PHONY: clean
clean:
	-rm -rf hal.py*
	-rm -rf *.so
	-rm -rf *.o
	-rm -rf endian_swapper_hal_wrap.c
