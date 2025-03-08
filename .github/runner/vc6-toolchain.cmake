# Visual C++ 6.0 through Wine CMake toolchain file
# This toolchain file configures CMake to use our Python proxy scripts
# as the compiler and linker, which then forward commands to VC6 through Wine.

# Specify the platform
set(CMAKE_SYSTEM_NAME Windows)

# Define the paths to our proxy scripts
set(TOOLS_DIR "${CMAKE_CURRENT_LIST_DIR}/tools")
set(CL_PROXY "${TOOLS_DIR}/cl.py")
set(LINK_PROXY "${TOOLS_DIR}/link.py")
set(LIB_PROXY "${TOOLS_DIR}/lib.py")
set(MIDL_PROXY "${TOOLS_DIR}/midl.py")

# Configure the C and C++ compilers
set(CMAKE_C_COMPILER "${CL_PROXY}")
set(CMAKE_CXX_COMPILER "${CL_PROXY}")

# Configure the linker
set(CMAKE_LINKER "${LINK_PROXY}")

# VC6 specific compiler flags
set(CMAKE_C_FLAGS_INIT "")
set(CMAKE_CXX_FLAGS_INIT "")
set(CMAKE_C_FLAGS_DEBUG_INIT "")
set(CMAKE_CXX_FLAGS_DEBUG_INIT "")

# Configure the linker flags
set(CMAKE_EXE_LINKER_FLAGS_INIT "")
set(CMAKE_MODULE_LINKER_FLAGS_INIT "")

# Configure the library tool
set(CMAKE_AR "${LIB_PROXY}")
set(CMAKE_C_COMPILER_AR "${LIB_PROXY}")
set(CMAKE_CXX_COMPILER_AR "${LIB_PROXY}")
 
# Make sure we don't look for Unix binaries
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Add MIDL compiler command
set(CMAKE_MIDL_COMPILER "${MIDL_PROXY}")
