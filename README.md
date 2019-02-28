# Eyga Backup

Backup script for MySQL databases and Linux user files.
Full MySQL backup is created once per day and diffs are created on every hour.
Linux user files are backed up once per week and diffs are created every day.

Uses 7-Zip for compression:
- because backups can be opened in Windows and
- can create update (added, deleted, modified files) achieves based on full archives.

Uploads databases and user file diffs to Google Drive. In my case full backup of user files takes too much space.
Run googledrive.py manually once to set the credentials.

Some performance improvements could be made - check TODO at the end of Python files.


Installation and configuration:
- install p7zip-full package
- install python libraries https://developers.google.com/api-client-library/python/start/installation
- create a new "Google APIs" project on https://console.developers.google.com/project
- enable "Drive API" on https://console.developers.google.com/apis/library
- create "OAuth client ID" credentials to get client "id" and "sectet" on https://console.developers.google.com/apis/credentials
- rename google_credentials.sample.cfg to google_credentials.cfg and set clinet "id" and "secret" parameters
- run googledrive.py directly to link the app with Google Drive
- rename passwords.sample.cfg to passwords.cfg and set passwords for database and 7z
- rename settings.sample.cfg to settings.cfg and set source and destination folders, etc.
- add a cron/job schedule to run backup.py once per hour
- don't write full logs to disk if using binary logs
