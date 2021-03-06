#!/usr/bin/python
# Copyright Eyga.net
# For python 2.7

# Import modules
import ConfigParser as configparser # Python 2
#import configparser # Python 3
import os
import subprocess
import sys
from datetime import datetime, timedelta


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
		self.__passwords("passwords.cfg")
	
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
		self.backup_dirpath       = config.get(config_section, "backup_dirpath")
		self.backup_dirpath_tmp   = config.get(config_section, "backup_dirpath_tmp")
		self.backup_verbose       = config.get(config_section, "backup_verbose")
		self.db_root_dirpath      = config.get(config_section, "db_root_dirpath")
		self.db_temp_dirpath_full = config.get(config_section, "db_temp_dirpath_full")
		self.db_temp_dirpath_diff = config.get(config_section, "db_temp_dirpath_diff")
		self.db_binlog_dirpath    = config.get(config_section, "db_binlog_dirpath")
		self.db_binlog_rm_hours   = config.get(config_section, "db_binlog_rm_hours")
		self.db_default_user      = config.get(config_section, "db_default_user")
		self.db_ignore            = config.get(config_section, "db_ignore").split("|")
		self.db_ignore_users      = config.get(config_section, "db_ignore_users")
		self.user_root_dirpath    = config.get(config_section, "user_root_dirpath")
		self.user_ignore          = config.get(config_section, "user_ignore").split("|")
		self.user_path_ignore     = config.get(config_section, "user_path_ignore")
		self.split_week_by_day    = config.getint(config_section, "split_week_by_day")
		self.split_day_by_hour    = config.getint(config_section, "split_day_by_hour")
		self.full_backup_weeks    = config.getint(config_section, "full_backup_weeks")
		self.gd_upload_enable     = config.getint(config_section, "gd_upload_enable")
	
	# Read passwords form config file
	def __passwords(self, config_filename):
		config_filepath = self.__get_config_filepath(config_filename)
		config = configparser.RawConfigParser()
		config.read(config_filepath)
		config_section   = "passwords"
		self.password_db = config.get(config_section, "password_db")
		self.password_7z = config.get(config_section, "password_7z")


# Define period start times and backup types
class BackupInfo(object):
	
	def __init__(self, script_runtime, split_day_by_hour, split_week_by_day, full_backup_weeks):
		if split_day_by_hour > 23:
			split_day_by_hour = 0
		if split_week_by_day > 6:
			split_week_by_day = 0
		if full_backup_weeks < 2:
			full_backup_weeks = 2
		self.__set_shifted_time(script_runtime, split_day_by_hour, split_week_by_day, full_backup_weeks)
	
	# Shift time to hour of full backup
	def __set_shifted_time(self, script_runtime, split_day_by_hour, split_week_by_day, full_backup_weeks):
		# Fix hour
		day_hours = split_day_by_hour
		shifted_hour = (script_runtime - timedelta(hours=day_hours)).hour
		# Fix weekday
		week_hours = 24 * split_week_by_day + split_day_by_hour
		shifted_weekday = (script_runtime - timedelta(hours=week_hours)).weekday()
		# Calculate week number
		week_start_1 = (datetime(2014, 12, 28) + timedelta(hours=day_hours)) # Corrections must be on Monday
		week_start_2 = (script_runtime - timedelta(hours=week_hours))
		shifted_week = ((week_start_2 - week_start_1).days / 7) % full_backup_weeks
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
			self.__set_backup_attr(week, "full", None, "full", None, "yes")
		elif shifted_hour == 0:
			# Daily backup
			self.__set_backup_attr(day, "full", None, "diff", week, "no")
		elif shifted_weekday == 0:
			# Hourly backup in week delimiter day
			self.__set_backup_attr(hour, "diff", week, None, None, "no")
		else:
			# Hourly backup
			self.__set_backup_attr(hour, "diff", day, None, None, "no")
	
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
	def test_shifting_time(self, split_day_by_hour, split_week_by_day, full_backup_weeks):
		print("")
		year = 2015
		month = 1
		for day in range(2, 12):
		#	for hour in range(split_week_by_day - 2, split_week_by_day + 1):
		#for day in range(2, 5):
			for hour in range(0, 23):
				script_runtime = datetime(year, month, day, hour)
				self.__set_shifted_time(script_runtime, split_day_by_hour, split_week_by_day, full_backup_weeks)
				print("runtume: " + script_runtime.isoformat(' ') + ""
						", time: " + str(self.backup_time) + ""
						", db_type: " + str(self.backup_db_type) + ""
						", db_time: " + str(self.backup_db_time) + ""
						", user_type: " + str(self.backup_user_type) + ""
						", user_time: " + str(self.backup_user_time) + "")


