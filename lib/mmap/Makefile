INCLUDE_PATHS = -I/usr/include/python2.7

# $(CC_ARGS) = -m32

all: mmap_preload.so

mmap_shim.o: mmap_shim.c
	gcc -pthread -fno-strict-aliasing -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -mtune=generic -m32 -D_GNU_SOURCE -fPIC -fwrapv -DNDEBUG -I/usr/include/python2.7 -c mmap_shim.c -o mmap_shim.o

mmap_shim.so: mmap_shim.o
	gcc -pthread -shared -Wl,-z,relro mmap_shim.o -L/usr/lib -lpython2.7 -m32 -o mmap_shim.so

# all: mmap_preload.so

# %.o : %.c
# 	gcc -g $(INCLUDE_PATHS) $< -o $@

# mmap_shim.so : mmap_shim.c
# 	gcc -g -Xcompiler -o32 -Xlinker -shared $< -o $@
	
mmap_preload.so : mmap_shim.so mmap_preload.c
	gcc -g -ldl -shared -fPIC mmap_preload.c mmap_shim.so -m32 -o $@


clean:
	-rm -rf *.o
	-rm -rf *.so
