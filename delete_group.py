#!/usr/bin/env python3

import os
import json
from dotenv import load_dotenv
from uptime_kuma_api import UptimeKumaApi, MonitorType

load_dotenv()

base_url = os.getenv("BASE_URL")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
parent = os.getenv("PARENT")


api = UptimeKumaApi(base_url)
api.login(username, password)

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
  if monitor_name[i] == parent and monitor_type[i] == "group":
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