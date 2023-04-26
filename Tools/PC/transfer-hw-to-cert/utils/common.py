import json
import re


def is_valid_cid(cid: str) -> bool:
    """ Check if it's valid of the format of CID
        The format of CID is yyyymm-{5 random number}
        Valid range of yyyy is from 2000 to 2099
        Valid range of mm is 01 to 12
    """
    pattern = re.compile(r'^20\d{2}0[1-9]-\d{5}$|^20\d{2}1[0-2]-\d{5}$')
    return True if re.match(pattern, cid) else False


def is_valid_location(location: str) -> bool:
    """ Check if it's valid of the format of Location
    """
    pattern = re.compile(
        r'^TEL-L\d-F\d{2}-S\d-P[12]$|^TEL-L\d-R\d{2}-S\d{1,2}-P0$')
    return True if re.match(pattern, location) else False


def read_json_config(config_path: str) -> dict:
    if not config_path.endswith(".json"):
        raise Exception(f"Expect JSON config file but got {config_path}")
    with open(config_path) as config_file:
        file_contents = config_file.read()
        return json.loads(file_contents)


def parse_location(location: str) -> dict:
    """ Parse the location data
    """
    part_re = re.compile(
        '(?P<Lab>TEL-L\d)-(?P<Frame>F\d+)-S(?P<Shelf>\d+)-P(?P<Partition>\d+)'  # noqa: W605, E501
    )
    match = re.search(part_re, location)
    return {} if not match else {
        'Lab': match.group('Lab'),
        'Frame': match.group('Frame'),
        'Shelf': match.group('Shelf'),
        'Partition': match.group('Partition')
    }
