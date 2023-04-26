from utils.common import (
    is_valid_cid,
    is_valid_location,
    read_json_config,
    parse_location
)

from GoogleSheet.google_sheet_api import GoogleSheetOperator

"""
    This python script handles the procedure of filling the DUT's information
    in the Cert Team's Google Sheet.
"""

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
                        'cid': '202304-12345',
                        'location': 'TEL-L3-F24-S5-P2'
                        'gm_image_link': ''
                    },
                    {
                        'cid': '202311-12346',
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
                'row_index': idx + offset,
                'CID': v[columns['CID']],
                'Certified_OEM_Image': v[columns['Certified_OEM_Image']]
            }
        sheet_data[t]['indexed_table'] = indexed_table

    return sheet_data


def are_candidated_sheet_cells_empty(
        data: list[dict], sheet_data: dict) -> tuple[bool, list]:
    """ Check the cells are empty on Cert Lab Google Sheet
        Currently, this function checks the value of CID and
        Certified_OEM_Image

        @param:data, a list contains the bunch of dictionary data, each
                    data has the following keys, cid, location and the
                    gm_image_link
                    e.g.
                        data = [
                            {
                                'cid': '202312-12345',
                                'location': 'TEL-L3-F24-S5-P2',
                                'gm_image_link': ''
                            },
                            {
                                'cid': '202302-12346',
                                'location': 'TEL-L3-F23-S5-P2',
                                'gm_image_link': 'http://oem-share'
                            }
                        ]
        @param:sheet_data, a dictionary which is from get_sheet_data function

        @return
            bool: True if all candidated cells are empty, otherwise False
            list: non empty list. It shows all record whose CID cell is empty
    """
    all_empty = True
    non_empty_list = []
    for d in data:
        lab = parse_location(d['location']).get('Lab', None)
        if not lab or lab not in sheet_data:
            err_msg = 'Error: Lab \'{}\' is not in indexed table'.format(lab)
            raise Exception(err_msg)
        # get the indexed table of specific lab
        indexed_table = sheet_data[lab]['indexed_table']
        # check the CID cell is not empty
        if indexed_table[d['location']]['CID']:
            all_empty = False
            message = 'try to fill \'{}\' in the CID cell but there\'s '\
                '\'{}\' occupies the cell'
            non_empty_list.append({
                'message': message.format(
                    d['cid'],
                    indexed_table[d['location']]['CID']
                ),
                'row_index': indexed_table[d['location']]['row_index'],
                'location': d['location']
            })

    return all_empty, non_empty_list


def fill_in_google_sheet(data: list[dict], sheet_data: dict) -> bool:
    """ Fill the data in the Google Sheet

        @param:data, a list contains the bunch of dictionary data, each
                    data has the following keys, cid, location and the
                    gm_image_link
                    e.g.
                        data = [
                            {
                                'cid': '202312-12345',
                                'location': 'TEL-L3-F24-S5-P2',
                                'gm_image_link': ''
                            },
                            {
                                'cid': '202302-12346',
                                'location': 'TEL-L3-F23-S5-P2',
                                'gm_image_link': 'http://oem-share'
                            }
                        ]
        @param:sheet_data, a dictionary which is from get_sheet_data function
    """
    gs_obj = create_google_sheet_instance()
    batch_update_data = []

    for d in data:
        table = parse_location(d['location'])['Lab']
        headers = sheet_data[table]['headers']
        indexed_table = sheet_data[table]['indexed_table']
        row_index = indexed_table[d['location']]['row_index']
        cid_column_chr = chr(65 + headers['CID'])
        gm_image_link_chr = chr(65 + headers['Certified_OEM_Image'])
        # append cid data who is to be filled in
        cid_data = {
            'range': f'{table}!{cid_column_chr}{row_index}',
            'values': [[d['cid']]]
        }
        batch_update_data.append(cid_data)

        # append gm_image_link_data data who is to be filled in
        gm_image_link_data = {
            'range': f'{table}!{gm_image_link_chr}{row_index}',
            'values': [[d['gm_image_link']]]
        }
        batch_update_data.append(gm_image_link_data)

    res = gs_obj.update_range_data(data=batch_update_data)
    print(res)


def update_cert_lab_google_sheet(data: list[dict]) -> dict:
    """ Fill the DUT information to the Cert Lab Google Sheet

        @param:data, a list contains the bunch of dictionary data, each
                    data has the following keys, cid, location and the
                    gm_image_link
            e.g.
                data = [
                    {
                        'cid': '202312-12345',
                        'location': 'TEL-L3-F24-S5-P2',
                        'gm_image_link': ''
                    },
                    {
                        'cid': '202302-12346',
                        'location': 'TEL-L3-F23-S5-P2',
                        'gm_image_link': 'http://oem-share'
                    }
                ]
        @return
            bool: True if all data are valid, otherwise False
            list: invalid list. It shows all invalid data in a list
    """
    # Sanitize data
    valid, invalid_list = is_valid_input_data(data)

    if not valid:
        err_msg = 'Error: input data is invalid. Invalid data list: {}'.format(
            invalid_list)
        raise Exception(err_msg)

    # Get Google Sheet data
    sheet_data = get_sheet_data()

    # Check those cells are empty
    empty, non_empty_list = are_candidated_sheet_cells_empty(
        data,
        sheet_data
    )

    if not empty:
        err_msg = 'Error: some cells are not empty. Non empty list: {}'.format(
            non_empty_list)
        raise Exception(err_msg)

    # fill the data to google sheet
    response = fill_in_google_sheet(data, sheet_data)
    return response


if __name__ == '__main__':
    # get_sheet_data()
    data = [
        {
            'cid': '20230405-12345',
            'location': 'TEL-L3-F24-S5-P2',
            'gm_image_link': '',
            'sku': ''
        },
        {
            'cid': '20230405-12346',
            'location': 'TEL-L5-F20-S1-P1',
            'gm_image_link': 'http://oem-share'
        }
    ]
    update_cert_lab_google_sheet(data)
