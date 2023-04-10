import unittest

from utils.common import (
    is_valid_cid,
    is_valid_location,
    parse_location
)


class IsValidCIDTest(unittest.TestCase):

    def test_is_valid_cid(self):
        """ Check if the format of cid is wrong
        """
        test_cases = [{
            'name': 'correct cid',
            'cid': '202303-23456',
            'expect_value': True
        }, {
            'name': 'correct cid 2',
            'cid': '204312-39768',
            'expect_value': True
        }, {
            'name': 'cid has too many numbers',
            'cid': '2023010-2956754',
            'expect_value': False
        }, {
            'name': 'cid contains non-numeric character',
            'cid': '2023@k-2okhel',
            'expect_value': False
        }, {
            'name': 'no hyphen in cid',
            'cid': '20230329123',
            'expect_value': False
        }, {
            'name': 'cid not starts with 20',
            'cid': '302303-29123',
            'expect_value': False
        }, {
            'name': 'cid not in 12 month',
            'cid': '202399-29123',
            'expect_value': False
        }]

        for case in test_cases:
            valid = is_valid_cid(case['cid'])
            self.assertEqual(
                case['expect_value'], valid,
                'case: \'{}\' expects {} but got {}'.format(
                    case['name'], case['expect_value'], valid))


class IsValidLocationTest(unittest.TestCase):
    def test_is_valid_location(self):
        """ Check if the format of location is wrong
        """
        test_cases = [
            {
                'name': 'correct location',
                'location': 'TEL-L3-F24-S5-P1',
                'expect_value': True
            },
            {
                'name': 'correct location 2',
                'location': 'TEL-L3-R01-S10-P0',
                'expect_value': True
            },
            {
                'name': 'wrong start',
                'location': 'ATEL-L3-R01-S10-P0',
                'expect_value': False
            },
            {
                'name': 'missing L',
                'location': 'TEL-F24-S5-P1',
                'expect_value': False
            },
            {
                'name': 'missing F',
                'location': 'TEL-L5-S5-P1',
                'expect_value': False
            },
            {
                'name': 'missing S',
                'location': 'TEL-L5-F02-P1',
                'expect_value': False
            },
            {
                'name': 'missing P',
                'location': 'TEL-L5-F02-S1',
                'expect_value': False
            },
            {
                'name': 'wrong partition (only accept 0 or 1)',
                'location': 'TEL-L5-F02-S1-P7',
                'expect_value': False
            },
            {
                'name': 'lower alphabet',
                'location': 'tel-L5-F02-S1-P7',
                'expect_value': False
            },
        ]

        for case in test_cases:
            valid = is_valid_location(case['location'])
            self.assertEqual(
                case['expect_value'], valid,
                'case: \'{}\' expects {} but got {}'.format(
                    case['name'], case['expect_value'], valid))


class ParseLocationTest(unittest.TestCase):
    def test_parse_valid_location(self):
        """ Parse the valid location
        """
        actual_result = parse_location(location='TEL-L3-F24-S5-P1')
        expected_result = {
            'Lab': 'TEL-L3',
            'Frame': 'F24',
            'Shelf': '5',
            'Partition': '1'
        }
        self.assertCountEqual(expected_result, actual_result)

    def test_parse_invalid_location(self):
        """ Parse the invalid location
        """
        actual_result = parse_location(location='TE00L-L3-F24-S5-PK1')
        expected_result = {
            'Lab': '',
            'Frame': 'F24',
            'Shelf': '5',
            'Partition': ''
        }
        self.assertCountEqual(expected_result, actual_result)

    def test_parse_empty_location(self):
        """ Parse the invalid location
        """
        actual_result = parse_location(location='')
        expected_result = {
            'Lab': '',
            'Frame': '',
            'Shelf': '',
            'Partition': ''
        }
        self.assertCountEqual(expected_result, actual_result)


if __name__ == '__main__':
    unittest.main()
