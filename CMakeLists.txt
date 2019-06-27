cmake_minimum_required(VERSION 3.4.0)

project(cocotb)

find_package(PythonLibs REQUIRED)
find_package(PythonExtensions REQUIRED)

set(SHARE_DIR cocotb/share)
set(CMAKE_INSTALL_RPATH "$ORIGIN")

include_directories("cocotb/share/include")

# gpilog
add_library(gpilog SHARED
	${SHARE_DIR}/lib/gpi_log/gpi_logging.c
)
target_include_directories(gpilog
	PRIVATE ${PYTHON_INCLUDE_DIRS}
)
target_compile_definitions(gpilog PRIVATE
	FILTER
)
target_link_libraries_with_dynamic_lookup(gpilog
	${PYTHON_LIBRARIES}
)
install(TARGETS gpilog DESTINATION cocotb)

# cocotbutils
add_library(cocotbutils SHARED
	${SHARE_DIR}/lib/utils/cocotb_utils.c
)
target_include_directories(cocotbutils
	PRIVATE ${PYTHON_INCLUDE_DIRS}
)
install(TARGETS cocotbutils DESTINATION cocotb)

# cocotb
add_library(cocotb SHARED
	${SHARE_DIR}/lib/embed/gpi_embed.c
)
target_link_libraries(cocotb
	cocotbutils
	gpilog
	${PYTHON_LIBRARIES}
)
target_link_libraries_with_dynamic_lookup(cocotb
	${PYTHON_LIBRARIES}
)
target_compile_definitions(cocotb PRIVATE
	PYTHON_SO_LIB=${PYTHON_LIBRARIES}
)
target_include_directories(cocotb PRIVATE
	${PYTHON_INCLUDE_DIRS}
)
install(TARGETS cocotb DESTINATION cocotb)

# gpi
add_library(gpi SHARED
	${SHARE_DIR}/lib/gpi/GpiCbHdl.cpp
	${SHARE_DIR}/lib/gpi/GpiCommon.cpp
)
target_link_libraries(gpi
	cocotbutils
	gpilog
	cocotb
)
target_compile_definitions(gpi PRIVATE
	VPI_CHECKING
	SINGLETON_HANDLES
	LIB_EXT=CMAKE_SHARED_LIBRARY_SUFFIX
)
install(TARGETS gpi DESTINATION cocotb)


# simulator
add_library(simulator MODULE
	${SHARE_DIR}/lib/simulator/simulatormodule.c
)
target_link_libraries(simulator
	cocotbutils
	gpilog
	gpi
)
python_extension_module(simulator)
install(TARGETS simulator DESTINATION cocotb)

# vpi
# TODO:
# temporary hack for cvc
# ifeq ($(SIM),cvc)
#     GXX_ARGS    += -DMODELSIM
# endif

add_library(vpi SHARED
	${SHARE_DIR}/lib/vpi/VpiCbHdl.cpp
	${SHARE_DIR}/lib/vpi/VpiImpl.cpp
)
target_link_libraries(vpi
	gpilog
	gpi
)
target_compile_definitions(vpi PRIVATE
	VPI_CHECKING
)
install(TARGETS vpi DESTINATION cocotb)

# vhpi
add_library(vhpi SHARED
	${SHARE_DIR}/lib/vhpi/VhpiCbHdl.cpp
	${SHARE_DIR}/lib/vhpi/VhpiImpl.cpp
)
target_link_libraries(vhpi
	gpilog
	gpi
)
target_compile_definitions(vhpi PRIVATE
	VHPI_CHECKING
)
install(TARGETS vhpi DESTINATION cocotb)
