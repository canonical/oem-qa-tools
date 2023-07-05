import requests
import json

HIC_URL = 'http://10.102.180.14:5000'


def query_database() -> dict:
    """ Query the databse to get whole mapping

        @return, a dictionary data like below
            {
                "48:9e:bd:ea:d3:d4": "Varc-PV-SKU6-1_202302-31212",
                "00:be:43:bd:cf:16": "TRM-DVT1-L10-C1_202304-31528"
            }
    """
    try:
        response = requests.request(
            'GET',
            f'{HIC_URL}/q'
        )
        if response.status_code < 200 or response.status_code > 299:
            response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Unable to query the HIC database. Error: {e}")
        raise


def delete_duts(cids: list[str]) -> None:
    """ Remove DUTs from HIC site

        @param:cids, a list which contains CIDs
            e.g cids: ['202306-12345']
    """
    if not cids:
        print('Do nothing due to empty cids list received')
        return

    # Query database to get whole records
    mapping = query_database()

    duts = []
    for cid in cids:
        temp_d = {
            'sku_name': '',
            'mac_addresses': []
        }
        # Find designated DUT from mapping
        # Get its mac addresses into temp_d
        for k, v in mapping.items():
            if cid in v:
                temp_d['sku_name'] = v
                temp_d['mac_addresses'].append(k)
        if not temp_d['sku_name']:
            print(f"Ignore {cid} since there\'s no record on HIC")
            continue
        if temp_d['sku_name']:
            duts.append(temp_d)

    if len(duts) == 0:
        print('All of the following DUTs have been removed')
        print(cids)
        return

    print('Will remove the following DUTs from HIC...')
    print(json.dumps(duts, indent=2))

    success = 1
    for d in duts:
        for mac in d['mac_addresses']:
            try:
                response = requests.request(
                    'GET',
                    f'{HIC_URL}/d?db=sku&k={mac}'
                )
                if response.status_code < 200 or response.status_code > 299:
                    response.raise_for_status()
            except Exception as e:
                success = 0
                print(f"Error: Unable to remove {d['sku_name']} ({mac})")
                print(e)
    if not success:
        raise Exception('Error: Some DUTs cannot be removed from HIC!')
