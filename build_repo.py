#!/usr/bin/python
# -*- coding: utf-8 -*-

'''*
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*'''

import re
import os
import sys
import json
import shutil
import requests
import inspect
import zipfile
import hashlib
import ConfigParser
import subprocess
import xml.etree.ElementTree as ET
from optparse import OptionParser
from time import strftime

parser = OptionParser()
parser.add_option("-a", "--addon", dest="AddonID", help="Specify a single Addon ID")
parser.add_option("-b", "--build", dest="BuildID", help="Build a specific Addon ID")
parser.add_option("-l", "--list", action="store_true", dest="LIST", help="List Addons", default=False)
parser.add_option("-i", action="store_true", dest="Interactive", help="Full Interative mode", default=True)
(options, args) = parser.parse_args()

CONFIG_DIR = 'config'
CONFIG_FILE = 'config/config.txt'
class COLORS:
	GRAY 	= '\033[1;30;40m'
	RED 	= '\033[1;31;40m'
	GREEN 	= '\033[1;32;40m'	
	YELLOW 	= '\033[1;33;40m'
	BLUE 	= '\033[1;34;40m'
	MAGENTA = '\033[1;35;40m'
	CYAN 	= '\033[1;36;40m'
	WHITE 	= '\033[1;37;40m'
	END 	= '\033[0m'

# Load configuration from config/config.txt
config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

addon_list = [ a.strip() for a in config.get('addons', 'addons_list').split(",")]
try:
	user_map = {}
	temp = config.get('addons', 'user_map').split(",")
	for t in temp:
		t = t.split(":")
		user_map[t[0].strip()] = t[1].strip()
except:
	user_map = {}

try:
	host_map = {}
	temp = config.get('addons', 'host_map').split(",")
	for t in temp:
		t = t.split(":")
		host_map[t[0].strip()] = t[1].strip()
except:
	host_map = {}

class BuildException(Exception):
	pass

'''*
Check the repo is uptodate before we proceed.

*'''

status = subprocess.check_output(['./check_repo', '']).strip()
if status != "Up-to-date":
	print "Repository is out of sync with remote"
	if status == "Need to push":
		print "Local is ahead of remote."
		print "Push required to sync."
		c = raw_input(COLORS.MAGENTA + "Push changes now?" + COLORS.END + " [N]: ").strip()
		if c.lower() == 'y':
			os.system('git push')
		else:
			raise BuildException("Repository Status: %s" % status)	
			sys.exit()
	elif status == "Need to pull":
		print "Local is behind remote."
		print "Pull required to sync."
		c = raw_input(COLORS.MAGENTA + "Pull now?" + COLORS.END + " [N]: ").strip()
		if c.lower() == 'y':
			os.system('git pull')
	else:
		raise BuildException("Repository Status: %s" % status)	
		sys.exit()


'''*

Simple build script for maintaining repo versions and packaging addons for release.
Maintains a running list of build versions and prompts for upgrade and new version info.

Version prompts:
	x.x.x: specify a specific version number
	+: increment minor version x.x.(x+1)
	++: increment major version x.(x+1).0
	+++: increment build version (x+1).0.0

*'''

''' Define paths here '''
root_dir = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
addon_path = config.get('directories', 'output_dir')
work_path = os.path.join(root_dir, "work")
addon_dir = os.path.join(root_dir, addon_path)
work_dir = os.path.join(root_dir, work_path)

for d in [addon_dir, work_dir]:
	if not os.path.exists(d): os.mkdir(d)

''' load version file if exists '''
version_file = os.path.join("%s/versions.json" % CONFIG_DIR)
if os.path.exists(version_file):
	version_list = json.loads(open(version_file, "r").read())
else:
	version_list = {}


if options.LIST:
	print "Available addons in repository:"
	for a in addon_list:
		v = version_list[a] if a in version_list else 'None'
		print "\t%s: %s" % (a, v)

def get_version(i,c):
	if re.match("^\d+\.\d+\.\d+$", i):
		return i
	elif i == '+':
		temp = c.split('.')
		temp[2] = str(int(temp[2]) + 1)
		return '.'.join(temp)
	elif i == '++':
		temp = c.split('.')
		temp[1] = str(int(temp[1]) + 1)
		temp[2] = '0'
		return '.'.join(temp)
	elif i == '+++':
		temp = c.split('.')
		temp[0] = str(int(temp[0]) + 1)
		temp[1] = '0'
		temp[2] = '0'
		return '.'.join(temp)
	elif i == "":
		return c
	return False

def zipdir(path, ziph, addon_id):
	# ziph is zipfile handle
	for root, dirs, files in os.walk(path):
		new_root = os.path.join(addon_id, root[len(path)+1:])
		for file in files:
			ziph.write(os.path.join(root, file), os.path.join(new_root, file))

