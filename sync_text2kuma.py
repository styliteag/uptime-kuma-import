#!/usr/bin/env python3

import os
import time
import json
import re
import sys
#from dotenv import load_dotenv
import configparser
from uptime_kuma_api import UptimeKumaApi, MonitorType

# default values
interval = 120
retryInterval = 120
resendInterval = 60
maxretries = 3
timeout = 10 # seconds after the monitor is considered as down
expiryNotification = False

#
api_timeout=10


def edit_monitor_with_retry(func, id, **kwargs):
  global api, api_timeout, base_url, username, password
  success = False
  while not success:
    try:
        if func == "add":
          if verbose:
            print(f"  Add Monitor: {kwargs['name']}")
          result = api.add_monitor(**kwargs)
        elif func == "edit":
          if verbose:
            print(f"  Edit Monitor: {id}")
          result = api.edit_monitor(id, **kwargs)
        else:
          print("Unknown function")
          return
        success = True
    except Exception as e:
        #print( "  An exception occurred:", type(e).__name__, "–", e)
        #print(f"  retrying: {id}")
        success = False
        #api.disconnect()
        #api = UptimeKumaApi(base_url ,timeout=api_timeout)
        lsuccess = False
        while not lsuccess:
          try:
              #print(f"  Login again: {username}")
              api.login(username, password)
              lsuccess = True
          except Exception:
              #print("Login failed")
              time.sleep(2)
              lsuccess = False

if "-h" in sys.argv:
  print(f"Usage: {sys.argv[0]} [-u] [-f input_file] [-c config_file]")
  print("  -h: show this help")
  print("  -u: update the existing monitors")
  print("  -c config_file: use the config file (default: SCRIPTNAME.ini)")
  print("  -f input_file: use the file input_file as input (default: urls.txt)")
  print("  -v: verbose output")
  exit(0)

verbose = False
if "-v" in sys.argv:
  verbose = True

do_updates = False
if "-u" in sys.argv:
  do_updates = True
  
input_file_name = "urls.txt"

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

# Read the config file
config = configparser.ConfigParser()
config.read(config_file_name)

# get baseurl form config
base_url = config.get("uptimekuma", "base_url")
username = config.get("uptimekuma", "username")
password = config.get("uptimekuma", "password")
parent = config.get("uptimekuma", "parent", fallback="AutoChecks")

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
#print(json.dumps(monitors, indent=2))

# Get all Mointors IDs from pages
monitor_id = []
monitor_name = []
monitor_pathname = []
monitor_type = []
for monitor in monitors:
  monitor_id.append(monitor["id"])
  monitor_name.append(monitor["name"])
  monitor_pathname.append(monitor["pathName"])
  monitor_type.append(monitor["type"])
  if verbose:
    print(f"Monitor ID: {monitor['id']}, Name: {monitor['name']}, Type: {monitor['type']}, PathName: {monitor['pathName']}")

# Find the parent Group ID
parent_group_id = 0
for i in range(len(monitor_id)):
  if monitor_name[i] == parent and monitor_type[i] == "group":
    parent_group_id = monitor_id[i]
    break
  else:
    parent_group_id = 0

if parent_group_id == 0:
  print(f"Parent Group {parent} not found")
  exit(1)


