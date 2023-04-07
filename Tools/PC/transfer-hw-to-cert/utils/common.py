import re


def is_valid_cid(cid: str) -> bool:
    """ Check if it's valid of the format of CID
    """
    pattern = re.compile(r'^20\d{2}0[1-9]-\d{5}$|^20\d{2}1[0-2]-\d{5}$')
    return True if re.match(pattern, cid) else False


def is_valid_location(location: str) -> bool:
    """ Check if it's valid of the format of Location
    """
    pattern = re.compile(
        r'^TEL-L\d-F\d{2}-S\d-P[12]$|^TEL-L\d-R\d{2}-S\d{1,2}-P0$')
    return True if re.match(pattern, location) else False
