from utils.common import is_valid_cid, is_valid_location

"""
    This python script handles the procedure of filling the DUT's information
    in the Cert Team's Google Sheet.
"""


def is_valid_input_data(data: list[dict]) -> tuple[bool, list]:
    """ Check the input data's content is valid.
        Currently, this function checks the value of CID and Location

        @param:data, a list contains the bunch of dictionary data, each
                    data has the following keys, CID, Location and the link
                    of GM image.
            e.g.
                data = [
                    {
                        'cid': '20230405-12345',
                        'location': 'TEL-L3-F24-S5-P2'
                        'gm_image_link': ''
                    },
                    {
                        'cid': '20230405-12346',
                        'location': 'TEL-L3-F23-S5-P2'
                        'gm_image_link': 'http://oem-share'
                    }
                ]
        @return
            bool: True if all data are valid, otherwise False
            list: invalid list. It shows all invalid data in a list
    """
    invalid_list = []
    mandatory_keys = ['cid', 'location', 'gm_image_link']

    for d in data:
        is_data_valid = True
        # Check keys exist in dictionary
        for mk in mandatory_keys:
            if mk not in d:
                is_data_valid = False

        # No need to perform the following checks since missing the key
        if not is_data_valid:
            invalid_list.append(d)
            continue

        is_data_valid = is_valid_cid(d['cid']) and \
            is_valid_location(d['location'])

        if not is_data_valid:
            invalid_list.append(d)

    return not len(invalid_list), invalid_list


def are_sheet_cells_empty(data: list[dict]) -> tuple[bool, list]:
    """ Check the cells are empty on Cert Lab Google Sheet
        Currently, this function checks the value of CID and
        Certified_OEM_Image
    """
    pass


def update_cert_lab_google_sheet(data: list[dict]) -> bool:
    """ Fill the DUT information to the Cert Lab Google Sheet

        @param:data, a list contains the bunch of dictionary data, each
                    data has the following keys, CID, Location and the link
                    of GM image.
            e.g.
                data = [
                    {
                        'cid': '20230405-12345',
                        'location': 'TEL-L3-F24-S5-P2'
                        'gm_image_link': ''
                    },
                    {
                        'cid': '20230405-12346',
                        'location': 'TEL-L3-F23-S5-P2'
                        'gm_image_link': 'http://oem-share'
                    }
                ]
        @return
            bool: True if all data are valid, otherwise False
            list: invalid list. It shows all invalid data in a list
    """
    # Sanitize data
    is_valid_input_data(data)

    # Check the google sheet

    # fill the data to google sheet
