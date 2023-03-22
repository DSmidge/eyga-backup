import sys

buffer_bytes_limit = 1024 * 1024 * 16 # 16 MB

insert_string = b"INSERT INTO "
values_string = b" VALUES "

buffer_bytes_count = 0
value_index = -1

# Read from input
for line in sys.stdin.buffer:
	is_insert_line = line.startswith(insert_string)

	# First insert line
	if (value_index == -1 and is_insert_line == True):
		value_index = line.find(values_string) + len(values_string)

	# For every insert line
	if (value_index >= 0 and is_insert_line == True):
		new_line = line.rstrip()[value_index:-1]
		if (buffer_bytes_count == 0 or buffer_bytes_count + len(new_line) >= buffer_bytes_limit):
			# Write to new INSERT
			line = line.rstrip()[0:-1]
			if (buffer_bytes_count > 0):
				# Close last INSERT
				line = b";\n" + line
			buffer_bytes_count = 0
		else:
			# Write to existing INSERT
			line = b",\n" + new_line
		buffer_bytes_count += len(line)

	# No more inserts
	if (value_index >= 0 and is_insert_line == False):
		# Close last INSERT
		line = b";\n" + line
		value_index = -1
		buffer_bytes_count = 0

	# Write to output
	sys.stdout.buffer.write(line)
