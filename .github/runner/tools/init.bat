@echo off
:: This script initializes the Wine profile on build
:: so that we don't have to on runtime.
call Z:\opt\work\tools\setup.bat
CL /?
LINK /?
MIDL /?
RC /?
