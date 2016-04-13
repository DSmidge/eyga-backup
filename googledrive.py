#!/usr/bin/python
# Copyright Eyga.net
# For python 2.7
# Run it manually first to set the credentials

# Import modules
import ConfigParser
import os.path
import sys
# Used by Google
import apiclient
import httplib2
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage


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
		self.__google_credentials("google_credentials.cfg")
	
	# Get the path of the configuration file
	def __get_config_filepath(self, config_filename):
		config_filepath = self.script_dirpath + config_filename
		if not os.path.isfile(config_filepath):
			print("Configuration file '" + config_filepath + "' is missing.")
			sys.exit(1)
		return config_filepath
	
	def __google_credentials(self, config_filename):
		config_filepath = self.__get_config_filepath(config_filename)
		config = ConfigParser.RawConfigParser()
		config.read(config_filepath)
		config_section               = "google_credentials"
		self.google_client_id        = config.get(config_section, "google_client_id")
		self.google_client_secret    = config.get(config_section, "google_client_secret")
		self.google_credentials_json = self.script_dirpath + "google_credentials.json"


# For uploading to Google Drive
class GoogleDrive(object):
	credentials = None
	
	def __init__(self, client_id, client_secret, credentials_file):
			# Check https://developers.google.com/drive/scopes for all available scopes
			oauth_scope = 'https://www.googleapis.com/auth/drive'
			# Redirect URI for installed apps
			redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
			# Run through the OAuth flow and retrieve credentials
			flow = OAuth2WebServerFlow(client_id, client_secret, oauth_scope, redirect_uri=redirect_uri)
			flow.params['access_type'] = 'offline'
			# Get/set credentials
			storage = Storage(credentials_file)
			if os.path.isfile(credentials_file):
				self.credentials = storage.get()
			else:
				authorize_url = flow.step1_get_authorize_url()
				print 'Go to the following link in your browser: ' + authorize_url
				code = raw_input('Enter verification code: ').strip()
				self.credentials = flow.step2_exchange(code)
				storage.put(self.credentials)

	def upload_file(self, file_path, file_name, file_desc):
		# Create a Http object and authorize it with our credentials
		http = httplib2.Http()
		http = self.credentials.authorize(http)
		try:
			drive_service = apiclient.discovery.build('drive', 'v2', http=http)
		except e:
			print("Error building Google Drive service object: {0}".format(e.message))
		# File contents
		media_body = apiclient.http.MediaFileUpload(file_path, mimetype='application/octet-stream', resumable=True)
		# Does the file exist?
		file_id = None
		param = {
			'q': "title = '" + file_name + "'"
		}
		files = drive_service.files().list(**param).execute()
		if len(files['items']) > 0:
			file_id = files['items'][0]['id']
		# Upload new contents
		if file_id is not None:
			# Update the file
			body = {
				'description': file_desc
			}
			try:
				drive_service.files().update(
					fileId=file_id,
					body=body,
					newRevision=False,
					media_body=media_body).execute()
			except e:
				print("Error occurred when updating a file on Google Drive: {0}".format(e.message))
		else:
			# Insert the file
			body = {
				'title': file_name,
				'description': file_desc
			}
			try:
				drive_service.files().insert(
					body=body,
					media_body=media_body).execute()
			except e:
				print("Error occurred when inserting a file to Google Drive: {0}".format(e.message))


# Main
if len(sys.argv) == 3:
	config = Config()
	filepath = sys.argv[1]
	filename = os.path.basename(filepath)
	filedesc = sys.argv[2]
	if os.path.isfile(filepath):
		drive = GoogleDrive(config.google_client_id, config.google_client_secret, config.google_credentials_json)
		drive.upload_file(filepath, filename, filedesc)
else:
	print("Expected 'filepath' and 'filedesc' for parameters.")
	sys.exit(1)


# TODO:
#	Store backup files in specific folder
