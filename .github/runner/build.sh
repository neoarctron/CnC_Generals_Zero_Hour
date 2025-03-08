#!/bin/bash
echo $PWD
cd /opt/work/repo/ 
export TOOLS_DIR="/opt/work/tools/"
export PATH="$TOOLS_DIR:$PATH"

echo $TOOLS_DIR
echo $PATH
echo $PWD
ls /opt/work
ls /opt
cd /opt/work/build/
echo $PWD
cmake -DCMAKE_TOOLCHAIN_FILE="/opt/work/vc6-toolchain.cmake" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
      -DCMAKE_MSVC_RUNTIME_LIBRARY="MultiThreaded$<$<CONFIG:Debug>:Debug>DLL" \
      -DTHYME_FLAGS="/W3" \
      -G "Unix Makefiles" \
      /opt/work/repo

cmake --build . -j $(nproc)