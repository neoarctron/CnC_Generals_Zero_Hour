#!/bin/bash

cd /opt/work/repo/

export SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export TOOLS_DIR="$PARENT_DIR/tools"
export PATH="$TOOLS_DIR:$PATH"

cd /opt/work/build/

cmake -DCMAKE_TOOLCHAIN_FILE="$PARENT_DIR/vc6-toolchain.cmake" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
      -DCMAKE_MSVC_RUNTIME_LIBRARY="MultiThreaded$<$<CONFIG:Debug>:Debug>DLL" \
      -DTHYME_FLAGS="/W3" \
      -G "Unix Makefiles" \
      /opt/work/repo

cmake --build . -j $(nproc)