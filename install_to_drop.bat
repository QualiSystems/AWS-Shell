call kill_python.bat
cd package
del /Q /S cloudshell\cp\aws\*.pyc
"C:\TFS\QualiSystems\Trunk\Drop\TestShell\ExecutionServer\python\2.7.10\python.exe" setup.py develop
cd ..\