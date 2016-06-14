@echo off
pushd %CD%
cd drivers 
call pack.bat
popd

copy version.txt package/version.txt
copy version.txt drivers/version.txt
