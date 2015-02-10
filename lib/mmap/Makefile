INCLUDE_PATHS = -I/usr/include/python2.7

all: mmap_shim.so

mmap_shim.o: mmap_shim.c
	gcc -pthread -fno-strict-aliasing -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions --param=ssp-buffer-size=4 -grecord-gcc-switches -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv -DNDEBUG -I/usr/include/python2.7 -c mmap_shim.c -o mmap_shim.o

mmap_shim.so: mmap_shim.o
	gcc -pthread -shared -Wl,-z,relro mmap_shim.o -L/usr/lib -lpython2.7 -o mmap_shim.so

clean:
	-rm -rf *.o
	-rm -rf *.so
