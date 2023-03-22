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

url = f"https://certification.canonical.com/api/v1/hardware/{cid}/?username={username}&api_key={api_key}&format=json"
data = requests.get(url)
data_req = json.loads(data.text)

with open("hardware_info.txt", "wt") as f:
    f.write(f"CID: {cid}\n")
    f.write(f"Secure ID: {data_req.get('secure_id')}\n")
    f.write(f"C3: https://certification.canonical.com/hardware/{cid}\n")
    f.write(f"SKU: {data_req.get('sku')}\n")
