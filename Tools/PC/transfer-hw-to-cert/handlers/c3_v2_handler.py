import logging
from modules.c3_relay_service.relay_service import (
    convert_to_c3_location_status,
    get_labresource_list,
    update_device_info,
    get_labresource_id,
    detach_labresource,
    link_labresource,
    LabPosition,
)
from utils.common import parse_location


def update_duts_info_on_c3(data: list[dict], new_holder: str):
    """
    Update DUTS' information on C3 webstie
    Currently, we detach the old and link the new labresource

    :data: DUTs information.

    :new_holder: holder launchpad name

    :returns: None
    """
    # limit the query in the TEL-L4 and TEL-L10
    pos = LabPosition("TEL-L4,TEL-L10", None, 0, 0)
    labresources = get_labresource_list(pos, "DUT")
    for dut in data:
        cid = dut["cid"]
        logging.info(f"Updating {cid}")
        # detach labresource
        resp = detach_labresource(cid, labresources)
        if resp["canonical_id"]:
            logging.error(f"detach labresource from CID:{cid} failed")
        loc = parse_location(dut["location"])
        pos = LabPosition(
            loc["Lab"], loc["Frame"], int(loc["Shelf"]), int(loc["Partition"])
        )
        labresource_id = get_labresource_id(pos)
        # link to new labresource
        resp = link_labresource(cid, labresource_id)
        if resp["canonical_id"] != cid:
            logging.error(f"link labresource to CID:{cid} failed")
        else:
            try:
                (new_loc, new_status) = convert_to_c3_location_status(pos)
                info = {
                    "holder": new_holder,
                    "location": new_loc,
                    "status": new_status,
                }
                resp = update_device_info(cid, info)
                if resp["canonical_id"] != cid:
                    logging.error(f"update status:[{new_status}] failed")
            except AttributeError as e:
                logging.error(f"position:[{pos}] error:{repr(e)}")


def update_returned_duts_info_on_c3(data: list[dict], status: str):
    """
    Update DUTS' information on C3 webstie
    Currently, we detach the old labresource and update location and status

    :data: DUTs information.

    :status: status (useless, it should be removed after C3 V1 API deprecated)

    :returns: None
    """
    # limit the query in the TEL-L4 and TEL-L10
    pos = LabPosition("TEL-L4,TEL-L10", None, 0, 0)
    labresources = get_labresource_list(pos, "DUT")
    for dut in data:
        cid = dut["cid"]
        logging.info(f"Updating {cid}")
        # detach labresource
        resp = detach_labresource(cid, labresources)
        if resp["canonical_id"]:
            logging.error(f"detach labresource from CID:{cid} failed")
        else:
            try:
                pos = LabPosition("Return", None, 0, 0)
                (new_loc, new_status) = convert_to_c3_location_status(pos)
                info = {"location": new_loc, "status": new_status}
                resp = update_device_info(cid, info)
                if resp["canonical_id"] != cid:
                    logging.error(f"update status:[{status}] failed")
            except AttributeError as e:
                logging.error(f"position:[{pos}] error:{repr(e)}")
