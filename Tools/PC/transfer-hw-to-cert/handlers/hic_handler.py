import requests
import json

HIC_URL = "http://10.102.180.14:5000"


def hic_request(parameter: str) -> dict:
    """Query the databse to get whole mapping

    @return, a dictionary data
    """
    mapping = {}
    try:
        response = requests.request("GET", f"{HIC_URL}/{parameter}")
        if response.status_code < 200 or response.status_code > 299:
            response.raise_for_status()
        return response.json()
    except Exception as e:
        print(
            f"====Unable to query the HIC database.==== "
            f"Please check your connection. Error: {e}"
        )

    return mapping


def query_database() -> dict:
    """Query the databse to get whole mapping

    @return, a dictionary data like below
        {
            "48:9e:bd:ea:d3:d4": "Varc-PV-SKU6-1_202302-31212",
            "00:be:43:bd:cf:16": "TRM-DVT1-L10-C1_202304-31528"
        }
    """
    return hic_request("q")


def query_ip() -> dict:
    """Query the databse to get whole mapping

    @return, a dictionary data like below
        {
            "LUSA14-PV-SKU8_202401-33447": ["10.102.183.232"],
            "PX-SIT-C6_202404-33916":["10.102.182.246","10.102.182.104"]
        }
    """
    return hic_request("q?db=ipo")


def get_dut_info(cid: str, macs: dict, ips: dict) -> dict:
    """mapping the dut data with mac, ip and cid

    @return, a dictionary data
    """
    info = {}
    for k, v in macs.items():
        if cid in v:
            info["MAC"] = k
    for k, v in ips.items():
        if cid in k:
            info["IP"] = v[0]
    return info


def get_duts_info(cids: list[str]) -> dict:
    """mapping all the duts data with mac, ip and cid

    @return, a dictionary data
    """
    macs = query_database()
    ips = query_ip()
    duts_info = {}
    for cid in cids:
        duts_info[cid] = get_dut_info(cid, macs, ips)
    return duts_info


def delete_duts(cids: list[str]) -> None:
    """Remove DUTs from HIC site

    @param:cids, a list which contains CIDs
        e.g cids: ['202306-12345']
    """
    if not cids:
        print("Do nothing due to empty cids list received")
        return

    # Query database to get whole records
    mapping = query_database()

    duts = []
    for cid in cids:
        temp_d = {"sku_name": "", "mac_addresses": []}
        # Find designated DUT from mapping
        # Get its mac addresses into temp_d
        for k, v in mapping.items():
            if cid in v:
                temp_d["sku_name"] = v
                temp_d["mac_addresses"].append(k)
        if not temp_d["sku_name"]:
            print(f"Ignore {cid} since there's no record on HIC")
            continue
        if temp_d["sku_name"]:
            duts.append(temp_d)

    if len(duts) == 0:
        print("All of the following DUTs have been removed")
        print(cids)
        return

    print("Will remove the following DUTs from HIC...")
    print(json.dumps(duts, indent=2))

    success = 1
    for d in duts:
        for mac in d["mac_addresses"]:
            try:
                response = requests.request(
                    "GET", f"{HIC_URL}/d?db=sku&k={mac}"
                )
                if response.status_code < 200 or response.status_code > 299:
                    response.raise_for_status()
            except Exception as e:
                success = 0
                print(f"Error: Unable to remove {d['sku_name']} ({mac})")
                print(e)
    if not success:
        print("Error: Some DUTs cannot be removed from HIC!")