#######################################################################################################################
# Read the input file
name = "Undefined"
url = "Undefined"
check_mk_warn_default = 0
check_for_default = ""
check_for = ""
url_suffix = ""
url_suffix_default = ""
do_special = False
name1 = ""
name2 = ""
warntimes = {}
keywords = {}
keyword_urls = {}
intervals = {}
retryIntervals = {}
resendIntervals = {}
maxretriess = {}
timeouts = {}
expiryNotifications = {}
with open(input_file_name, 'r') as file:
  # Read a line from the ffile until the end of the file
  for line in file:
    check_mk_hint = "null" # This is the default which gets reported

    line = line.strip()
    #print(f"Line: {line}")
    # If the line starts with a #, then it is a comment
    if line.startswith("#"):
      continue
    # If the line is empty, then skip
    if len(line) == 0:
      continue

    if line.startswith("keyword="):
      check_for_default = line.split("=")[1]
      continue
    url_suffix = url_suffix_default
    if line.startswith("keyword_url="):
      url_suffix_default = line.split("=")[1]
      continue
    check_for = check_for_default
    if line.startswith("warn="):
      # Set a new default for the check_mk_warn for the rest of the file
      check_mk_warn_default = int(line.split("=")[1])
      continue
    check_mk_warn = check_mk_warn_default
    if line.startswith("interval="):
      interval = int(line.split("=")[1])
      continue
    if line.startswith("retryInterval="):
      retryInterval = int(line.split("=")[1])
      continue
    if line.startswith("resendInterval="):
      resendInterval = int(line.split("=")[1])
      continue
    if line.startswith("maxretries="):
      maxretries = int(line.split("=")[1])
      continue
    if line.startswith("timeout="):
      timeout = int(line.split("=")[1])
      continue
    if line.startswith("expiryNotification="):
      expiryNotification1 = int(line.split("=")[1])
      if expiryNotification1 == 1:
        expiryNotification = True
      else:
        expiryNotification = False
      continue
    if line.startswith("warn "):
      parts = line.split(" ",2)
      search = parts[1]
      warntime = int(parts[2])
      warntimes[search] = warntime
      continue
    if line.startswith("keyword "):
      parts = line.split(" ",2)
      search = parts[1]
      keyword = parts[2]
      keywords[search] = keyword
      continue
    if line.startswith("keyword_url "):
      parts = line.split(" ",2)
      search = parts[1]
      keyword = parts[2]
      keyword_urls[search] = keyword
      continue
    if line.startswith("interval "):
      parts = line.split(" ",2)
      search = parts[1]
      interval = int(parts[2])
      intervals[search] = interval
      continue
    if line.startswith("retryInterval "):
      parts = line.split(" ",2)
      search = parts[1]
      retryInterval = int(parts[2])
      retryIntervals[search] = retryInterval
      continue
    if line.startswith("resendInterval "):
      parts = line.split(" ",2)
      search = parts[1]
      resendInterval = int(parts[2])
      resendIntervals[search] = resendInterval
      continue
    if line.startswith("maxretries "):
      parts = line.split(" ",2)
      search = parts[1]
      maxretries = int(parts[2])
      maxretriess[search] = maxretries
      continue
    if line.startswith("timeout "):
      parts = line.split(" ",2)
      search = parts[1]
      timeout = int(parts[2])
      timeouts[search] = timeout
      continue
    if line.startswith("expiryNotification "):
      parts = line.split(" ",2)
      search = parts[1]
      expiryNotification1 = int(parts[2])
      if expiryNotification1 == 1:
        expiryNotification = True
      else:
        expiryNotification = False
      expiryNotifications[search] = expiryNotification
      continue

    
    # Wenn kein : enthalten ist, dann ist es ein Gruppenname
    if ":" not in line:
      name = line
      do_special = False
      name1 = ""
      name2 = ""

      # When ein - drin ist verändere den Namen/reihenfolge
      #print(f"Group: {line}")
      if "-" in name:
        # Verstausche die beiden Teile
        parts = name.split("-",1)
        if len(parts) > 0:
          #print(f"  parts: {parts}")
          name1 = parts[0].strip()
          name2 = parts[1].strip()
          do_special = True
          #print(f"  name1: {name1}, name2: {name2}")
      continue
    else:
      # Wenn ein : enthalten ist, dann ist es ein URL zum checkem
      parts = line.split(":",1)
      # Get the name and the url
      check = parts[0].strip()
      rest = parts[1].strip()
      # Split the rest into URL and keyword
      parts = rest.split(" ",1)
      if len(parts) > 1:
        url = parts[0].strip()
        check_for = parts[1].strip()
      else:
        url = rest.strip()
        check_for = ""
      # Does check_for contain string like "(299ms)"? check with a regex
      matches = re.findall(r'\((\d+)ms\)', check+check_for)
      if matches:
        check_mk_warn = int(matches[0])
        pattern = r'\s*\(\d+ms\)'
        check_for = re.sub(pattern, '', check_for).strip()
        check     = re.sub(pattern, '', check).strip()

  
    if not url.startswith("http"):
      continue
    
    if url.startswith("https:"):
      expiryNotification = True
    else:
      expiryNotification = False
    
    #if check_for == "":
    # Loop over all dictionaries
    check_for_temp = ""
    for dictionary in [warntimes, keywords, keyword_urls, intervals, retryIntervals, resendIntervals, maxretriess, timeouts, expiryNotifications]:
      for search in dictionary:
        if search in check: # if check.contains(search)
          if dictionary is warntimes:
            check_mk_warn = int(dictionary[search])
          elif dictionary is keywords:
            check_for_temp = dictionary[search]
          elif dictionary is keyword_urls:
            url_suffix = dictionary[search]
          elif dictionary is intervals:
            interval = int(dictionary[search])
          elif dictionary is retryIntervals:
            retryInterval = int(dictionary[search])
          elif dictionary is resendIntervals:
            resendInterval = int(dictionary[search])
          elif dictionary is maxretriess:
            maxretries = int(dictionary[search])
          elif dictionary is timeouts:
            timeout = int(dictionary[search])
          elif dictionary is expiryNotifications:
            expiryNotification = expiryNotifications[search]
          break

      if check_for == "":
        # Kein keyword speziell für diesen check gefunden
        check_for = check_for_temp
      # End of loop over all dictionaries

    if url_suffix == "":
      url_suffix = url_suffix_default
    if url_suffix != "":
      # Strip a trailing / from the url
      if url.endswith("/"):
        url = url[:-1]
      # strip a leading / from the url_suffix
      if url_suffix.startswith("/"):
        url_suffix = url_suffix[1:]
      url = url + "/" + url_suffix
      #print(f"  URL: {url}")
        
      
      check_mk_hint = ""
      if check_mk_warn > 0:
        check_mk_hint = f"({check_mk_warn}ms)"
  

    #print(f"Name: {check}, URL: {url}, Check for: {check_for}, Interval: {interval}, retryInterval: {retryInterval}, resendInterval: {resendInterval}, maxretries: {maxretries}, timeout: {timeout}, expiryNotification: {expiryNotification}, check_mk_hint: {check_mk_hint}")
    #print(f"name1: {name1}, name2: {name2}")
    myname = f"{name} - {check}"
    if do_special:
      myname = f"{name2} - {check} - {name1}"

    check_type=MonitorType.HTTP
    if check_for != "":
      check_type=MonitorType.KEYWORD
    # Check if the Monitor already exists
    if myname in monitor_name:
      #id=monitor_name.index(myname)
      id=monitor_id[monitor_name.index(myname)]
      #continue
      print(f"  Monitor edit: {myname} already exists")
      if not do_updates:
        print(f"  Not updating {myname}")
        continue
      edit_monitor_with_retry("edit", id,
          type=check_type,
          name=myname,
          url=url,
          parent=parent_group_id,
          keyword=check_for,
          interval=interval,
          retryInterval=retryInterval,
          resendInterval=resendInterval,
          maxretries=maxretries,
          expiryNotification=expiryNotification,
          timeout=timeout,
          description=f"Changed on {time.strftime('%Y-%m-%d %H:%M:%S')} by sync_stylite.py",
          hostname=check_mk_hint # This is visible in the metrics api, we use it to gie some hints to check_mk/omd
        )

      continue

    print(f"  Monitor add: {myname}")
    edit_monitor_with_retry("add", 0,
          type=check_type,
          name=myname,
          url=url,
          parent=parent_group_id,
          keyword=check_for,
          interval=interval,
          retryInterval=retryInterval,
          resendInterval=resendInterval,
          maxretries=maxretries,
          expiryNotification=expiryNotification,
          timeout=timeout,
          description=f"Changed on {time.strftime('%Y-%m-%d %H:%M:%S')} by sync_stylite.py",
          hostname=check_mk_hint # This is visible in the metrics api, we use it to gie some hints to check_mk/omd
      )

api.disconnect()