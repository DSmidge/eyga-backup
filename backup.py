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


# Main class
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
		print("\n\n# db = " + str(self.__info.backup_db_type) + ", user = " + str(self.__info.backup_user_type) + ", " + self.__info.script_runtime.isoformat(' '))
		self.__process_all(True)

	# Test
	def test_shifting_time(self):
		self.__info.test_shifting_time()

	# Process all backup sections
	def __process_all(self, debug_mode):
		self.__process("db", self.__db_cmds_core, debug_mode)
		self.__process("user", self.__user_cmds_core, debug_mode)
		if self.__config.gd_upload_enable == "1":
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
				log.write("\n" + self.__info.script_runtime.replace(microsecond=0).isoformat(' '))
			start = datetime.now()
			subprocess.call(cmd.replace("{pwd_db}", self.__config.authentication_db).replace("{pwd_7z}", self.__config.authentication_7z), shell=True)
			stop = datetime.now()
			with open(self.__config.backup_dirpath + "/backup.log", "a") as log:
				log.write(", " + backup_x + " = " + str(round((stop - start).total_seconds(), 1)) + "s")
				if self.__config.backup_verbose == "1":
					log.write(", commands:\n" + cmd + " #")
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
			self.backup_verbose       = config.get(config_section, "backup_verbose")
			self.db_root_dirpath      = config.get(config_section, "db_root_dirpath")
			self.db_temp_dirpath_full = config.get(config_section, "db_temp_dirpath_full")
			self.db_temp_dirpath_diff = config.get(config_section, "db_temp_dirpath_diff")
			self.db_backup_mode       = config.get(config_section, "db_backup_mode")
			self.db_binlog_dirpath    = config.get(config_section, "db_binlog_dirpath")
			self.db_binlog_rm_hours   = config.get(config_section, "db_binlog_rm_hours")
			self.db_default_user      = config.get(config_section, "db_default_user")
			self.db_ignore            = config.get(config_section, "db_ignore").split("|")
			self.db_ignore_users      = config.get(config_section, "db_ignore_users")
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
			self.diff_backup          = config.getboolean(config_section, "diff_backup")
			self.gd_upload_enable     = config.getint(config_section, "gd_upload_enable")
		
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
				self.__config.__split_day_by_hour = 0
			if self.__config.split_week_by_day > 6:
				self.__config.__split_week_by_day = 0
			if self.__config.full_backup_weeks < 2:
				self.__config.__full_backup_weeks = 2
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
			# Calculate week number
			week_start_1 = (datetime(2014, 12, 28) + timedelta(hours=day_hours)) # Corrections must be on Monday
			week_start_2 = (script_runtime - timedelta(hours=week_hours))
			shifted_week = int(((week_start_2 - week_start_1).days / 7) % self.__config.full_backup_weeks)
			# Set attributes
			self.__set_backup_info(shifted_hour, shifted_weekday, shifted_week)
		
		# Define type of backup (full or diff)
		def __set_backup_info(self, shifted_hour, shifted_weekday, shifted_week):
			hour = "h" + ("0" + str(shifted_hour))[-2:]
			day = "d" + str(shifted_weekday)
			week = "w" + str(shifted_week + 1)
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
					print("runtume: " + script_runtime.isoformat(' ') + ""
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
			db_list = os.listdir(db_root_dirpath)
			# Add files to ignored list
			for db in db_list:
				if db[0] == "#" or os.path.isfile(db_root_dirpath + "/" + db):
					db_ignore.append(db)
			# Remove ignored
			for db in db_ignore:
				if db in db_list:
					db_list.remove(db)
			# Sort and return
			db_list.sort()
			return db_list
		
		# User list
		@staticmethod
		def __user_list(user_root_dirpath, user_ignore):
			user_list = os.listdir(user_root_dirpath)
			# Remove ignored
			for user in user_ignore:
				if user in user_list:
					user_list.remove(user)
			# Sort and return
			user_list.sort()
			return user_list
		
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
				backup_filename = user + "-" + backup_x + "-" + backup_x_type + "-" + self.__info.backup_time + ".7z"
				# Create a place for storing SQL files
				if backup_x == "sql" and not os.path.isdir(db_dirpath):
					os.makedirs(db_dirpath, mode=755)
				# Set attributes
				self.backup_dirpath     = backup_dirpath
				self.backup_filename    = backup_filename
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
			self.__params_mysqldump     = "--skip-extended-insert --single-transaction --routines --triggers --events --no-tablespaces --mysqld-long-query-time=300"
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
				path.set(user, "sql", self.__info.backup_db_type, self.__info.backup_db_time)
				# Export all databases from specific user to files
				if user == self.__config.db_default_user:
					if self.__config.db_backup_mode == "binlog":
						# Backup binary logs
						if self.__info.backup_db_type == "full":
							db_cmds_user_7z.append(self.__mysql_flush_logs())
							db_cmds_user_7z.append(self.__mysql_purge_logs())
						if self.__config.diff_backup == True and self.__info.backup_db_type == "diff":
							db_cmds_user_7z.append(self.__mysql_backup_binlog(self.__config.db_binlog_dirpath, path.backup_dirpath, path.backup_filename))
					# Backup database permissions
					if self.__info.backup_db_type == "full":
						db_cmds_user_7z.append(self.__mysqldump_permissions(path.db_dirpath, self.__config.db_ignore_users, False) + ""
								"" + self.__7z_append("mysql.sql", path.backup_dirpath, path.backup_filename))
				for db in self.__lists.db_list_by_users[user]:
					# Full backup with binary logs
					if self.__config.db_backup_mode == "binlog" and self.__info.backup_db_type == "full":
						db_cmds_user_7z.append((self.__mysqldump_full(db, path.db_dirpath, False) + ""
								"" + self.__7z_append(db + ".sql", path.backup_dirpath, path.backup_filename)))
					# Full backup OR force full backup on diff
					if self.__config.db_backup_mode == "dumpdiff" and (self.__info.backup_db_type == "full" or self.__info.backup_db_type == "diff" and not os.path.isfile(path.db_dirpath_full + "/" + db + ".sql")):
						db_cmds_user.append(self.__mysqldump_full(db, path.db_dirpath, True))
					# Diff backup
					if self.__config.diff_backup == True and self.__config.db_backup_mode == "dumpdiff" and self.__info.backup_db_type == "diff":
						db_cmds_user_7z.append(self.__mysqldump_diff(db, path.db_dirpath, path.db_dirpath_full, False) + ""
								"" + self.__7z_append(db + ".sql.diff", path.backup_dirpath, path.backup_filename))
				# Compress databases
				if (len(db_cmds_user) > 0):
					db_cmds_user.insert(0, "if [ \"$(ls -A " + path.db_dirpath + ")\" ]; then rm " + path.db_dirpath + "/*; fi")
					db_cmds_user.append(self.__7z_create(path.db_temp_dirpath, user, None, path.backup_dirpath, path.backup_filename))
				if len(db_cmds_user_7z) > 0:
					db_cmds_user.extend(db_cmds_user_7z)
				# Upload to Google Drive
				gd_file = path.backup_dirpath + "/" + path.backup_filename
				if os.path.isfile(gd_file):
					db_cmds_gd.append("python \"" + self.__config.script_dirpath + "googledrive.py\""
							" '" + gd_file + "' 'Diff for " + str(self.__info.backup_db_time).upper() + "'")
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
				path.set(user, "user", self.__info.backup_user_type, self.__info.backup_user_time)
				user_path_ignore = self.__lists.user_path_ignore_list.get(user)
				# Full backup
				if self.__info.backup_user_type == "full":
					user_cmds.append(self.__7z_create(self.__config.user_root_dirpath, user, user_path_ignore, path.backup_dirpath, path.backup_filename))
				# Diff backup
				if self.__info.backup_user_type == "diff":
					user_cmds.append(self.__7z_update(self.__config.user_root_dirpath, user, user_path_ignore, path.backup_dirpath, path.backup_filename, path.user_filepath_full))
					# Upload to Google Drive
					gd_file = path.backup_dirpath + "/" + path.backup_filename
					if os.path.isfile(gd_file):
						user_cmds_gd.append("python \"" + self.__config.script_dirpath + "googledrive.py\""
								" '" + gd_file + "' 'Diff for " + str(self.__info.backup_user_time).upper() + "'")
			return user_cmds, user_cmds_gd
		
		def __mysqldump_permissions(self, db_dirpath, db_ignore_users, to_file):
			rcmd = ("{ mysqldump {pwd_db} " + self.__params_mysqldump + " --no-create-info --databases mysql --tables db user;"
					" echo \"\\nFLUSH PRIVILEGES;\"; }"
					" | sed \"17s/^$/\\nUSE \`mysql\`;\\n/\""
					" | grep --invert-match --extended-regexp \"^INSERT INTO \`user\` VALUES \('(\w|\-|\.)*','(" + db_ignore_users + ")',\""
					"" + (" > \"" + db_dirpath + "/mysql.sql\"" if to_file else ""))
			return rcmd
		
		def __mysql_flush_logs(self):
			return "echo \"FLUSH LOGS;\" | mysql {pwd_db} " + self.__params_mysql
		
		def __mysql_purge_logs(self):
			if self.__config.db_binlog_rm_hours.isdigit() and int(self.__config.db_binlog_rm_hours) > 0:
				return "echo \"PURGE BINARY LOGS BEFORE '" + (self.__info.script_runtime - timedelta(hours=int(self.__config.db_binlog_rm_hours))).isoformat() + "';\" | mysql {pwd_db} " + self.__params_mysql
			else:
				return ""
		
		def __mysqldump_full(self, db, db_dirpath, to_file):
			rcmd = ("{ echo \"SET SESSION UNIQUE_CHECKS = 0;\\nSET SESSION FOREIGN_KEY_CHECKS = 0;\\n\\n\"; "
					"{nice}mysqldump {pwd_db} " + self.__params_mysqldump + " --databases " + db + "; }"
					"" + (" > \"" + db_dirpath + "/" + db + ".sql\"" if to_file else ""))
			return rcmd
		
		def __mysqldump_diff(self, db, db_dirpath, db_dirpath_full, to_file):
			rcmd = ("{nice}mysqldump {pwd_db} " + self.__params_mysqldump + " --databases " + db + ""
					" | diff \"" + db_dirpath_full + "/" + db + ".sql\" -"
					"" + (" > \"" + db_dirpath + "/" + db + ".sql.diff\"" if to_file else ""))
			return rcmd
		
		def __mysql_backup_binlog(self, db_binlog_dirpath, backup_dirpath, backup_filename):
			filepath_7z = backup_dirpath + "/" + backup_filename
			rcmd = ("logs=`echo \"SHOW BINARY LOGS;\" | mysql {pwd_db} " + self.__params_mysql + " | tail -n1 | awk '{print $1}'`\n"
					"" + self.__mysql_flush_logs() + "\n"
					"for log in $logs; do\n"
					"    if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
					"    {nice}7z a {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					" \"" + filepath_7z + "\" \"" + db_binlog_dirpath + "/$log\""
					" > /dev/null\n"
					"done")
			return rcmd
		
		def __mysqloptimize(self):
			rcmd = ("{nice}mysqloptimize {pwd_db} " + self.__params_mysqloptimize + " --all-databases"
					" > \"" + self.__config.backup_dirpath + "/mysqloptimize.log\"")
			return rcmd
		
		def __7z_create(self, source_dirpath, source_name, extra_params, backup_dirpath, backup_filename):
			if not os.path.isdir(backup_dirpath):
				os.makedirs(backup_dirpath, mode=755)
			filepath_7z = backup_dirpath + "/" + backup_filename
			rcmd = ("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
					"{nice}7z a {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					"" + (extra_params if extra_params != None else "") + ""
					" \"" + filepath_7z + "\" \"" + source_dirpath + "/" + source_name + "\""
					" > /dev/null")
			return rcmd
		
		def __7z_append(self, source_name, backup_dirpath, backup_filename):
			filepath_7z = backup_dirpath + "/" + backup_filename
			rcmd = (" | {nice}7z a {pwd_7z} " + self.__params_7z + " -si" + source_name + ""
					" \"" + filepath_7z + "\""
					" > /dev/null")
			return rcmd
		
		def __7z_update(self, source_dirpath, source_name, extra_params, backup_dirpath, backup_filename, user_filepath_full):
			if not os.path.isfile(user_filepath_full):
				return "# Missing file for 7z update: " + user_filepath_full
			filepath_7z = backup_dirpath + "/" + backup_filename
			# http://a32.me/2010/08/7zip-differential-backup-linux-windows/
			rcmd = ("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
					"{nice}7z u {pwd_7z} " + self.__params_7z + " -w\"" + self.__config.backup_dirpath_tmp + "\""
					"" + (extra_params if extra_params != None else "") + ""
					" \"" + user_filepath_full + "\" \"" + source_dirpath + "/" + source_name + "\""
					" -u- -up0q3r2x2y2z0w2\!\"" + filepath_7z + "\""
					" > /dev/null")
			return rcmd


# Main
if __name__ == "__main__":
	if len(sys.argv) == 1:
		EygaBackup(datetime.now()).execute()
	else:
		# Debug
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
