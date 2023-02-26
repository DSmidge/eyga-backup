@echo off
cd ..
copy /y authentications.sample.cfg authentications.cfg
copy /y test\settings_binlog.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_binlog_py27.txt
C:\Python311\python backup.py debug > test\test_binlog_py3x.txt
copy /y test\settings_diff.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_diff_py27.txt
C:\Python311\python backup.py debug > test\test_diff_py3x.txt
pause
