#!/bin/bash

Xvfb :0 -screen 0 1x1x8 &

export TEMP="C:\windows\temp"

ln -s /opt/work/tools/midl.py /opt/work/tools/midl
ln -s /opt/work/tools/midl.py /opt/work/tools/midl.exe
ln -s /opt/work/tools/rc.py /opt/work/tools/rc
ln -s /opt/work/tools/rc.py /opt/work/tools/rc.exe


# Add the tools directory to the PATH
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

exec "$@"