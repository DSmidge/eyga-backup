#!/usr/bin/python
# Copyright Eyga.net
# For python 2.7, 3.x

# Import modules
try:
	# Python 3
	import configparser
except ImportError:
	# Python 2
	import ConfigParser as configparser # type: ignore
import os
import subprocess
import sys
from datetime import datetime, timedelta


# Backup class
class EygaBackup(object):
	# pylint: disable=anomalous-backslash-in-string

	# Execute backup for specific time
	def __init__(self, script_runtime):
		# Config data
		config = self.Config()
		# Type of backup and backup file name
		info = self.BackupInfo(script_runtime, config)
		# List of databases and user dirs to backup
		lists = self.Lists(config)
		# Prepare variables
		self.__config         = config
		self.__info           = info
		self.__extcmd_nice    = "nice -n {nice} ".format(nice=config.extcmd_nice) if config.extcmd_nice != "" else ""

		# Prepare database and user dirs commands for archiving
		cmds = self.BackupCommands(config, info, lists)
		db_cmds = cmds.db_cmds()
		(self.__db_cmds_core, self.__db_cmds_gd) = (None, None)
		if db_cmds is not None:
			(self.__db_cmds_core, self.__db_cmds_gd) = db_cmds
		user_cmds = cmds.user_cmds()
		(self.__user_cmds_core, self.__user_cmds_gd) = (None, None)
		if user_cmds is not None:
			(self.__user_cmds_core, self.__user_cmds_gd) = user_cmds

	# Execute backup commands
	def execute(self):
		self.__process_all(False)

	# Print debug text
	def debug(self):
		print("\n\n# db = " + str(self.__info.backup_db_type) + ", user = " + str(self.__info.backup_user_type) + ", " + self.__info.script_runtime.isoformat(" "))
		self.__process_all(True)

	# Test
	def test_shifting_time(self):
		self.__info.test_shifting_time()

	# Process all backup sections
	def __process_all(self, debug_mode):
		self.__process("db", self.__db_cmds_core, debug_mode)
		self.__process("user", self.__user_cmds_core, debug_mode)
		if self.__config.gd_upload_enable == True:
			self.__process("db_gd", self.__db_cmds_gd, debug_mode)
			self.__process("user_gd", self.__user_cmds_gd, debug_mode)

	# Process specific backup section
	def __process(self, backup_x, cmds, debug_mode):
		if cmds is None:
			return
		cmds = list(filter(None, cmds))
		if len(cmds) == 0:
			return
		cmd = "\n".join(cmds).replace("{nice}", self.__extcmd_nice)
		if not debug_mode:
			with open(self.__config.backup_dirpath + "/backup.log", "a") as log:
				log.write("\n" + self.__info.script_runtime.replace(microsecond=0).isoformat(" "))
			start = datetime.now()
			subprocess.call(cmd.replace("{pwd_db}", self.__config.authentication_db).replace("{pwd_7z}", self.__config.authentication_7z), shell=True, executable="/bin/bash")
			stop = datetime.now()
			with open(self.__config.backup_dirpath + "/backup.log", "a") as log:
				log.write(", " + backup_x + " = " + str(round((stop - start).total_seconds(), 1)) + "s")
				if self.__config.backup_verbose == True:
					log.write(", commands:\n" + cmd")
		else:
			print(cmd)


	# Configuration
	class Config(object):
		script_dirpath = None
		
		def __init__(self):
			# Define execution path
			if self.script_dirpath is None:
				script_dirpath = os.path.dirname(sys.argv[0])
				if len(script_dirpath) > 0:
					script_dirpath += "/"
				self.script_dirpath = script_dirpath
			# Set configuration attributes
			self.__settings("settings.cfg")
			self.__authentications("authentications.cfg")
		
		# Get the path of the configuration file
		def __get_config_filepath(self, config_filename):
			config_filepath = self.script_dirpath + config_filename
			if not os.path.isfile(config_filepath):
				print("Configuration file '" + config_filepath + "' is missing.")
				sys.exit(1)
			return config_filepath
		
		# Read settings from config file
		def __settings(self, config_filename):
			config_filepath = self.__get_config_filepath(config_filename)
			config = configparser.RawConfigParser()
			config.read(config_filepath)
			config_section            = "settings"
			# Result
			self.backup_dirpath       = config.get(config_section, "backup_dirpath")
			self.backup_dirpath_tmp   = config.get(config_section, "backup_dirpath_tmp")
			self.backup_verbose       = config.getboolean(config_section, "backup_verbose")
			self.db_root_dirpath      = config.get(config_section, "db_root_dirpath")
			self.db_temp_dirpath_full = config.get(config_section, "db_temp_dirpath_full")
			self.db_temp_dirpath_diff = config.get(config_section, "db_temp_dirpath_diff")
			self.db_backup_mode       = config.get(config_section, "db_backup_mode")
			self.db_dumpdiff_pipecmd  = config.get(config_section, "db_dumpdiff_pipecmd")
			self.db_binlog_dirpath    = config.get(config_section, "db_binlog_dirpath")
			self.db_binlog_rm_hours   = config.get(config_section, "db_binlog_rm_hours")
			self.db_default_user      = config.get(config_section, "db_default_user")
			self.db_ignore            = config.get(config_section, "db_ignore").split("|")
			self.db_ignore_users      = config.get(config_section, "db_ignore_users").split("|")
			self.db_optimize          = config.getboolean(config_section, "db_optimize")
			self.user_root_dirpath    = config.get(config_section, "user_root_dirpath")
			self.user_ignore          = config.get(config_section, "user_ignore").split("|")
			self.user_path_ignore     = config.get(config_section, "user_path_ignore")
			self.sevenzip_mx          = config.get(config_section, "sevenzip_mx")
			self.sevenzip_mmt         = config.get(config_section, "sevenzip_mmt")
			self.extcmd_nice          = config.get(config_section, "extcmd_nice")
			self.split_week_by_day    = config.getint(config_section, "split_week_by_day")
			self.split_day_by_hour    = config.getint(config_section, "split_day_by_hour")
			self.full_backup_weeks    = config.getint(config_section, "full_backup_weeks")
			self.db_diff_backup       = config.getboolean(config_section, "db_diff_backup")
			self.gd_upload_enable     = config.getboolean(config_section, "gd_upload_enable")

		# Read authentications form config file
		def __authentications(self, config_filename):
			config_filepath = self.__get_config_filepath(config_filename)
			config = configparser.RawConfigParser()
			config.read(config_filepath)
			config_section         = "authentications"
			# Result
			self.authentication_db = config.get(config_section, "authentication_db")
			self.authentication_7z = config.get(config_section, "authentication_7z")


	# Define period start times and backup types
	class BackupInfo(object):
		
		def __init__(self, script_runtime, config):
			self.script_runtime = script_runtime
			self.__config = config
			if self.__config.split_day_by_hour > 23:
				self.__config.split_day_by_hour = 0
			if self.__config.split_week_by_day > 6:
				self.__config.split_week_by_day = 0
			if self.__config.full_backup_weeks < 2:
				self.__config.full_backup_weeks = 2
			self.__set_shifted_time()
		
		# Shift time to hour of full backup
		def __set_shifted_time(self, script_runtime = None):
			if script_runtime == None:
				script_runtime = self.script_runtime
			# Fix hour
			day_hours = self.__config.split_day_by_hour
			shifted_hour = (script_runtime - timedelta(hours=day_hours)).hour
			# Fix weekday
			week_hours = 24 * self.__config.split_week_by_day + self.__config.split_day_by_hour
			shifted_weekday = (script_runtime - timedelta(hours=week_hours)).weekday()
			# Set attributes
			self.__set_backup_info(shifted_hour, shifted_weekday)
		
		# Define type of backup (full or diff)
		def __set_backup_info(self, shifted_hour, shifted_weekday):
			hour = "h" + ("0" + str(shifted_hour))[-2:]
			day = "d" + str(shifted_weekday)
			week = "w1"
			# Set backup type and time attributes
			if shifted_weekday == 0 and shifted_hour == 0:
				# Weekly backup (for last X weeks)
				self.__set_backup_attr(week, "full", None, "full", None, True)
			elif shifted_hour == 0:
				# Daily backup
				self.__set_backup_attr(day, "full", None, "diff", week, False)
			elif shifted_weekday == 0:
				# Hourly backup in week delimiter day
				self.__set_backup_attr(hour, "diff", week, None, None, False)
			else:
				# Hourly backup
				self.__set_backup_attr(hour, "diff", day, None, None, False)
		
		# Set backup attributes
		def __set_backup_attr(self, backup_time, backup_db_type, backup_db_time,
					backup_user_type, backup_user_time, db_optimize):
			self.backup_time      = backup_time
			self.backup_db_type   = backup_db_type
			self.backup_db_time   = backup_db_time
			self.backup_user_type = backup_user_type
			self.backup_user_time = backup_user_time
			self.db_optimize      = db_optimize
		
		# Test shifting hour, day and week calculations
		def test_shifting_time(self):
			print("\n\n# Test shifting time")
			year = 2023
			month = 1
			for day in range(2, 15):
				for hour in range(0, 23):
					script_runtime = datetime(year, month, day, hour)
					self.__set_shifted_time(script_runtime)
					print("runtume: " + script_runtime.isoformat(" ") + ""
							", time: " + str(self.backup_time) + ""
							", db_type: " + str(self.backup_db_type) + ""
							", db_time: " + str(self.backup_db_time) + ""
							", user_type: " + str(self.backup_user_type) + ""
							", user_time: " + str(self.backup_user_time) + "")


	# Lists of databases and users
	class Lists(object):
		
		def __init__(self, config):
			db_list                    = self.__db_list(config.db_root_dirpath, config.db_ignore)
			user_list                  = self.__user_list(config.user_root_dirpath, config.user_ignore)
			user_path_ignore_list      = self.__user_path_ignore_list(config.user_path_ignore)
			db_list_by_users           = self.__db_list_by_users(db_list, config.db_default_user, user_list)
			# Result
			self.user_list             = user_list
			self.user_path_ignore_list = user_path_ignore_list
			self.db_list_by_users      = db_list_by_users
		
		# Database list
		@staticmethod
		def __db_list(db_root_dirpath, db_ignore):
			listdir = os.listdir(db_root_dirpath)
			final_list = []
			# Add to list
			for db in listdir:
				if os.path.isdir(db_root_dirpath + "/" + db) and db not in db_ignore:
					final_list.append(db)
			# Sort and return
			final_list.sort()
			return final_list
		
		# User list
		@staticmethod
		def __user_list(user_root_dirpath, user_ignore):
			listdir = os.listdir(user_root_dirpath)
			final_list = []
			# Add to list
			for user in listdir:
				if user not in user_ignore:
					final_list.append(user)
			# Sort and return
			final_list.sort()
			return final_list
		
		# User path ignore list
		@staticmethod
		def __user_path_ignore_list(user_path_ignore):
			user_path_ignore_list = {}
			user_and_path_ignore_list = user_path_ignore.split("||")
			for user_and_path_ignore in user_and_path_ignore_list:
				user, path_ignore = user_and_path_ignore.split(":", 1)
				user_path_ignore_list[user] = " -x\!\"" + user + "/" + ("\" -x\!\"" + user + "/").join(path_ignore.split("|")) + "\""
			return user_path_ignore_list
		
		# Databases list by users
		@staticmethod
		def __db_list_by_users(db_list, db_default_user, user_list):
			db_list_by_users = {}
			for db in db_list:
				# Attach database to known user
				user_found = db_default_user
				for user in user_list:
					if db.find(user + "_") != -1:
						user_found = user
				if user_found not in db_list_by_users:
					db_list_by_users[user_found] = []
				db_list_by_users[user_found].append(db)
			return db_list_by_users


	# Define shell commands for backup execution
	class BackupCommands(object):
		
		# Set paths for backup
		class Path(object):
			
			def __init__(self, config, info):
				self.__config = config
				self.__info   = info
			
			# Set needed paths
			def set(self, user, backup_x, backup_x_type, backup_x_time):
				# Get dir and file info
				if backup_x_type == "full":
					db_temp_dirpath    = self.__config.db_temp_dirpath_full
					db_dirpath         = self.__config.db_temp_dirpath_full + "/" + user
					db_dirpath_full    = None
					user_filename_full = None
					user_filepath_full = None
				else:
					db_temp_dirpath    = self.__config.db_temp_dirpath_diff
					db_dirpath         = self.__config.db_temp_dirpath_diff + "/" + user
					db_dirpath_full    = self.__config.db_temp_dirpath_full + "/" + user
					user_filename_full = user + "-" + backup_x + "-full-" + backup_x_time + ".7z"
					user_filepath_full = self.__config.backup_dirpath + "/" + user + "/" + user_filename_full
				# Create a place for storing backup files
				backup_dirpath = self.__config.backup_dirpath + "/" + user
				if not os.path.isdir(backup_dirpath):
					os.makedirs(backup_dirpath, mode=755)
				backup_filenameN = user + "-" + backup_x + "-" + backup_x_type + "-{num}.7z"
				backup_filename = backup_filenameN.replace("{num}", self.__info.backup_time)
				# Create a place for storing SQL files
				if backup_x == "sql" and not os.path.isdir(db_dirpath):
					os.makedirs(db_dirpath, mode=755)
				# Set attributes
				self.backup_dirpath     = backup_dirpath
				self.backup_filename    = backup_filename
				self.backup_filepath    = backup_dirpath + "/" + backup_filename
				self.backup_filepathN   = backup_dirpath + "/" + backup_filenameN
				self.db_temp_dirpath    = db_temp_dirpath
				self.db_dirpath         = db_dirpath
				self.db_dirpath_full    = db_dirpath_full
				self.user_filename_full = user_filename_full
				self.user_filepath_full = user_filepath_full
		
		def __init__(self, config, info, lists):
			self.__config               = config
			self.__info                 = info
			self.__lists                = lists
			self.__params_mysql         = ""
			self.__params_mysqldump     = "--single-transaction --routines --triggers --events --no-tablespaces"
			self.__params_mysqloptimize = "--silent --skip-database=mysql"
			self.__params_7z            = "-bd -mhe=on -mf=off -mx={mx} -mmt={mmt}".format(mx=self.__config.sevenzip_mx, mmt=self.__config.sevenzip_mmt)
		
		# Prepare commands for backup of databases
		def db_cmds(self):
			if self.__info.backup_db_type is None:
				return
			# Separate backup for every user
			db_cmds = []
			db_cmds_gd = []
			path = self.Path(self.__config, self.__info)
			for user in self.__lists.db_list_by_users:
				db_cmds_user = []
				db_cmds_user_7z = []
				clear_tmp_dir = True
				path.set(user, "sql", self.__info.backup_db_type, self.__info.backup_db_time)
				# Export all databases from specific user to files
				if user == self.__config.db_default_user:
					# Backup binary logs
					if self.__config.db_backup_mode == "binlog":
						if self.__info.backup_db_type == "full":
							db_cmds_user_7z.append(self.__mysql_purge_logs())
						elif self.__info.backup_db_type == "diff" and self.__config.db_diff_backup == True:
							db_cmds_user_7z.append(self.__mysql_backup_binlog(self.__config.db_binlog_dirpath, path.backup_filepath))
					# Backup with mariabackup
					elif self.__config.db_backup_mode == "mariabackup":
						db_exclude = "" if self.__config.db_ignore == "" else "--databases-exclude=\"" + " ".join(self.__config.db_ignore) + "\" "
						check_time = False;
						if self.__info.backup_db_type == "full":
							check_time = True
							db_cmds_user.append(self.__mariabackup_full(db_exclude, path.db_dirpath))
						elif self.__info.backup_db_type == "diff" and self.__config.db_diff_backup == True and os.path.isdir(path.db_dirpath_full + "/mariadb"):
							check_time = True
							db_cmds_user.append(self.__mariabackup_diff(db_exclude, path.db_dirpath, path.db_dirpath_full))
						if check_time:
							check_file = path.db_dirpath + "/mariadb/backup-my.cnf"
							check_cmd = "if [ ! -f \"" + check_file + "\" ] || [ \"$(( $(date +\"%s\") - $(stat -c \"%Y\" \"" + check_file + "\") ))\" -gt \"1800\" ]; then echo \"MariaDB backup is missing or is older than 30 minutes.\"; fi"
							db_cmds_user.append(check_cmd)
					# Backup database users and grants
					if self.__info.backup_db_type == "full":
						db_cmds_user_7z.append(self.__mysql_users_and_grants(path.db_dirpath, self.__config.db_ignore_users, False) + ""
								"" + self.__7z_append(user, "mysql_users_and_grants.sql", path.backup_dirpath, path.backup_filepath))
				for db in self.__lists.db_list_by_users[user]:
					# Full backup with binary logs
					if self.__config.db_backup_mode == "binlog" and self.__info.backup_db_type == "full":
						db_cmds_user_7z.append((self.__mysqldump_full(db, path.db_dirpath, False) + ""
								"" + self.__7z_append(user, db + ".sql", path.backup_dirpath, path.backup_filepath)))
					# Backup with mysqldump
					elif self.__config.db_backup_mode == "mysqldump":
						# Full backup OR force full backup on diff
						if self.__info.backup_db_type == "full":
							db_cmds_user.append(self.__mysqldump_full(db, path.db_dirpath, True))
						# Diff backup
						elif self.__info.backup_db_type == "diff" and self.__config.db_diff_backup == True and os.path.isfile(path.db_dirpath_full + "/" + db + ".sql"):
							clear_tmp_dir = False
							db_cmds_user_7z.append(self.__mysqldump_diff(db, path.db_dirpath, path.db_dirpath_full, False) + ""
									"" + self.__7z_append(user, db + ".sql.diff", path.backup_dirpath, path.backup_filepath))
				# Archive databases
				if (len(db_cmds_user) > 0):
					if clear_tmp_dir == True:
						db_cmds_user.insert(0, "if [ -d \"" + path.db_dirpath + "\" ]; then rm -r \"" + path.db_dirpath + "\"; fi")
						db_cmds_user.insert(1, "if [ ! -d \"" + path.db_dirpath + "\" ]; then mkdir -p \"" + path.db_dirpath + "\"; fi")
					db_cmds_user_7z.append(self.__7z_create(path.db_temp_dirpath, user, None, path.backup_dirpath, path.backup_filepath))
				# Rotate backup files if needed
				if len(db_cmds_user_7z) > 0:
					if self.__info.backup_db_type == "full" and self.__info.backup_time == "w1":
						db_cmds_user.append(self.__rotate_backups(path.backup_filepathN))
					db_cmds_user.append("if [ -f \"" + path.backup_filepath + "\" ]; then rm \"" + path.backup_filepath + "\"; fi")
					db_cmds_user.extend(db_cmds_user_7z)
				# Upload to Google Drive
				if os.path.isfile(path.backup_filepath):
					db_cmds_gd.append("python \"" + self.__config.script_dirpath + "googledrive.py\""
							" '" + path.backup_filepath + "' 'Diff for " + str(self.__info.backup_db_time).upper() + "'")
				# Add to all commands
				if (len(db_cmds_user) > 0):
					db_cmds.extend(db_cmds_user)
			# Database optimizations
			if self.__config.db_optimize == True and self.__info.db_optimize == True:
				db_cmds.append(self.__mysqloptimize())
			return db_cmds, db_cmds_gd
		
		# Prepare commands for backup of user files
		def user_cmds(self):
			user_cmds = []
			user_cmds_gd = []
			if self.__info.backup_user_type is None:
				return
			# Separate backup for every user
			path = self.Path(self.__config, self.__info)
			for user in self.__lists.user_list:
				user_cmds_user = []
				user_cmds_user_7z = []
				path.set(user, "user", self.__info.backup_user_type, self.__info.backup_user_time)
				user_path_ignore = self.__lists.user_path_ignore_list.get(user)
				# Full backup
				if self.__info.backup_user_type == "full":
					user_cmds_user_7z.append(self.__7z_create(self.__config.user_root_dirpath, user, user_path_ignore, path.backup_dirpath, path.backup_filepath))
				# Diff backup
				if self.__info.backup_user_type == "diff":
					user_cmds_user_7z.append(self.__7z_update(self.__config.user_root_dirpath, user, user_path_ignore, path.backup_filepath, path.user_filepath_full))
					# Upload to Google Drive
					gd_file = path.backup_dirpath + "/" + path.backup_filename
					if os.path.isfile(gd_file):
						user_cmds_gd.append("python \"" + self.__config.script_dirpath + "googledrive.py\""
								" '" + gd_file + "' 'Diff for " + str(self.__info.backup_user_time).upper() + "'")
				# Rotate backup files if needed
				if (len(user_cmds_user_7z) > 0):
					if self.__info.backup_user_type == "full" and self.__info.backup_time == "w1":
						user_cmds_user.append(self.__rotate_backups(path.backup_filepathN))
					user_cmds_user.append("if [ -f \"" + path.backup_filepath + "\" ]; then rm \"" + path.backup_filepath + "\"; fi")
					user_cmds_user.extend(user_cmds_user_7z)
				# Add to all commands
				if (len(user_cmds_user) > 0):
					user_cmds.extend(user_cmds_user)
			return user_cmds, user_cmds_gd

		def __mysqldump_extra_params(self):
			params = "$(if [[ `mysql --version` == *\"MariaDB\"* ]]; then echo \"--skip-log-queries\"; else echo \"--mysqld-long-query-time=300\"; fi) "
			if self.__config.db_backup_mode == "mysqldump" and self.__config.db_diff_backup == True:
				params += "--skip-extended-insert "
			return params
		
		def __mysqldump_pipe(self):
			pipe = ""
			if self.__config.db_backup_mode == "mysqldump" and self.__config.db_diff_backup == True:
				pipe += " | " + self.__config.db_dumpdiff_pipecmd
			return pipe
		
		def __mysql_users_and_grants(self, db_dirpath, db_ignore_users, to_file):
			where = ""
			if len(db_ignore_users) > 0:
				like = "' AND User NOT LIKE '"
				where = like.join(db_ignore_users)
				if len(where) > 0:
					where = " WHERE '1'='1" + like + where + "'"
			userAtHost = "''', User, '''@''', Host, '''"
			rcmd = ("echo \"FLUSH PRIVILEGES; "
					"SELECT CONCAT('SHOW CREATE USER " + userAtHost + "; SHOW GRANTS FOR " + userAtHost + ";') AS cmd "
					"FROM mysql.user" + where + ";\""
					" | mysql {pwd_db} " + self.__params_mysql + " -N"
					" | mysql {pwd_db} " + self.__params_mysql + " -N"
					"" + (" > \"" + db_dirpath + "/mysql_users_and_grants.sql\"" if to_file else ""))
			return rcmd
		
		def __mysqldump_full(self, db, db_dirpath, to_file):
			rcmd = ("{ echo \"SET SESSION UNIQUE_CHECKS = 0;\\nSET SESSION FOREIGN_KEY_CHECKS = 0;\\n\\n\"; "
					"{nice}mysqldump {pwd_db} " + self.__mysqldump_extra_params() + self.__params_mysqldump + " --databases " + db + ""
					"" + self.__mysqldump_pipe() + "; }"
					"" + (" > \"" + db_dirpath + "/" + db + ".sql\"" if to_file else ""))
			return rcmd
		
		def __mysqldump_diff(self, db, db_dirpath, db_dirpath_full, to_file):
			rcmd = ("{nice}mysqldump {pwd_db} " + self.__mysqldump_extra_params() + self.__params_mysqldump + " --databases " + db + ""
					"" + self.__mysqldump_pipe() + ""
					" | diff \"" + db_dirpath_full + "/" + db + ".sql\" -"
					"" + (" > \"" + db_dirpath + "/" + db + ".sql.diff\"" if to_file else ""))
			return rcmd
		
		def __mariabackup_full(self, db_exclude, db_dirpath):
			rcmd = ("{nice}mariabackup {pwd_db} --backup " + db_exclude + ""
					"--target-dir=\"" + db_dirpath + "/mariadb\" &> /dev/null")
			return rcmd
		
		def __mariabackup_diff(self, db_exclude, db_dirpath, db_dirpath_full):
			rcmd = ("{nice}mariabackup {pwd_db} --backup " + db_exclude + ""
					"--target-dir=\"" + db_dirpath + "/mariadb\" "
					"--incremental-basedir=\"" + db_dirpath_full + "/mariadb\" &> /dev/null")
			return rcmd
		
		def __mysql_purge_logs(self):
			if self.__config.db_binlog_rm_hours.isdigit() and int(self.__config.db_binlog_rm_hours) > 0:
				return "echo \"PURGE BINARY LOGS BEFORE '" + (self.__info.script_runtime - timedelta(hours=int(self.__config.db_binlog_rm_hours))).isoformat() + "';\" | mysql {pwd_db} " + self.__params_mysql
			else:
				return ""
		
		def __mysql_backup_binlog(self, db_binlog_dirpath, backup_filepath):
			rcmd = ("echo \"FLUSH LOGS;\" | mysql {pwd_db} " + self.__params_mysql + "\n"
					"logs=`echo \"SHOW BINARY LOGS;\" | mysql {pwd_db} " + self.__params_mysql + " | tail -n1 | awk '{print $1}'`\n"
					"for log in $logs; do\n"
					"    if [ -f \"" + backup_filepath + "\" ]; then rm \"" + backup_filepath + "\"; fi\n"
					"    {nice}7z a {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					" \"" + backup_filepath + "\" \"" + db_binlog_dirpath + "/$log\""
					" > /dev/null\n"
					"done")
			return rcmd
		
		def __mysqloptimize(self):
			rcmd = ("{nice}mysqloptimize {pwd_db} " + self.__params_mysqloptimize + " --all-databases"
					" > \"" + self.__config.backup_dirpath + "/mysqloptimize.log\"")
			return rcmd
		
		def __rotate_backups(self, backup_filepathN):
			file0 = backup_filepathN.replace("{num}", "w1")
			rcmd = ("if [ -f \"" + file0 + "\" ] && [ $(date -r \"" + file0 + "\" +%G%V) -lt $(date +%G%V) ]; then\n")
			for num in range(self.__config.full_backup_weeks, 0, -1):
				file1 = backup_filepathN.replace("{num}", "w" + str(num))
				file2 = backup_filepathN.replace("{num}", "w" + str(num + 1))
				cmd = "rm \"" + file1 + "\"" if num == self.__config.full_backup_weeks else "mv \"" + file1 + "\" \"" + file2 + "\""
				rcmd += ("    if [ -f \"" + file1 + "\" ]; then " + cmd + "; fi\n")
			rcmd += ("fi")
			return rcmd
		
		def __7z_create(self, source_dirpath, source_name, extra_params, backup_dirpath, backup_filepath):
			if not os.path.isdir(backup_dirpath):
				os.makedirs(backup_dirpath, mode=755)
			rcmd = ("{nice}7z a {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					"" + (extra_params if extra_params != None else "") + ""
					" \"" + backup_filepath + "\" \"" + source_dirpath + "/" + source_name + "\""
					" > /dev/null")
			return rcmd
		
		def __7z_append(self, source_user, source_name, backup_dirpath, backup_filepath):
			if not os.path.isdir(backup_dirpath):
				os.makedirs(backup_dirpath, mode=755)
			rcmd = (" | {nice}7z a {pwd_7z} " + self.__params_7z + " -si\"" + source_user + "/" + source_name + "\""
					" \"" + backup_filepath + "\""
					" > /dev/null")
			return rcmd
		
		def __7z_update(self, source_dirpath, source_name, extra_params, backup_filepath, user_filepath_full):
			if not os.path.isfile(user_filepath_full):
				return "# Missing file for 7z update: " + user_filepath_full
			# http://a32.me/2010/08/7zip-differential-backup-linux-windows/
			rcmd = ("{nice}7z u {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					"" + (extra_params if extra_params != None else "") + ""
					" \"" + user_filepath_full + "\" \"" + source_dirpath + "/" + source_name + "\""
					" -u- -up0q3r2x2y2z0w2\!\"" + backup_filepath + "\""
					" > /dev/null")
			return rcmd


# Main
if __name__ == "__main__":
	if len(sys.argv) == 1:
		EygaBackup(datetime.now()).execute()
	elif sys.argv[1] == "test":
		EygaBackup(datetime.now()).debug()
	elif sys.argv[1] == "debug":
		print("# List of backup.py commands")
		script_runtime = datetime(2022, 12, 31, 1)
		EygaBackup(script_runtime).debug()
		script_runtime = datetime(2023, 1, 1, 1)
		EygaBackup(script_runtime).debug()
		script_runtime = datetime(2023, 1, 1, 2)
		EygaBackup(script_runtime).debug()
		EygaBackup(script_runtime).test_shifting_time()


# TODO:
#	Generate a file with chmod and chown commands (7z doesn't store this info)
#	Generate a file with restore commands (mysql imports, 7z extracts)
#	Disable (lock file) diffs when full backup is in progress
