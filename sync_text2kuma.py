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
server_tags_queried = False

#
api_timeout=5 # seconds Default is 10
wait_events=2 # seconds Default is 0.2


def edit_monitor_with_retry(func, id, **kwargs):
  global api, username, password
  success = False
  while not success:
    try:
        if func == "add":
          if verbose:
            print(f"  Add Monitor: '{kwargs['name']}'")
          result = api.add_monitor(**kwargs)
        elif func == "edit":
          if verbose:
            print(f"  Edit Monitor: '{id}'")
          result = api.edit_monitor(id, **kwargs)
        else:
          print("Unknown function")
          return 0
        success = True
        return result["monitorID"]
    except Exception as e:
        #print( "  An exception occurred:", type(e).__name__, "–", e)
        #print(f"  retrying: {id}")
        success = False
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
    # If we are here, we have an error
    return 0

def server_add_tag(**kwargs):
  global api, username, password
  if verbose:
    print(f"Server:Add Tag {kwargs['name']} with color {kwargs['color']}")
  success = False
  while not success:
    try:
      result = api.add_tag(
        **kwargs
      )
      success = True
      return result
    except Exception as e:
        if verbose:
          print( "  An exception occurred:", type(e).__name__, "–", e)
        success = False
        lsuccess = False
        while not lsuccess:
          try:
              if verbose:
                print(f"  Login again: {username}")
              api.login(username, password)
              lsuccess = True
          except Exception:
              if verbose:
                print("Login failed")
              time.sleep(2)
              lsuccess = False

def remove_tags(monitor_id, tags):
  global api, username, password
  if verbose:
    print(f"  Remove unused tags from Monitor {monitor_id}")
  success = False
  while not success:
    try:
      result = api.get_monitor(monitor_id)
      #print(json.dumps(result, indent=2))
      monitor_tags = result["tags"]
      # Find all monitor_tags["name"] which are not in the tags array
      for monitor_tag in monitor_tags:
        if monitor_tag["name"] not in tags:
          print(f"  Remove Tag {monitor_tag['name']} with id {monitor_tag['tag_id']} from Monitor {monitor_id}")
          api.delete_monitor_tag(
            tag_id=monitor_tag["tag_id"],
            monitor_id=monitor_id
            ##value=monitor_tag["name"]
          )
      success = True
    except Exception as e:
        #print( "  An exception occurred:", type(e).__name__, "–", e)
        #print(f"  retrying: {id}")
        success = False
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
  
def add_tag(monitor_id, tag_id):
  global api, api_timeout, base_url, username, password
  if verbose:
    print(f"  Add Tag {tag_id} to Monitor {monitor_id}")
  # Check if the tag is already assigned
  success = False
  while not success:
    try:
  
      result = api.get_monitor(monitor_id)
      for monitor_tagid in result["tags"]:
        if monitor_tagid["tag_id"] == tag_id:
          if verbose:
            print(f"  Tag {tag_id} already assigned to Monitor {monitor_id}")
          return
      # If we are here, the tag is not assigned yet
      if verbose:
        print(f"  Add Tags")
      result = api.add_monitor_tag(
        tag_id=tag_id,
        monitor_id=monitor_id
        ##value="stylite"
      )
      success = True
    except Exception as e:
        #print( "  An exception occurred:", type(e).__name__, "–", e)
        #print(f"  retrying: {id}")
        success = False
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
    # If we are here, we have an error
    return 0

def create_group(name):
  global api, username, password, groups

  if verbose:
    print(f"  Create Group: {name}")

  if name in groups:
    if verbose:
      print(f" Group {name} already exists with ID {groups[name]}")
    return groups[name]

  success = False
  while not success:
    try:
      result = api.add_monitor(
          type="group", 
          name=name,
          description=f"{name}"
      )
      if verbose:
        print(json.dumps(result, indent=2))
        print(f"  Group {name} created with ID {result['monitorID']}")

      success = True
    except Exception as e:
        print( "  An exception occurred:", type(e).__name__, "–", e)
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
    monitor_id = result["monitorID"]
    groups[name] = monitor_id
    return monitor_id

