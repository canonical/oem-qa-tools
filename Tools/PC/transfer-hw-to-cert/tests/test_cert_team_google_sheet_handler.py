import unittest
from unittest.mock import patch

# Make sure mock_import must need to be imported before our own modules
from . import mock_import  # noqa: F401

from cert_team_google_sheet_handler import (
    is_valid_input_data,
    get_sheet_data
)


class IsValidInputDataTest(unittest.TestCase):
    def test_valid_data(self):
        """ Should return True if data is valid
        """
        data = [
            {
                'cid': '202304-28634',
                'location': 'TEL-L3-F23-S5-P2',
                'gm_image_link': 'http://fake-link/oem-share'
            },
            {
                'cid': '202304-28635',
                'location': 'TEL-L3-F23-S5-P1',
                'gm_image_link': ''
            },
        ]
        is_valid, invalid_list = is_valid_input_data(data)
        self.assertEqual(True, is_valid)
        self.assertEqual([], invalid_list)

    def test_missing_key(self):
        """ Should find data who misses key
        """
        data = [
            {
                'location': 'TEL-L3-F23-S5-P2',
                'gm_image_link': 'http://fake-link/oem-share'
            },
            {
                'cid': '202304-28635',
                'gm_image_link': ''
            },
            {
                'location': 'TEL-L3-F23-S5-P2',
                'cid': '202304-28635',
            },
            {
                'cid': '202304-28635',
            },
        ]

        expected_invalid_list = data

        is_valid, invalid_list = is_valid_input_data(data)
        self.assertEqual(False, is_valid)
        self.assertEqual(expected_invalid_list, invalid_list)

    def test_find_out_wrong_cid(self):
        """ Should get the data which has wrond CID
        """
        data = [
            {
                'cid': '303304-29abc',
                'location': 'TEL-L3-F23-S5-P2',
                'gm_image_link': 'http://fake-link/oem-share'
            },
            {
                'cid': '202304-28635',
                'location': 'TEL-L3-F23-S5-P1',
                'gm_image_link': ''
            },
        ]

        expected_invalid_list = [data[0]]

        is_valid, invalid_list = is_valid_input_data(data)

        self.assertEqual(False, is_valid)
        self.assertCountEqual(expected_invalid_list, invalid_list)

    def test_find_out_wrong_location(self):
        """ Should get the data which has wrond Location
        """
        data = [
            {
                'cid': '203304-29342',
                'location': 'TEL-F23-S5-P2',
                'gm_image_link': 'http://fake-link/oem-share'
            },
            {
                'cid': '202304-28635',
                'location': 'TEL-L3-F23-S5-P1',
                'gm_image_link': ''
            },
        ]

        expected_invalid_list = [data[0]]

        is_valid, invalid_list = is_valid_input_data(data)

        self.assertEqual(False, is_valid)
        self.assertCountEqual(expected_invalid_list, invalid_list)


class GetSheetDataTest(unittest.TestCase):
    @patch('cert_team_google_sheet_handler.create_google_sheet_instance')
    @patch(
        'cert_team_google_sheet_handler.GOOGLE_SHEET_CONF',
        {'tables': ['test-TEL-L5']}
    )
    def test_generate_customized_data(self, mock_gs_instance):
        """ Should generate the customized data
        """
        expected_data = {
            'test-TEL-L5': {
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
                    'TEL-L5-R01-S3-P0': {
                        'CID': '',
                        'Certified_OEM_Image': 'http://fake123.com',
                        'row_index': 3
                    }
                }
            }
        }

        mock_gs_obj = mock_gs_instance()
        mock_gs_obj.get_range_data.side_effect = [
            [
                [
                    'CID', 'MAC', 'Controller_MAC', 'Provision', 'Power',
                    'Device_ID', 'TF_Queue', 'Customized_Agent_Config',
                    'Advertised', 'Certified_OEM_Image', 'Username_OEM',
                    'Password_OEM', 'SRU_Pool', 'IP', 'PDU_IP', 'PDU_Outlet',
                    'Lab', 'Frame', 'Shelf', 'Partition', 'Eth_Port', 'Switch',
                    'POE_Port', 'POE_Switch', '2nd_Eth_Usage', 'Note'
                ]
            ],
            [
                [
                    '202112-39487', '00:e0:4d:3a:71:18', '', 'noprovision',
                    'raritan', 'aaeon-sse-opti-c29832', '', '', '', '',
                    'ubuntu', 'insecure', '', '10.102.160.11',
                    '10.102.196.101', '5', 'TEL-L5', 'F01', '1', '1', '1',
                    'TEL-L5-framesw01', '1', 'TEL-L5-frameswpoe01'
                ],
                [
                    '', '', '', 'maas_uefi', 'raritan', '', '', '', '',
                    'http://fake123.com', '', '', '', '10.102.160.13',
                    '10.102.196.101', '6', 'TEL-L5', 'F01', '1', '2', '2',
                    'TEL-L5-framesw01', '2', 'TEL-L5-frameswpoe01'
                ]
            ]
        ]
        actual_result = get_sheet_data()

        self.assertCountEqual(expected_data, actual_result)
