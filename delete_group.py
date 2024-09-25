#!/usr/bin/env python3

import os
import sys
import json
import configparser
#from dotenv import load_dotenv
from uptime_kuma_api import UptimeKumaApi, MonitorType

# default values
api_timeout=10


if "-h" in sys.argv:
  print(f"Usage: {sys.argv[0]} [-h] [-c config_file] [-v]")
  print("  -h: show this help")
  print("  -c config_file: use the config file (default: SCRIPTNAME.ini)")
  print("  -g groupname: delete all monitors in this group (default: default_group from config)")
  print("  -v: verbose output")
  exit(0)

verbose = False
if "-v" in sys.argv:
  verbose = True

if "-f" in sys.argv:
  input_file_name = sys.argv[sys.argv.index("-f")+1]

# Create a config_filename wich is the path iand the name of this script without the extension and with .ini
config_file_name = os.path.splitext(sys.argv[0])[0]+".ini"
#print(f"Config File: {config_file_name}")

if "-c" in sys.argv:
  config_file_name = sys.argv[sys.argv.index("-c")+1]

if not os.path.exists(config_file_name):
  print(f"Config File {config_file_name} not found")
  exit(1)

my_group = ""
if "-g" in sys.argv:
  my_group = sys.argv[sys.argv.index("-g")+1]

# Read the config file
config = configparser.ConfigParser()
config.read(config_file_name)

# get baseurl form config
base_url = config.get("uptimekuma", "base_url")
username = config.get("uptimekuma", "username")
password = config.get("uptimekuma", "password")
if my_group == "":
  default_group = config.get("uptimekuma", "default_group", fallback="AutoChecks")
else:
  default_group = my_group

if base_url is None:
  print("No BASE_URL given")
  exit(1)
if username is None:
  print("No USERNAME given")
  exit(1)
if password is None:
  print("No PASSWORD given")
  exit(1)

if verbose:
  print(f"Base URL: {base_url}")
  print(f"Username: {username}")
  #print(f"Password: {password}")
api = UptimeKumaApi(base_url ,timeout=api_timeout)
#if verbose:
#  print(f"API: {api}")
api.login(username, password)
if verbose:
  print(f"API: {api}")

monitors = api.get_monitors()
#print(json.dumps(result, indent=2))

# Get all Mointors IDs from pages
monitor_id = []
monitor_name = []
monitor_pathname = []
monitor_type = []
monitor_parent = []
for monitor in monitors:
  monitor_id.append(monitor["id"])
  monitor_name.append(monitor["name"])
  monitor_pathname.append(monitor["pathName"])
  monitor_type.append(monitor["type"])
  monitor_parent.append(monitor["parent"])
  
  #print(f"Monitor ID: {monitor['id']}, Name: {monitor['name']}, Type: {monitor['type']}, PathName: {monitor['pathName']}")

# Find the parent Group ID
parent_group_id = 0
for i in range(len(monitor_id)):
  if monitor_name[i] == default_group and monitor_type[i] == "group":
    parent_group_id = monitor_id[i]
    break
  else:
    parent_group_id = 0

# delete all Monitors in this group
for i in range(len(monitor_id)):
  if monitor_type[i] != "group" and monitor_parent[i] == parent_group_id:
    print(f"Deleting Monitor ID: {monitor_id[i]} Name: {monitor_name[i]} Type: {monitor_type[i]} PathName: {monitor_pathname[i]}")
    api.delete_monitor(monitor_id[i])

api.disconnect()