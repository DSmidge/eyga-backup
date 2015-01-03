#!/usr/bin/python

# For python 2.7

# Import modules
import ConfigParser
from datetime import datetime, timedelta
import os
import subprocess
import sys


# Configuration
class Config(object):
	script_dirpath = None
	
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
		config = ConfigParser.RawConfigParser()
		config.read(config_filepath)
		config_section            = "settings"
		self.backup_dirpath       = config.get(config_section, "backup_dirpath")
		self.db_root_dirpath      = config.get(config_section, "db_root_dirpath")
		self.db_temp_dirpath_full = config.get(config_section, "db_temp_dirpath_full")
		self.db_temp_dirpath_diff = config.get(config_section, "db_temp_dirpath_diff")
		self.db_default_user      = config.get(config_section, "db_default_user")
		self.db_ignore            = config.get(config_section, "db_ignore").split("|")
		self.db_ignore_users      = config.get(config_section, "db_ignore_users")
		self.user_root_dirpath    = config.get(config_section, "user_root_dirpath")
		self.user_ignore          = config.get(config_section, "user_ignore").split("|")
		self.split_week_by_day    = config.getint(config_section, "split_week_by_day")
		self.split_day_by_hour    = config.getint(config_section, "split_day_by_hour")
		self.full_backup_weeks    = config.getint(config_section, "full_backup_weeks")
	
	# Read passwords form config file
	def __passwords(self, config_filename):
		config_filepath = self.__get_config_filepath(config_filename)
		config = ConfigParser.RawConfigParser()
		config.read(config_filepath)
		config_section   = "passwords"
		self.password_db = config.get(config_section, "password_db")
		self.password_7z = config.get(config_section, "password_7z")
	
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


# Define period start times and backup types
class BackupInfo(object):
	
	# Shift time to hour of full backup
	def __set_shifted_time(self):
		# Fix hour
		day_hours = self.__split_day_by_hour
		hour = (self.__script_runtime - timedelta(hours=day_hours)).hour
		# Fix weekday
		week_hours = 24 * self.__split_week_by_day + self.__split_day_by_hour
		weekday = (self.__script_runtime - timedelta(hours=week_hours)).weekday()
		# Calculate week number
		week_start_1 = (self.__week_cnt_start - timedelta(days=self.__week_cnt_start.weekday() + self.__split_week_by_day))
		week_start_2 = (self.__script_runtime - timedelta(days=self.__script_runtime.weekday() + self.__split_week_by_day))
		week = ((week_start_2 - week_start_1).days / 7) % self.__full_backup_weeks
		# Set attributes
		self.__shifted_hour    = hour
		self.__shifted_weekday = weekday
		self.__shifted_week    = week
	
	# Set backup attributes
	def __set_backup_attr(self, backup_time, backup_db_type, backup_db_time,
				backup_user_type, backup_user_time, db_optimize):
		self.backup_time      = backup_time
		self.backup_db_type   = backup_db_type
		self.backup_db_time   = backup_db_time
		self.backup_user_type = backup_user_type
		self.backup_user_time = backup_user_time
		self.db_optimize      = db_optimize
	
	# Define type of backup (full or diff)
	def __set_backup_info(self):
		hour = "h" + ("0" + str(self.__shifted_hour))[-2:]
		day = "d" + str(self.__shifted_weekday)
		week = "w" + str(self.__shifted_week)
		# Set backup type and time attributes
		if self.__shifted_weekday == 0 and self.__shifted_hour == 0:
			# Weekly backup (for last X weeks)
			self.__set_backup_attr(week, "full", None, "full", None, "yes")
		elif self.__shifted_hour == 0:
			# Daily backup
			self.__set_backup_attr(day, "full", None, "diff", week, "no")
		elif self.__shifted_weekday == 0:
			# Hourly backup in week delimiter day
			self.__set_backup_attr(hour, "diff", week, None, None, "no")
		else:
			# Hourly backup
			self.__set_backup_attr(hour, "diff", day, None, None, "no")
	
	def __init__(self, script_runtime, split_day_by_hour, split_week_by_day, full_backup_weeks):
		if split_day_by_hour > 23: split_day_by_hour = 0
		if split_week_by_day > 06: split_week_by_day = 0
		self.__script_runtime    = script_runtime
		self.__week_cnt_start    = datetime(2014, 12, 29) # On Monday
		self.__split_day_by_hour = split_day_by_hour
		self.__split_week_by_day = split_week_by_day
		self.__full_backup_weeks = full_backup_weeks
		self.__set_shifted_time()
		self.__set_backup_info()