def md5(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

addons_path = os.path.join(addon_dir, "addons.xml")


if not os.path.exists(addons_path):
	print "addons.xml is missing"
	print "writing blank template"
	shutil.copy("config/addons.xml.template", addons_path)
		
	#raise BuildException('addons.xml missing')
addons_tree = ET.parse(addons_path)
addons_root = addons_tree.getroot()

def compile_addon(addon_id):
	global addons_tree, addons_root, addon_list, version_list
	global root_dir, addon_dir, work_dir
	if addon_id not in addon_list:
		raise BuildException("Unknown addon_id")
	host = host_map[addon_id] if addon_id in host_map else config.get('git', 'git_host')	
	username = user_map[addon_id] if addon_id in user_map else config.get('git', 'git_username')
	git_url = "git@%s:%s/%s.git" % (host, username, addon_id)
	print git_url 
	output_path = os.path.join(work_dir, addon_id)
	shutil.rmtree(output_path, ignore_errors=True)
	os.system("git clone %s %s" % (git_url, output_path))
	ref_path = "%s/%s/.git/packed-refs" % (work_path, addon_id)
	with open(ref_path, "r") as ref:
		cur_hash = re.search("(\S+)\srefs", ref.read()).group(1)
	shutil.rmtree("%s/%s/.git" % (work_path, addon_id), ignore_errors=True)
	try: os.remove("%s/%s/.gitignore" % (work_path, addon_id))
	except: pass
	tree = ET.parse(os.path.join(output_path, "addon.xml"))
	root = tree.getroot()
	for addon in root.iter('addon'):
		cur_version = addon.get('version')
		addon_name = addon.get('name')
		break

	if addon_id in version_list:
		cur_version = version_list[addon_id]["version"]
		if 'hash' in version_list[addon_id]:
			prev_hash = version_list[addon_id]['hash']
		else:
			prev_hash = ""
	else:
		cur_version = '0.0.0'
		prev_hash = ''

	if cur_hash == prev_hash:
		prompt_string = "{color}Compile {addon}{end} [N]: ".format(color=COLORS.GREEN, addon=addon_name, end=COLORS.END)
	else:
		prompt_string = "{color}Compile {addon}{end} [N]: ".format(color=COLORS.RED, addon=addon_name, end=COLORS.END)

	c = raw_input(prompt_string).strip()
	if c.lower() != "y": return
	
	version = raw_input("%s Version [%s]: " % (addon_name, cur_version)).strip()
	version = get_version(version, cur_version)
	if not version: raise BuildException("Version Error: Invalid version format.")
	print "Setting %s version to %s" % (addon_name, version)
	version_list[addon_id]["version"] = version
	version_list[addon_id]["hash"] = cur_hash
	for addon in root.iter('addon'):
		addon.set('version', version)
		break
	for a in addons_root.iter('addon'):
		if addon_id == a.get('id'):
			addons_root.remove(a)
	addons_root.append(root)
	if not os.path.exists("%s/%s" % (addon_path, addon_id)): os.mkdir("%s/%s" % (addon_path, addon_id))
	''' update xml '''
	print "Updating addons.xml file"
	output_xml = os.path.join(output_path, "addon.xml")
	dir_xml = os.path.join("%s/%s/addon.xml" % (addon_path, addon_id))
	if os.path.exists(output_xml): os.remove(output_xml)
	if os.path.exists(dir_xml): os.remove(dir_xml)
	tree.write(output_xml, xml_declaration=True, encoding='utf-8')
	tree.write(dir_xml, xml_declaration=True, encoding='utf-8')
	for f in ['fanart.jpg', 'icon.png']:
		src = "%s/%s/%s" % (work_path, addon_id, f)
		if os.path.exists(src):
			dst = "%s/%s/%s" % (addon_path, addon_id, f)
			shutil.copy(src, dst)
	output_zip = "%s/%s/%s-%s.zip" % (addon_path, addon_id, addon_id, version)
	if os.path.exists(output_zip):
		os.remove(output_zip)
	zipf = zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED)
	zipdir('%s/%s' % (work_path, addon_id), zipf, addon_id)
	zipf.close()

if __name__ == '__main__':
	if options.BuildID is not None:
		compile_addon(options.BuildID)
	elif options.AddonID is not None:
		compile_addon(options.AddonID)
	else:
		for addon_id in addon_list:
			compile_addon(addon_id)

	output_f = '%s/addons.xml' % addon_path
	addons_tree.write(output_f, xml_declaration=True, encoding='utf-8')
	check = md5(output_f)
	print "Writing %s and md5" % output_f
	open(output_f + ".md5" , 'w').write(check)

	open(version_file , 'w').write(json.dumps(version_list))

	''' Add new files '''
	c = raw_input(COLORS.YELLOW + "Commit changes?" + COLORS.END + " [Y]: ").strip()
	if c.lower() != 'n':
		os.system("git add %s" % addon_path)
		message = strftime("Updated at %D %T")
		os.system('git commit -a -m "%s"' % message)
	else:
		sys.exit()
	c = raw_input(COLORS.YELLOW + "Push changes?" + COLORS.END + " [N]: ").strip()
	if c.lower() == 'y':
		os.system('git push')
		print "Complete!"
	else:
		print COLORS.RED + "Don't forget to commit your changes" + COLORS.END