if "-h" in sys.argv:
  print(f"Usage: {sys.argv[0]} [-u] [-f input_file] [-c config_file]")
  print("  -h: show this help")
  print("  -u: update the existing monitors")
  print("  -r: remove unused tags")
  print("  -c config_file: use the config file (default: SCRIPTNAME.ini)")
  print("  -f input_file: use the file input_file as input (default: urls.txt)")
  print("  -v: verbose output")
  print("  -n: no updates, just show what would be done (dry run)")
  exit(0)

verbose = False
if "-v" in sys.argv:
  verbose = True

do_updates = False
if "-u" in sys.argv:
  do_updates = True

remove_unused_tags = False
if "-r" in sys.argv:
  remove_unused_tags = True

try_only = False
if "-n" in sys.argv:
  try_only = True
  
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
group = config.get("uptimekuma", "default_group", fallback="AutoCheck")

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
api = UptimeKumaApi(base_url ,timeout=api_timeout, wait_events=wait_events)
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

# Find all groups in the Instance
groups = {}
for i in range(len(monitor_id)):
  if monitor_type[i] == "group":
    groups[monitor_name[i]] = monitor_id[i]
    if verbose:
      print(f"  found Group: {monitor_name[i]} with ID {monitor_id[i]}")

#######################################################################################################################
# Read the input file
name = "Undefined"
url = "Undefined"
check_mk_warn_default = 0
check_for_default = ""
check_for = ""
url_suffix = ""
url_suffix_default = ""
#do_special = False
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
tags = []
tag_id = {}
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

    if line.startswith("!"):
      # This is a command
      # Remove the !
      line = line[1:]
      parts = line.split(" ")
      keyword = parts[0]
      rest = " ".join(parts[1:])
      if verbose:
        print(f"Command: {keyword}, Rest: {rest}")
        print(json.dumps(parts, indent=2))

      # Check the commands
      if keyword == "group":
        group = rest
        if verbose:
          print(f"   Group: {group}")
        continue
      if keyword == "prefix":
        prefix = rest
        if verbose:
          print(f"   Prefix: {prefix}")
        continue
      if keyword == "suffix":
        suffix = rest
        if verbose:
          print(f"   Suffix: {suffix}")
        continue
      if keyword == "keyword_default":
        check_for_default = rest
        continue
      #url_suffix = url_suffix_default
      if keyword == "url_suffix_default":
        url_suffix_default = rest
        continue
      #check_for = check_for_default
      if keyword == "warn_default":
        # Set a new default for the check_mk_warn for the rest of the file
        check_mk_warn_default = int(rest)
        continue
      #check_mk_warn = check_mk_warn_default
      if keyword == "interval_default":
        interval = int(rest)
        continue
      if keyword == "retryInterval_default":
        retryInterval = int(rest)
        continue
      if keyword == "resendInterval_default":
        resendInterval = int(rest)
        continue
      if keyword == "maxretries_default":
        maxretries = int(rest)
        continue
      if keyword == "timeout_default":
        timeout = int(rest)
        continue
      if keyword == "expiryNotification_default":
        expiryNotification1 = int(rest)
        if expiryNotification1 == 1:
          expiryNotification = True
        else:
          expiryNotification = False
        continue
      if keyword == "tag":
        tag = rest
        if len(tag) > 0:
          tags = []
          # Split the tag into parts
          parts = tag.split(" ")
          for part in parts:
            tags.append(part)
        else:
          # If empty Clear the tag Array
          tags = []
        continue
      # check if we have two argument
      if len(parts) <= 2:
        print(f"WARNING:Not enough arguments for {keyword}, ignoring line '!{line}'")
        #print(json.dumps(parts, indent=2))
        continue
      else:
        # All this keywords have two arguments
        # The first one is the search string in name of the check
        # The second one is the value we want to set
        p1 = parts[1]
        p2 = parts[2]
        if keyword == "warn":
          search = p1
          warntime = int(p2)
          warntimes[search] = warntime
          continue
        if keyword == "keyword":
          search = p1
          keyword = p2
          keywords[search] = keyword
          continue
        if keyword == "keyword_url":
          search = p1
          keyword = p2
          keyword_urls[search] = keyword
          continue
        if keyword == "interval":
          search = p1
          interval = int(p2)
          intervals[search] = interval
          continue
        if keyword == "retryInterval":
          search = p1
          retryInterval = int(p2)
          retryIntervals[search] = retryInterval
          continue
        if keyword == "resendInterval":
          search = p1
          resendInterval = int(p2)
          resendIntervals[search] = resendInterval
          continue
        if keyword == "maxretries":
          search = p1
          maxretries = int(p2)
          maxretriess[search] = maxretries
          continue
        if keyword == "timeout":
          search = p1
          timeout = int(p2)
          timeouts[search] = timeout
          continue
        if keyword == "expiryNotification":
          search = p1
          expiryNotification1 = int(p2)
          if expiryNotification1 == 1:
            expiryNotification = True
          else:
            expiryNotification = False
          expiryNotifications[search] = expiryNotification
          continue
      print(f"Unknown Command: {line}")
      
    if ":" not in line:
      #name = line
      #do_special = False
      name1 = ""
      name2 = ""
      prefix = line
      suffix = ""

      # When ein - drin ist verändere den Namen/reihenfolge
      #print(f"Group: {line}")
      if "-" in line:
        # Verstausche die beiden Teile und setze den suffix
        parts = line.split("-",1)
        if len(parts) > 0:
          #print(f"  parts: {parts}")
          name1 = parts[0].strip()
          name2 = parts[1].strip()
          prefix = name2
          suffix = name1
          #do_special = True
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
    myname = check
    if prefix != "":
      myname = prefix + " - " + myname
    if suffix != "":
      myname = myname + " - " + suffix
    #myname = f"{name} - {check}"
    #if do_special:
    #  myname = f"{check} - {name2} - {name1}"
    #  print(f"  do_special: {myname}")

    check_type=MonitorType.HTTP
    if check_for != "":
      check_type=MonitorType.KEYWORD

    # Find the group ID
    group_id = 0
    if group in groups:
      group_id = groups[group]
    else:
      if verbose:
        print(f"Group {group} not found")
      if not try_only:
        group_id = create_group(group)
        if group_id == 0:
          print(f"Group {group} could not be created")
        exit(1)
      
    # Find the tag IDs
    if server_tags_queried == False:
      server_tags = api.get_tags()
      for server_tag in server_tags:
        if verbose:
          print(f"  Server Tag: {server_tag['name']} with ID {server_tag['id']}")
        tag_id[server_tag["name"]] = server_tag["id"]
      server_tags_queried = True

    # Add the tags if the tags array which does not exist yet
    for tag in tags:
      if tag not in tag_id:
        result = server_add_tag(
          name=tag,
          color="#900000"
        )
        tag_id[tag] = result["id"]
        if verbose:
          print(f"  Tag {tag} added with ID {tag_id[tag]}")
      
        
    # Check if the Monitor already exists
    monID = 0
    if myname in monitor_name:
      #id=monitor_name.index(myname)
      id=monitor_id[monitor_name.index(myname)]
      #continue
      print(f"  Monitor edit: '{myname}' already exists")
      if not do_updates:
        print(f"  Not updating '{myname}'")
        continue
      if not try_only:
        monID = edit_monitor_with_retry("edit", id,
            type=check_type,
            name=myname,
          url=url,
          parent=group_id,
          keyword=check_for,
          interval=interval,
          retryInterval=retryInterval,
          resendInterval=resendInterval,
          maxretries=maxretries,
          expiryNotification=expiryNotification,
          timeout=timeout,
          description=f"Changed on {time.strftime('%Y-%m-%d %H:%M:%S')} by sync_stylite.py",
          hostname=check_mk_hint # This is visible in the metrics api, we use it to give some hints to check_mk/omd
        )

    else:
      print(f"  Monitor add: '{myname}'")
      if not try_only:
        monID = edit_monitor_with_retry("add", 0,
          type=check_type,
          name=myname,
          url=url,
          parent=group_id,
          keyword=check_for,
          interval=interval,
          retryInterval=retryInterval,
          resendInterval=resendInterval,
          maxretries=maxretries,
          expiryNotification=expiryNotification,
          timeout=timeout,
          description=f"Changed on {time.strftime('%Y-%m-%d %H:%M:%S')} by sync_stylite.py",
          hostname=check_mk_hint # This is visible in the metrics api, we use it to give some hints to check_mk/omd
        )

    if verbose: 
      print(f"  Monitor ID: {monID}")
    if monID > 0:
      # Add the tags
      for tag in tags:
        add_tag(monID, tag_id[tag])
      if remove_unused_tags:
        remove_tags(monID, tags)
api.disconnect()