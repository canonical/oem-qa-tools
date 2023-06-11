import os
import json

from C3.apis.base import C3API, TaipeiLocation
from utils.common import parse_location


def init_c3_api() -> object:
    c3 = C3API() if os.path.exists('./configs/production_c3.txt') \
        else C3API(
        base_url='https://certification.staging.canonical.com/api/v1/hardware')

    return c3


def update_duts_info_on_c3(data: list[dict], new_holder: str):
    """ Update DUTS' information on C3 webstie

        Currently, we update the holder and location
    """
    c3 = init_c3_api()

    for dut in data:
        # print(dut['cid'], dut['location'])
        # print(parse_location(dut['location'])['Lab'].replace('-', '_'))
        payload = {
            'holder': new_holder,
            'location': TaipeiLocation[
                parse_location(dut['location'])['Lab'].replace('-', '_')].value
        }
        print('Updating {}'.format(dut['cid']))
        res = c3.update_dut_by_cid(cid=dut['cid'], payload=payload)
        if res.status_code < 200 or res.status_code > 299:
            raise Exception('Error: update failed')


def get_duts_info_from_c3(data: list[dict]) -> list:
    """ Get DUTS' information from C3 webstie

        return 
    """
    c3 = init_c3_api()

    r_list = []
    for dut in data:
        res = c3.get_dut_by_cid(dut['cid'])
        d = json.loads(res.text)
        if res.status_code < 200 or res.status_code > 299:
            raise Exception('Error: {}'.format(res.text))
        if d['meta']['total_count'] != 1:
            raise Exception('Error: fail to get {} from C3. url: {}'.format(
                dut['cid'],
                c3.base_url
            ))
        temp_d = {
            'cid': dut['cid'],
            'make': d['objects'][0]['platform']['vendor']['name'],
            'model': d['objects'][0]['platform']['name']
        }
        r_list.append(temp_d)

    return r_list
