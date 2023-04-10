import pprint

from utils.common import is_valid_cid, is_valid_location, read_json_config

from GoogleSheet.google_sheet_api import GoogleSheetOperator

"""
    This python script handles the procedure of filling the DUT's information
    in the Cert Team's Google Sheet.
"""

pp = pprint.PrettyPrinter(indent=2)

GOOGLE_SHEET_CONF = read_json_config('./configs/google_sheet_link.json')


def create_google_sheet_instance():
    gs_obj = GoogleSheetOperator()
    gs_obj.prepare_sheet_obj()
    gs_obj.spreadsheet = GOOGLE_SHEET_CONF["sheet_link"]
    return gs_obj


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


def get_sheet_data() -> dict:
    """ Get the data from Google Sheet and generate the customized dictionary

        @reutrn: return a customized dictionary which contains the index of
                header and the indexed_table.

        e,g.
            # TEL-L5: is the name of table (sheet) on Google Sheet.
            # headers: shows the index of columns which make us can find the
                       target quickly.
            # indexed_table: use the location as key to build an hash table,
                             there are some values can help us find the target
                             cell quickly.

            { 'TEL-L5': {
                'headers': {
                    'CID': 0,
                    'Certified_OEM_Image': 9,
                    'Frame': 17,
                    'Lab': 16,
                    'Partition': 19,
                    'Shelf': 18},
                'indexed_table': {
                    'TEL-L5-F01-S1-P1': {
                        'CID': '202112-39487',
                        'Certified_OEM_Image': '',
                        'row_index': 2},
                    'TEL-L5-F01-S1-P2': {
                        'CID': '202304-23456',
                        'Certified_OEM_Image': '',
                        'row_index': 3},
                }
            }
    """
    sheet_data = {}
    gs_obj = create_google_sheet_instance()

    wanted_headers = [
        'CID', 'Certified_OEM_Image', 'Lab', 'Frame', 'Shelf', 'Partition']

    # t is TEL-L3 or TEL-L5
    for t in GOOGLE_SHEET_CONF['tables']:
        sheet_data[t] = {}
        # Get the first row (a.k.a header), such as CID, Lab, Frame ...
        headers = gs_obj.get_range_data(f'{t}!1:1', major_dimension="ROWS")
        # Generate the mapping of headers
        columns = {}
        for wh in wanted_headers:
            columns[wh] = headers[0].index(wh)
        sheet_data[t]['headers'] = columns

        # Get data without header
        offset = 2  # offest is the bias of start row number at google sheet
        data = gs_obj.get_range_data(
            f'{t}!A{offset}:Z', major_dimension="ROWS")

        # Build the indexed table (indexed by Location)
        indexed_table = {}
        for idx, v in enumerate(data):
            location = '{}-{}-{}-{}'.format(
                v[columns['Lab']],
                v[columns['Frame']],
                'S' + v[columns['Shelf']],
                'P' + v[columns['Partition']]
            )
            indexed_table[location] = {
                'row_index': idx+2,
                'CID': v[columns['CID']],
                'Certified_OEM_Image': v[columns['Certified_OEM_Image']]
            }
        sheet_data[t]['indexed_table'] = indexed_table

    return sheet_data


def find_sheet_row_index() -> int:
    pass


def are_sheet_cells_empty(data: list[dict]) -> tuple[bool, list]:
    """ Check the cells are empty on Cert Lab Google Sheet
        Currently, this function checks the value of CID and
        Certified_OEM_Image
    """
    test_obj = GoogleSheetOperator()
    test_obj.prepare_sheet_obj()
    test_obj.spreadsheet = GOOGLE_SHEET_CONF["sheet_link"]

    rts_range = 'test!Q1:T'
    key_data = test_obj.get_range_data(rts_range, major_dimension="ROWS")
    print(key_data)


def test_update():
    test_obj = GoogleSheetOperator()
    test_obj.prepare_sheet_obj()
    test_obj.spreadsheet = GOOGLE_SHEET_CONF["sheet_link"]

    data = [{
        'range': 'test!A3',
        'values': [['202304-00000']]
    }, {
        'range': 'test!J3',
        'values': [['http://yahoo2.com.tw']]
    }, {
        'range': 'test!A2',
        'values': [['nonono']]
    }]
    res = test_obj.update_range_data(data=data)
    print(res)


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


if __name__ == '__main__':
    get_sheet_data()
