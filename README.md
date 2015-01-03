eyga-backup
===========

Backup script for MySQL databases and Linux user files.
Full MySQL backup is created once per day and diffs are created on every hour.
Linux user files are backed up once per week and diffs are created every day.

Uses 7-Zip for compression:
- because backups can be opened in Windows and
- can create update (added, deleted, modified files) achieves based on full archives.
Uploads databases and user file diffs to Google Drive. In my case full backup of user files takes too much space.

Some performance improvements could me made - check TODO at the end of Python files.
