#!/usr/bin/python
# Copyright Eyga.net
# For python 3.x

import sys
from datetime import datetime, timedelta

buffer_bytes_limit = 1024 * 1024 * 16 # 16 MB

insert_string = b"INSERT INTO "
len_insert_string = len(insert_string)
values_string = b" VALUES "
len_values_string = len(values_string)

buffer_bytes_count = 0
value_index = -1

start = datetime.now()

# Read from input
for line in sys.stdin.buffer:
	len_line = len(line)
	mv_line = memoryview(line)
	is_insert_line = (mv_line[0:len_insert_string] == insert_string)

	# First insert line
	if (value_index == -1 and is_insert_line == True):
		value_index = line.find(values_string) + len_values_string
		sys.stdout.buffer.flush()

	# For every insert line
	if (value_index >= 0 and is_insert_line == True):
		new_line = mv_line[value_index:-2]
		len_new_line = len_line - value_index - 2
		if (buffer_bytes_count == 0):
			# Write to new INSERT
			sys.stdout.buffer.write(mv_line[0:-2])
			buffer_bytes_count = len_line - 2
		elif (buffer_bytes_count + len_new_line + 3 >= buffer_bytes_limit):
			# Close last INSERT
			sys.stdout.buffer.write(b";\n")
			sys.stdout.buffer.flush()
			sys.stdout.buffer.write(mv_line[0:-2])
			buffer_bytes_count = len_line - 2
		else:
			# Write to existing INSERT
			sys.stdout.buffer.write(b",\n")
			sys.stdout.buffer.write(new_line)
			buffer_bytes_count += len_new_line + 3

	# Normal line
	elif (value_index == -1 and is_insert_line == False):
		sys.stdout.buffer.write(line)

	# No more inserts
	elif (value_index >= 0 and is_insert_line == False):
		# Close last INSERT
		sys.stdout.buffer.write(b";\n")
		sys.stdout.buffer.flush()
		sys.stdout.buffer.write(line)
		value_index = -1
		buffer_bytes_count = 0

stop = datetime.now()
# print("-- Duration of mysql-insert-fix: " + str(round((stop - start).total_seconds(), 1)) + "s")