# Lists of databases and users
class Lists(object):
	
	def __init__(self, db_root_dirpath, db_default_user, db_ignore, user_root_dirpath, user_ignore, user_path_ignore):
		db_list               = self.__db_list(db_root_dirpath, db_ignore)
		user_list             = self.__user_list(user_root_dirpath, user_ignore)
		user_path_ignore_list = self.__user_path_ignore_list(user_path_ignore)
		db_list_by_users      = self.__db_list_by_users(db_list, db_default_user, user_list)
		self.user_list        = user_list
		self.user_path_ignore_list = user_path_ignore_list
		self.db_list_by_users = db_list_by_users
	
	# Database list
	@staticmethod
	def __db_list(db_root_dirpath, db_ignore):
		db_list = os.listdir(db_root_dirpath)
		# Add files to ignored list
		for db in db_list:
			if os.path.isfile(db_root_dirpath + "/" + db):
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
		
		def __init__(self, backup_dirpath, backup_time, db_temp_dirpath_full, db_temp_dirpath_diff, user_root_dirpath):
			self.__backup_dirpath       = backup_dirpath
			self.__backup_time          = backup_time
			self.__db_temp_dirpath_full = db_temp_dirpath_full
			self.__db_temp_dirpath_diff = db_temp_dirpath_diff
			self.__user_root_dirpath    = user_root_dirpath
		
		# Set needed paths
		def __set(self, user, backup_x, backup_x_type, backup_x_time):
			backup_dirpath       = self.__backup_dirpath
			backup_time          = self.__backup_time
			db_temp_dirpath_full = self.__db_temp_dirpath_full
			db_temp_dirpath_diff = self.__db_temp_dirpath_diff
			# Get dir and file info
			if backup_x_type == "full":
				db_temp_dirpath    = db_temp_dirpath_full
				db_dirpath         = db_temp_dirpath_full + "/" + user
				db_dirpath_full    = None
				user_filename_full = None
				user_filepath_full = None
			else:
				db_temp_dirpath    = db_temp_dirpath_diff
				db_dirpath         = db_temp_dirpath_diff + "/" + user
				db_dirpath_full    = db_temp_dirpath_full + "/" + user
				user_filename_full = user + "-" + backup_x + "-full-" + backup_x_time + ".7z"
				user_filepath_full = backup_dirpath + "/" + user + "/" + user_filename_full
			# Create a place for storing backup files
			backup_dirpath = backup_dirpath + "/" + user
			if not os.path.isdir(backup_dirpath):
				os.makedirs(backup_dirpath, mode=755)
			backup_filename = user + "-" + backup_x + "-" + backup_x_type + "-" + backup_time + ".7z"
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
		def set(self, user, backup_x, backup_x_type, backup_x_time):
			self.__set(user, backup_x, backup_x_type, backup_x_time)
	
	def __init__(self, script_runtime, script_dirpath, debug_mode, backup_dirpath, backup_dirpath_tmp, backup_time,
				db_temp_dirpath_full, db_temp_dirpath_diff, db_binlog_dirpath, db_binlog_rm_hours,
				user_root_dirpath, password_db, password_7z):
		# Log execution to file
		if not debug_mode:
			with open(backup_dirpath + "/backup.log", "a") as log:
				log.write("\n" + script_runtime.replace(microsecond=0).isoformat(' '))
		# Set attributes
		self.__script_dirpath       = script_dirpath
		self.__debug_mode           = debug_mode
		self.__backup_dirpath       = backup_dirpath
		self.__backup_dirpath_tmp   = backup_dirpath_tmp
		self.__backup_time          = backup_time
		self.__db_temp_dirpath_full = db_temp_dirpath_full
		self.__db_temp_dirpath_diff = db_temp_dirpath_diff
		self.__db_binlog_dirpath    = db_binlog_dirpath
		self.__db_binlog_rm_hours   = db_binlog_rm_hours
		self.__user_root_dirpath    = user_root_dirpath
		self.__params_mysql         = password_db
		self.__params_mysqldump     = password_db + " --skip-extended-insert --single-transaction --routines --triggers --events --no-tablespaces"
		self.__params_mysqloptimize = password_db + " --silent"
		self.__params_7z            = password_7z + " -bd -mhe=on -mx5 -mf=off -ms=e -mmt=off"
	
	# Prepare commands for backup of databases
	def db_cmds(self, backup_db_type, backup_db_time, db_list_by_users, db_default_user, db_ignore_users, db_optimize):
		if backup_db_type is None:
			return
		# Separate backup for every user
		db_all_cmds = []
		path = self.Path(self.__backup_dirpath, self.__backup_time, self.__db_temp_dirpath_full, self.__db_temp_dirpath_diff, self.__user_root_dirpath)
		for user in db_list_by_users:
			db_cmds = []
			db_cmds_7z = []
			db_cmds_gd = []
			path.set(user, "sql", backup_db_type, backup_db_time)
			# Export all databases from specific user to files
			export = False
			db_cmds.append("\nif [ \"$(ls -A " + path.db_dirpath + ")\" ]; then rm " + path.db_dirpath + "/*; fi")
			if user == db_default_user:
				if self.__db_binlog_dirpath != "":
					# Backup binary logs
					if backup_db_type == "full":
						db_all_cmds.insert(0, self.__mysql_flush_logs())
						db_all_cmds.insert(1, self.__mysql_purge_logs())
					if backup_db_type == "diff":
						db_all_cmds.append(self.__mysql_backup_binlog(self.__db_binlog_dirpath, path.backup_dirpath, path.backup_filename))
				# Backup database permissions
				db_all_cmds.append(self.__mysqldump_permissions(path.db_dirpath, db_ignore_users, False) + ""
						"" + self.__7z_add_std("mysql.sql", path.backup_dirpath, path.backup_filename))
			for db in db_list_by_users[user]:
				# Full backup with binary logs
				if backup_db_type == "full" and self.__db_binlog_dirpath != "":
					export = True
					db_cmds_7z.append(self.__mysqldump_full(db, path.db_dirpath, False) + ""
							"" + self.__7z_add_std(db + ".sql", path.backup_dirpath, path.backup_filename))
				# Full backup
				if backup_db_type == "full" and self.__db_binlog_dirpath == "":
					export = True
					db_cmds.append(self.__mysqldump_full(db, path.db_dirpath, True))
				# Diff backup
				if backup_db_type == "diff" and self.__db_binlog_dirpath == "":
					export = True
					db_cmds_7z.append(self.__mysqldump_diff(db, path.db_dirpath, path.db_dirpath_full, False) + ""
							"" + self.__7z_add_std(db + ".sql.diff", path.backup_dirpath, path.backup_filename))
			# Compress databases
			db_cmds.append(self.__7z_add(path.db_temp_dirpath, user, None, path.backup_dirpath, path.backup_filename))
			if len(db_cmds_7z) > 0:
				db_cmds.extend(db_cmds_7z)
			# Upload to Google Drive
			gd_file = path.backup_dirpath + "/" + path.backup_filename
			if os.path.isfile(gd_file):
				db_cmds_gd.append("python \"" + self.__script_dirpath + "googledrive.py\""
						" '" + gd_file + "' 'Diff for " + str(backup_db_time).upper() + "'")
			# Add to all commands
			if (export == True):
				db_all_cmds.extend(db_cmds)
		# Database optimizations
		if db_optimize == "yes":
			db_all_cmds.append(self.__mysqloptimize())
		return db_all_cmds, db_cmds_gd
	
	# Prepare commands for backup of user files
	def user_cmds(self, backup_user_type, backup_user_time, user_list, user_path_ignore_list):
		user_cmds = []
		user_cmds_gd = []
		if backup_user_type is None:
			return
		# Separate backup for every user
		path = self.Path(self.__backup_dirpath, self.__backup_time, self.__db_temp_dirpath_full, self.__db_temp_dirpath_diff, self.__user_root_dirpath)
		for user in user_list:
			path.set(user, "user", backup_user_type, backup_user_time)
			user_path_ignore = user_path_ignore_list.get(user)
			# Full backup
			if backup_user_type == "full":
				user_cmds.append(self.__7z_add(self.__user_root_dirpath, user, user_path_ignore, path.backup_dirpath, path.backup_filename))
			# Diff backup
			if backup_user_type == "diff":
				user_cmds.append(self.__7z_update(self.__user_root_dirpath, user, user_path_ignore, path.backup_dirpath, path.backup_filename, path.user_filepath_full))
				# Upload to Google Drive
				gd_file = path.backup_dirpath + "/" + path.backup_filename
				if os.path.isfile(gd_file):
					user_cmds_gd.append("python \"" + self.__script_dirpath + "googledrive.py\""
							" '" + gd_file + "' 'Diff for " + str(backup_user_time).upper() + "'")
		return user_cmds, user_cmds_gd
	
	# Execute backup commands
	def execute(self, backup_dirpath, backup_verbose, backup_x, cmds):
		if cmds is None:
			return
		cmds = filter(None, cmds)
		if len(cmds) == 0:
			return
		cmd = "\n".join(cmds)
		if not self.__debug_mode:
			start = datetime.now()
			subprocess.call(cmd, shell=True)
			stop = datetime.now()
			with open(backup_dirpath + "/backup.log", "a") as log:
				log.write(", " + backup_x + " = " + str(round((stop - start).total_seconds(), 1)) + "s")
				if backup_verbose == "1":
					log.write(", commands:\n" + cmd)
		else:
			print(cmd)
	
	def __mysqldump_permissions(self, db_dirpath, db_ignore_users, to_file):
		return("{ mysqldump " + self.__params_mysqldump + " --no-create-info --databases mysql --tables db user;"
				" echo \"\\nFLUSH PRIVILEGES;\"; }"
				" | sed \"17s/^$/\\nUSE \`mysql\`;\\n/\""
				" | grep --invert-match --extended-regexp \"^INSERT INTO \`user\` VALUES \('(\w|\-|\.)*','(" + db_ignore_users + ")',\""
				"" + (" > \"" + db_dirpath + "/mysql.sql\"" if to_file else ""))
	
	def __mysql_flush_logs(self):
		return("echo \"FLUSH LOGS;\" | mysql " + self.__params_mysql)
	
	def __mysql_purge_logs(self):
		if self.__db_binlog_rm_hours.isdigit() and int(self.__db_binlog_rm_hours) > 0:
			return("echo \"PURGE BINARY LOGS BEFORE '" + (datetime.now() - timedelta(hours=int(self.__db_binlog_rm_hours))).isoformat() + "';\" | mysql " + self.__params_mysql)
		else:
			return("")
	
	def __mysqldump_full(self, db, db_dirpath, to_file):
		return("{ echo \"SET SESSION UNIQUE_CHECKS = 0;\\nSET SESSION FOREIGN_KEY_CHECKS = 0;\\n\\n\"; "
				"mysqldump " + self.__params_mysqldump + " --databases " + db + "; }"
				"" + (" > \"" + db_dirpath + "/" + db + ".sql.diff\"" if to_file else ""))
	
	def __mysqldump_diff(self, db, db_dirpath, db_dirpath_full, to_file):
		if not os.path.isfile(db_dirpath_full + "/" + db + ".sql"):
			return
		return("mysqldump " + self.__params_mysqldump + " --databases " + db + ""
				" | diff \"" + db_dirpath_full + "/" + db + ".sql\" -"
				"" + (" > \"" + db_dirpath + "/" + db + ".sql.diff\"" if to_file else ""))
	
	def __mysql_backup_binlog(self, db_binlog_dirpath, backup_dirpath, backup_filename):
		filepath_7z = backup_dirpath + "/" + backup_filename
		return("\nlogs=`echo \"SHOW BINARY LOGS;\" | mysql " + self.__params_mysql + " | tail -n1 | awk '{print $1}'`\n"
				"" + self.__mysql_flush_logs() + "\n"
				"for log in $logs; do\n"
				"    7z a " + self.__params_7z + " -w\"" + self.__backup_dirpath_tmp + "\""
				" \"" + filepath_7z + "\" \"" + db_binlog_dirpath + "/$log\""
				" > /dev/null\n"
				"done" + "\n")
	
	def __mysqloptimize(self):
		return("mysqloptimize " + self.__params_mysqloptimize + " --all-databases"
				" > \"" + self.__backup_dirpath + "/mysqloptimize.log\"")
	
	def __7z_add(self, source_dirpath, source_name, extra_params, backup_dirpath, backup_filename):
    		if not os.path.isdir(backup_dirpath):
			os.makedirs(backup_dirpath, mode=755)
		filepath_7z = backup_dirpath + "/" + backup_filename
		return("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
				"7z a " + self.__params_7z + " -w\"" + self.__backup_dirpath_tmp + "\""
				"" + (extra_params if extra_params != None else "") + ""
				" \"" + filepath_7z + "\" \"" + source_dirpath + "/" + source_name + "\""
				" > /dev/null")
	
	def __7z_add_std(self, source_name, backup_dirpath, backup_filename):
		filepath_7z = backup_dirpath + "/" + backup_filename
		return(" | 7z a " + self.__params_7z + " -si" + source_name + ""
				" \"" + filepath_7z + "\""
				" > /dev/null")

	def __7z_update(self, source_dirpath, source_name, extra_params, backup_dirpath, backup_filename, user_filepath_full):
		if not os.path.isfile(user_filepath_full):
			return("# Missing file for 7z update: " + user_filepath_full)
		filepath_7z = backup_dirpath + "/" + backup_filename
		# http://a32.me/2010/08/7zip-differential-backup-linux-windows/
		return("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
				"7z u " + self.__params_7z + " -w\"" + self.__backup_dirpath_tmp + "\""
				"" + (extra_params if extra_params != None else "") + ""
				" \"" + user_filepath_full + "\" \"" + source_dirpath + "/" + source_name + "\""
				" -u- -up0q3r2x2y2z0w2\!\"" + filepath_7z + "\""
				" > /dev/null")


