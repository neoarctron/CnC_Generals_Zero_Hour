#!/bin/bash

Xvfb :0 -screen 0 1x1x8 &

export TEMP="C:\windows\temp"

ln -s /opt/work/tools/midl.py /opt/work/tools/midl
ln -s /opt/work/tools/midl.py /opt/work/tools/midl.exe
ln -s /opt/work/tools/rc.py /opt/work/tools/rc
ln -s /opt/work/tools/rc.py /opt/work/tools/rc.exe

exec "$@"