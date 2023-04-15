#!/usr/bin/env python3

import requests
import json
import configparser

print("\nGetting ID info from C3...")

config = configparser.ConfigParser()
config.read("./conf/setting.conf")
c3cfg = config["c3"]
username = c3cfg["username"]
api_key = c3cfg["api_key"]
cid = input("Please enter CID: ")

url = f"https://certification.canonical.com/api/v1/hardware/{cid}/" \
      f"?username={username}&api_key={api_key}&format=json"
data = requests.get(url)
data_req = json.loads(data.text)

with open("hardware_info.txt", "wt") as f:
    f.write(f"CID:\t\t{cid}\n")
    f.write(f"Secure ID:\t{data_req.get('secure_id')}\n")
    f.write(f"C3:\t\thttps://certification.canonical.com/hardware/{cid}\n")
    f.write(f"SKU:\t\t{data_req.get('sku')}\n")