# Execute backup for specific time
def execute_at_runtime(script_runtime, debug_mode):
	# Config data
	config = Config()
	# Type of backup and backup file name
	info = BackupInfo(script_runtime, config.split_day_by_hour, config.split_week_by_day,
			config.full_backup_weeks)
	# List of databases and user dirs to backup
	lists = Lists(config.db_root_dirpath, config.db_default_user, config.db_ignore,
			config.user_root_dirpath, config.user_ignore, config.user_path_ignore)
	# Prepare database and user dirs commands for archiving
	cmds = BackupCommands(script_runtime, config.script_dirpath, debug_mode, config.backup_dirpath, config.backup_dirpath_tmp, info.backup_time,
			config.db_temp_dirpath_full, config.db_temp_dirpath_diff, config.db_binlog_dirpath, config.db_binlog_rm_hours,
			config.user_root_dirpath, config.password_db, config.password_7z)
	db_cmds = cmds.db_cmds(info.backup_db_type, info.backup_db_time,
			lists.db_list_by_users, config.db_default_user, config.db_ignore_users, info.db_optimize)
	(db_cmds_core, db_cmds_gd) = (None, None)
	if db_cmds is not None:
		(db_cmds_core, db_cmds_gd) = db_cmds
	user_cmds = cmds.user_cmds(info.backup_user_type, info.backup_user_time,
			lists.user_list, lists.user_path_ignore_list)
	(user_cmds_core, user_cmds_gd) = (None, None)
	if user_cmds is not None:
		(user_cmds_core, user_cmds_gd) = user_cmds
	# Execute backup commands
	cmds.execute(config.backup_dirpath, config.backup_verbose, "db", db_cmds_core)
	cmds.execute(config.backup_dirpath, config.backup_verbose, "user", user_cmds_core)
	if config.gd_upload_enable == "1":
		cmds.execute(config.backup_dirpath, config.backup_verbose, "db_gd", db_cmds_gd)
		cmds.execute(config.backup_dirpath, config.backup_verbose, "user_gd", user_cmds_gd)


# Main
if len(sys.argv) == 1:
	execute_at_runtime(datetime.now(), False)
else:
	# Debug
	print("# List of backup.py commands")
	script_runtime = datetime(2015, 1, 3, 4)
	print("\n\n# db = full, user = full, " + script_runtime.isoformat(' '))
	execute_at_runtime(script_runtime, True)
	script_runtime = datetime(2015, 1, 4, 4)
	print("\n\n# db = full, user = diff, " + script_runtime.isoformat(' '))
	execute_at_runtime(script_runtime, True)
	script_runtime = datetime(2015, 1, 4, 5)
	print("\n\n# db = diff, user = none, " + script_runtime.isoformat(' '))
	execute_at_runtime(script_runtime, True)
	# Test shifting time
	config = Config()
	info = BackupInfo(script_runtime, config.split_day_by_hour, config.split_week_by_day,
			config.full_backup_weeks)
	info.test_shifting_time(config.split_day_by_hour, config.split_week_by_day, config.full_backup_weeks)


# TODO:
#	Generate a file with chmod and chown commands (7z doesn't store this info)
#	Generate a file with restore commands (mysql imports, 7z extracts)
#	Join methods for some mysqldump/7z commands
#	Remove passwords from 7z calls: "7z a -p* ".
