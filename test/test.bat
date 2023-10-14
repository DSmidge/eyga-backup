@echo off

echo Notes:
echo - Full backup file database for user user1 exists so diff can be made.
echo - Full backup file database for user system does not exist so full backup is made instead of diff.

cd ..
copy /y authentications.sample.cfg authentications.cfg

copy /y test\settings_binlog.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_binlog_py27.txt
python backup.py debug > test\test_binlog_py3x.txt

copy /y test\settings_mysqldump.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_mysqldump_py27.txt
python backup.py debug > test\test_mysqldump_py3x.txt

copy /y test\settings_mariabackup.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_mariabackup_py27.txt
python backup.py debug > test\test_mariabackup_py3x.txt

copy /y test\settings_binlog_nodbdiff.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_binlog_nodbdiff_py27.txt
python backup.py debug > test\test_binlog_nodbdiff_py3x.txt

copy /y test\settings_mysqldump_nodbdiff.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_mysqldump_nodbdiff_py27.txt
python backup.py debug > test\test_mysqldump_nodbdiff_py3x.txt

copy /y test\settings_mariabackup_nodbdiff.cfg settings.cfg
rem C:\Python27\python backup.py debug > test\test_mariabackup_nodbdiff_py27.txt
python backup.py debug > test\test_mariabackup_nodbdiff_py3x.txt

cd test
pause
