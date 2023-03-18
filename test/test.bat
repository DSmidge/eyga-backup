@echo off

echo Notes:
echo - Full backup file database for user user1 exists so diff can be made.
echo - Full backup file database for user system does not exist so full backup is made instead of diff.

cd ..
copy /y authentications.sample.cfg authentications.cfg

copy /y test\settings_binlog.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_binlog_py27.txt
C:\Python311\python backup.py debug > test\test_binlog_py3x.txt

copy /y test\settings_dumpdiff.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_dumpdiff_py27.txt
C:\Python311\python backup.py debug > test\test_dumpdiff_py3x.txt

copy /y test\settings_binlog_nodbdiff.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_binlog_nodbdiff_py27.txt
C:\Python311\python backup.py debug > test\test_binlog_nodbdiff_py3x.txt

copy /y test\settings_dumpdiff_nodbdiff.cfg settings.cfg
C:\Python27\python backup.py debug > test\test_dumpdiff_nodbdiff_py27.txt
C:\Python311\python backup.py debug > test\test_dumpdiff_nodbdiff_py3x.txt

pause