# Lists of databases and users
class Lists(object):
	
	# Database list
	def __db_list(self, db_root_dirpath, db_ignore):
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
	def __user_list(self, user_root_dirpath, user_ignore):
		user_list = os.listdir(user_root_dirpath)
		# Remove ignored
		for user in user_ignore:
			if user in user_list:
				user_list.remove(user)
		# Sort and return
		user_list.sort()
		return user_list
	
	# Databases list by users
	def __db_list_by_users(self, db_root_dirpath, db_list, db_default_user, user_list):
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
	
	def __init__(self, db_root_dirpath, db_default_user, db_ignore, user_root_dirpath, user_ignore):
		db_list          = self.__db_list(db_root_dirpath, db_ignore)
		user_list        = self.__user_list(user_root_dirpath, user_ignore)
		db_list_by_users = self.__db_list_by_users(db_root_dirpath, db_list, db_default_user, user_list)
		self.user_list        = user_list
		self.db_list_by_users = db_list_by_users


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
		def set(self, user, backup_x, backup_x_type, backup_x_time):
			backup_dirpath       = self.__backup_dirpath
			backup_time          = self.__backup_time
			db_temp_dirpath_full = self.__db_temp_dirpath_full
			db_temp_dirpath_diff = self.__db_temp_dirpath_diff
			# Create a place for storing backup files
			backup_dirpath = backup_dirpath + "/" + user
			if not os.path.isdir(backup_dirpath):
				os.makedirs(backup_dirpath, mode=0755)
			backup_filename = user + "-" + backup_x + "-" + backup_x_type + "-" + backup_time + ".7z"
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
				user_filepath_full = backup_dirpath + "/" + user_filename_full
			# Create a place for storing SQL files
			if backup_x == "sql" and not os.path.isdir(db_dirpath):
				os.makedirs(db_dirpath, mode=0755)
			# Set attributes
			self.backup_dirpath     = backup_dirpath
			self.backup_filename    = backup_filename
			self.db_temp_dirpath    = db_temp_dirpath
			self.db_dirpath         = db_dirpath
			self.db_dirpath_full    = db_dirpath_full
			self.user_filename_full = user_filename_full
			self.user_filepath_full = user_filepath_full
	
	def __init__(self, script_runtime, script_dirpath, debug_mode, backup_dirpath, backup_time,
				db_temp_dirpath_full, db_temp_dirpath_diff, user_root_dirpath,
				password_db, password_7z):
		# Log execution to file
		with open(backup_dirpath + "/backup.log", "a") as log:
			log.write("\n" + script_runtime.replace(microsecond=0).isoformat(' '))
		# Set attributes
		self.__script_dirpath       = script_dirpath
		self.__debug_mode           = debug_mode
		self.__backup_dirpath       = backup_dirpath
		self.__backup_time          = backup_time
		self.__db_temp_dirpath_full = db_temp_dirpath_full
		self.__db_temp_dirpath_diff = db_temp_dirpath_diff
		self.__user_root_dirpath    = user_root_dirpath
		self.__params_mysqldump     = password_db + " --compress --skip-extended-insert --single-transaction --routines --triggers"
		self.__params_mysqloptimize = password_db + " --compress --silent"
		self.__params_7z            = password_7z + " -mx5 -mhe=on -s=e -f=off -mt=off"
	
	def __mysqldump_permissions(self, db_dirpath, db_ignore_users):
		return ("{ mysqldump " + self.__params_mysqldump + " --no-create-info --databases mysql --tables db user;"
				" echo \"\\nFLUSH PRIVILEGES;\"; }"
				" | sed \"17s/^$/\\nUSE \`mysql\`;\\n/\""
				" | grep --invert-match --extended-regexp \"^INSERT INTO \`user\` VALUES \('(\w|\-|\.)*','(" + db_ignore_users + ")',\""
				" > \"" + db_dirpath + "/mysql.sql\"")
	
	def __mysqldump_full(self, db, db_dirpath):
		return ("mysqldump " + self.__params_mysqldump + " --databases " + db + ""
				" > \"" + db_dirpath + "/" + db + ".sql\"")
	
	def __mysqldump_diff(self, db, db_dirpath, db_dirpath_full):
		if not os.path.isfile(db_dirpath_full + "/" + db + ".sql"):
			return
		return ("mysqldump " + self.__params_mysqldump + " --databases " + db + ""
				" | diff \"" + db_dirpath_full + "/" + db + ".sql\" -"
				" > \"" + db_dirpath + "/" + db + ".sql.diff\"")
	
	def __mysqloptimize(self):
		return ("mysqloptimize " + self.__params_mysqloptimize + " --all-databases"
				" > \"" + self.__backup_dirpath + "/mysqloptimize.log\"")
	
	def __7z_add(self, source_dirpath, source_name, backup_dirpath, backup_filename):
		if not os.path.isdir(backup_dirpath):
			os.makedirs(backup_dirpath, mode=0755)
		filepath_7z = backup_dirpath + "/" + backup_filename
		return ("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
				"7z a " + self.__params_7z + " -w\"" + source_dirpath + "\""
				" \"" + filepath_7z + "\" \"" + source_dirpath + "/" + source_name + "\""
				" > /dev/null")
	
	def __7z_update(self, source_dirpath, source_name, backup_dirpath, backup_filename, user_dirpath_full):
		if not os.path.isfile(user_dirpath_full):
			return
		filepath_7z = backup_dirpath + "/" + backup_filename
		# http://a32.me/2010/08/7zip-differential-backup-linux-windows/
		return ("if [ -f \"" + filepath_7z + "\" ]; then rm \"" + filepath_7z + "\"; fi\n"
				"7z u " + self.__params_7z + " -w\"" + source_dirpath + "\""
				" \"" + filepath_7z + "\" \"" + source_dirpath + "/" + source_name + "\""
				" -u- -up0q3r2x2y2z0w2\!\"" + user_dirpath_full + "\""
				" > /dev/null")
	
	# Prepre commands for backup of databases
	def db_cmds(self, backup_db_type, backup_db_time, db_list_by_users, db_default_user, db_ignore_users, db_optimize):
		db_cmds = []
		if backup_db_type is None:
			return
		# Seperate backup for every user
		path = self.Path(self.__backup_dirpath, self.__backup_time, self.__db_temp_dirpath_full, self.__db_temp_dirpath_diff, self.__user_root_dirpath)
		for user in db_list_by_users:
			path.set(user, "sql", backup_db_type, backup_db_time)
			# Export all databases from specific user to files
			if backup_db_type == "full":
				db_cmds.append("rm \"" + path.db_dirpath + "/*\"")
			if user == db_default_user:
				# Backup database permissions
				db_cmds.append(self.__mysqldump_permissions(path.db_dirpath, db_ignore_users))
			for db in db_list_by_users[user]:
				# Full backup
				if backup_db_type == "full":
					db_cmds.append(self.__mysqldump_full(db, path.db_dirpath))
				# Diff backup
				if backup_db_type == "diff":
					db_cmds.append(self.__mysqldump_diff(db, path.db_dirpath, path.db_dirpath_full))
			# Compress databases
			db_cmds.append(self.__7z_add(path.db_temp_dirpath, user, path.backup_dirpath, path.backup_filename))
			# Upload to Google Drive
			db_cmds.append("python \"" + self.__script_dirpath + "googledrive.py\""
					" '" + path.backup_dirpath + "/" + path.backup_filename + "' '" + path.backup_filename + "'"
					" 'Diff for " + str(backup_db_time).upper() + "'")
		# Database optimizations
		if db_optimize == "yes":
			db_cmds.append(self.__mysqloptimize())
		return db_cmds
	
	# Prepare commands for backup of user files
	def user_cmds(self, backup_user_type, backup_user_time, user_list):
		user_cmds = []
		if backup_user_type is None:
			return
		# Seperate backup for every user
		path = self.Path(self.__backup_dirpath, self.__backup_time, self.__db_temp_dirpath_full, self.__db_temp_dirpath_diff, self.__user_root_dirpath)
		for user in user_list:
			path.set(user, "user", backup_user_type, backup_user_time)
			# Full backup
			if backup_user_type == "full":
				user_cmds.append(self.__7z_add(self.__user_root_dirpath, user, path.backup_dirpath, path.backup_filename))
			# Diff backup
			if backup_user_type == "diff":
				user_cmds.append(self.__7z_update(self.__user_root_dirpath, user, path.backup_dirpath, path.backup_filename, path.user_filepath_full))
				# Upload to Google Drive
				user_cmds.append("python \"" + self.__script_dirpath + "googledrive.py\""
						" '" + path.backup_dirpath + "/" + path.backup_filename + "' '" + path.backup_filename + "'"
						" 'Diff for " + str(backup_user_time).upper() + "'")
		return user_cmds
	
	# Execute backup commands
	def execute(self, backup_dirpath, backup_x, cmds):
		if cmds is not None:
			cmds = filter(None, cmds)
			cmd = "\n".join(cmds)
			if not self.__debug_mode:
				start = datetime.now()
				subprocess.call(cmd, shell=True);
				stop = datetime.now()
				with open(backup_dirpath + "/backup.log", "a") as log:
					log.write(", " + backup_x + " = " + str(round(stop - start, 1)) + "s")
			else:
				print(cmd)

