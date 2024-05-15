import os

from C3.apis.base import C3API, C3Location
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
        payload = {
            'holder': new_holder,
            'location': C3Location[
                parse_location(dut['location'])['Lab'].replace('-', '_')].value
        }
        print(f"Updating {dut['cid']}")
        res = c3.update_dut_by_cid(cid=dut['cid'], payload=payload)
        if res.status_code < 200 or res.status_code > 299:
            raise Exception('Error: update failed')


def update_returned_duts_info_on_c3(data: list[dict], status: str):
    """ Update DUTS' information on C3 website
        For the returned DUTs, we update the location and the status
    """
    c3 = init_c3_api()
    for dut in data:
        payload = {
            'location': C3Location.Return.value,
            'status': status,
        }
        print(f"Updating {dut['cid']}")
        res = c3.update_dut_by_cid(cid=dut['cid'], payload=payload)
        if res.status_code < 200 or res.status_code > 299:
            raise Exception('Error: update failed')
