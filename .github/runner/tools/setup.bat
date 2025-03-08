@echo off
:: LINK.EXE fails on the final stage of the build process
:: when there's no TEMP variable in the docker environment.
:: There doesn't seem to be any TEMP variable when we pre-bake the /root/.wine folder
:: So we do this janky method instead.

:: Set default TEMP if not defined or empty
echo Checking TEMP environment variable...
if not defined TEMP (
  echo WARNING: TEMP environment variable is not defined!
) else (
  if "%TEMP%"=="" (
    echo WARNING: TEMP environment variable is empty!
  ) else (
    echo SUCCESS: TEMP environment variable is defined as: "%TEMP%"
    goto :check_dir
  )
)

echo Attempting to create and set TEMP variable...
:: Try to use common Wine temp locations
if exist "C:\windows\temp\" (
  set "TEMP=C:\windows\temp"
) else if exist "C:\temp\" (
  set "TEMP=C:\temp"
) else if exist "%USERPROFILE%\Temp\" (
  set "TEMP=%USERPROFILE%\Temp"
) else if exist "%USERPROFILE%\Local Settings\Temp\" (
  set "TEMP=%USERPROFILE%\Local Settings\Temp"
) else (
  :: Create a temp directory if none exists
  echo Creating Temp directory in C:\ drive...
  mkdir "C:\temp" 2>nul
  set "TEMP=C:\temp"
)

:: Set TMP variable to the same value
set "TMP=%TEMP%"

:: Verify TEMP is now set and not empty
if not defined TEMP (
  echo ERROR: Failed to set TEMP environment variable!
  goto :error
) else (
  if "%TEMP%"=="" (
    echo ERROR: TEMP environment variable is still empty!
    goto :error
  ) else (
    echo SUCCESS: TEMP environment variable set to: "%TEMP%"
  )
)

:check_dir
echo.
:: Check if the directory exists
echo Checking if TEMP directory exists at: "%TEMP%"...
if not exist "%TEMP%\" (
  echo WARNING: TEMP directory does not exist!
  echo Attempting to create TEMP directory...
  mkdir "%TEMP%" 2>nul
  if not exist "%TEMP%\" (
    echo ERROR: Failed to create TEMP directory!
    goto :error
  ) else (
    echo SUCCESS: TEMP directory created at: "%TEMP%"
  )
) else (
  echo SUCCESS: TEMP directory exists at: "%TEMP%"
)
echo.

:: Root of Visual Developer Studio Common files.
set ToolsRoot=Z:\opt\work\tools\VC6SP6
set VSCommonDir=%ToolsRoot%\Common
::
:: Root of Visual Developer Studio installed files.
::
set MSDevDir=%ToolsRoot%\Common\msdev98
::
:: Root of Visual C++ installed files.
::
set MSVCDir=%ToolsRoot%\VC98
::
:: VcOsDir is used to help create either a Windows 95 or Windows NT specific path.
::
set VcOsDir=WIN95
if "%OS%" == "Windows_NT" set VcOsDir=WINNT
::
echo Setting environment for using Microsoft Visual C++ tools.
::
if "%OS%" == "Windows_NT" set PATH=%MSDevDir%\BIN;%MSVCDir%\BIN;%VSCommonDir%\TOOLS\%VcOsDir%;%VSCommonDir%\TOOLS;%PATH%
if "%OS%" == "" set PATH="%MSDevDir%\BIN";"%MSVCDir%\BIN";"%VSCommonDir%\TOOLS\%VcOsDir%";"%VSCommonDir%\TOOLS";"%windir%\SYSTEM";"%PATH%"
set INCLUDE=%MSVCDir%\ATL\INCLUDE;%MSVCDir%\INCLUDE;%MSVCDir%\MFC\INCLUDE;%INCLUDE%
set LIB=%MSVCDir%\LIB;%MSVCDir%\MFC\LIB;%LIB%

:: Add some debug output for PATH
echo PATH=%PATH%
echo INCLUDE=%INCLUDE%
echo LIB=%LIB%

set VcOsDir=
set VSCommonDir=

exit /b 0

:error
echo.
echo =========================================
echo Wine TEMP directory test FAILED!
echo =========================================
echo.
echo Suggestions to fix TEMP directory issues:
echo 1. Manually set TEMP and TMP environment variables in Wine configuration
echo 2. Create a TEMP directory manually (e.g., C:\windows\temp or C:\temp)
echo 3. Check Wine permissions to write to directories
echo.
exit /b 1