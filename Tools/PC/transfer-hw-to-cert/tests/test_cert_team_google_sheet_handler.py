import unittest

from cert_team_google_sheet_handler import (
    is_valid_input_data
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
