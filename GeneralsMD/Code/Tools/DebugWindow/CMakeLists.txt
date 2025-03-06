set(DEBUGWINDOW_SRC
    "DebugWindow.cpp"
    "DebugWindow.h"
    "DebugWindowDialog.cpp"
    "DebugWindowDialog.h"
    "DebugWindowExport.h"
    "StdAfx.cpp"
    "StdAfx.h"
)

add_library(debugwindow SHARED)

if(WIN32 OR "${CMAKE_SYSTEM}" MATCHES "Windows")
    target_compile_definitions(debugwindow PRIVATE _AFXDLL)
    target_sources(debugwindow PRIVATE
        DebugWindow.rc
        DebugWindow.def
    )
endif()

target_sources(debugwindow PRIVATE ${DEBUGWINDOW_SRC})