# Execute backup for specific time
def execute_at_runtime(script_runtime, debug_mode):
	os.nice(40)
	# Config data
	config = Config()
	# Type of backup and backup file name
	info = BackupInfo(script_runtime, config.split_day_by_hour, config.split_week_by_day,
			config.full_backup_weeks)
	# List of databases and user dirs to backup
	lists = Lists(config.db_root_dirpath, config.db_default_user, config.db_ignore,
			config.user_root_dirpath, config.user_ignore)
	# Prepare database and user dirs commands for archieving
	cmds = BackupCommands(script_runtime, config.script_dirpath, debug_mode, config.backup_dirpath, info.backup_time,
			config.db_temp_dirpath_full, config.db_temp_dirpath_diff, config.user_root_dirpath,
			config.password_db, config.password_7z)
	db_cmds = cmds.db_cmds(info.backup_db_type, info.backup_db_time,
			lists.db_list_by_users, config.db_default_user, config.db_ignore_users, info.db_optimize)
	user_cmds = cmds.user_cmds(info.backup_user_type, info.backup_user_time,
			lists.user_list)
	cmds.execute(config.backup_dirpath, "sql", db_cmds)
	cmds.execute(config.backup_dirpath, "user", user_cmds)

# Main
if len(sys.argv) >= 2:
	print "# List of backup.py commands"
	print "\n\n# db = full, user = full"
	execute_at_runtime(datetime(2014, 12, 27, 4), True)
	print "\n\n# db = full, user = diff"
	execute_at_runtime(datetime(2014, 12, 28, 4), True)
	print "\n\n# db = diff, user = none"
	execute_at_runtime(datetime(2014, 12, 28, 5), True)
else:
	execute_at_runtime(datetime.now(), False)

# TODO:
#	Generate a file with chmod and chown commands (7z doesn't store this info)
#	Generate a file with restore commands (mysql imports, 7z extracts)
#	Detect if no full backup exists for databases and user files
#	Join methods for some mysqldump/7z commands
#	Performace test: store full SQL files with gzip/7z and make diff on their stream (7z -si and -so switches)
#	Add full SQL files directly in 7z file (will ignore solid archieves; maby with -si, -so switches?)
