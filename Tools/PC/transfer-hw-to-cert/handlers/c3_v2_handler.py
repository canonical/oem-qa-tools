import logging
from modules.c3_relay_service.relay_service import (
    get_hostdata_list,
    get_hostdata_id,
    detach_hostdata,
    link_hostdata,
    LabPosition,
)
from utils.common import parse_location


def update_duts_info_on_c3(data: list[dict], new_holder: str):
    """
    Update DUTS' information on C3 webstie
    Currently, we detach the old and link the new hostdata

    :data: DUTs information.

    :new_holder: holder launchpad name

    :returns: None
    """
    hostdatas = get_hostdata_list(None, "DUT")
    for dut in data:
        cid = dut['cid']
        logging.info(f"Updating {cid}")
        # detach hostdata
        resp = detach_hostdata(cid, hostdatas)
        if resp["canonical_id"]:
            logging.error(f"detach hostdata from CID:{cid} failed")
        loc = parse_location(dut["location"])
        pos = LabPosition(
            loc["Lab"], loc["Frame"], int(loc["Shelf"]), int(loc["Partition"])
        )
        hostdata_id = get_hostdata_id(pos)
        # link to new hostdata
        resp = link_hostdata(cid, hostdata_id)
        if resp["canonical_id"] != cid:
            logging.error(f"link hostdata to CID:{cid} failed")
        # TODO There is no V2 API to change holder by lunchpad name.
        #      Have to wait or find the solution.


def update_returned_duts_info_on_c3(data: list[dict], status: str):
    """
    Update DUTS' information on C3 webstie
    Currently, we detach the old hostdata and update location and status

    :data: DUTs information.

    :status: status

    :returns: None
    """
    hostdatas = get_hostdata_list(None, "DUT")
    for dut in data:
        cid = dut["cid"]
        logging.info(f"Updating {cid}")
        # detach hostdata
        resp = detach_hostdata(cid, hostdatas)
        if resp["canonical_id"]:
            logging.error(f"detach hostdata from CID:{cid} failed")
        # TODO update status (New V2 API might be needed)
        # TODO There is no V2 API to change location.
        #      Have to wait or find the solution.
