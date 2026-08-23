This directory contains module-definition files (`.def`).
On Windows these are used to generate import libraries (`.a`, but not regular static libraries), which means we can compile our libraries without having the simulator binaries available.
They are not needed on other platforms.
More details on `.def` files can be found at http://www.mingw.org/wiki/msvc_and_mingw_dlls
