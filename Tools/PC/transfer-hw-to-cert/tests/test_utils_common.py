import unittest

from utils.common import (
    is_valid_cid,
    is_valid_location,
    parse_location
)


class IsValidCIDTest(unittest.TestCase):

    def test_valid_cid(self):
        """ Check the valid CID
        """
        test_cases = [{
            'name': 'correct cid',
            'cid': '202303-23456'
        }, {
            'name': 'correct cid 2',
            'cid': '204312-39768'
        }]

        for case in test_cases:
            valid = is_valid_cid(case['cid'])
            self.assertEqual(
                True, valid,
                f"case: \'{case['name']}\' expects True but got False")

    def test_invalid_cid(self):
        """ Check the invalid CID
        """
        test_cases = [{
            'name': 'cid has too many numbers',
            'cid': '2023010-2956754'
        }, {
            'name': 'cid contains non-numeric character',
            'cid': '2023@k-2okhel'
        }, {
            'name': 'no hyphen in cid',
            'cid': '20230329123'
        }, {
            'name': 'cid not starts with 20',
            'cid': '302303-29123'
        }, {
            'name': 'cid not in 12 month',
            'cid': '202399-29123'
        }]

        for case in test_cases:
            valid = is_valid_cid(case['cid'])
            self.assertEqual(
                False, valid,
                f"case: \'{case['name']}\' expects False but got True")


class IsValidLocationTest(unittest.TestCase):
    def test_valid_location(self):
        """ Check the valid location
        """
        test_cases = [
            {
                'name': 'correct location',
                'location': 'TEL-L3-F24-S5-P1',
            },
            {
                'name': 'correct location 2',
                'location': 'TEL-L3-R01-S10-P0',
            },
            {
                'name': 'correct location 3',
                'location': 'TEL-L6-F03-S3-P3',
            },
            {
                'name': 'correct location 4',
                'location': 'TEL-L6-R02-S10-P1',
            }
        ]

        for case in test_cases:
            valid = is_valid_location(case['location'])
            self.assertEqual(
                True, valid,
                f"case: \'{case['name']}\' expects True but got False")

    def test_invalid_location(self):
        """ Check the invalid location
        """
        test_cases = [
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
            {
                'name': 'wrong shelf',
                'location': 'TEL-L6-F02-S9-P1',
                'expect_value': False
            }
        ]

        for case in test_cases:
            valid = is_valid_location(case['location'])
            self.assertEqual(
                False, valid,
                f"case: \'{case['name']}\' expects False but got True")


class ParseLocationTest(unittest.TestCase):
    def test_parse_valid_location(self):
        """ Parse the valid location
        """
        test_cases = [
            {
                'name': 'correct location',
                'location': 'TEL-L3-F24-S5-P1',
                'expected_result': {
                    'Lab': 'TEL-L3',
                    'Frame': 'F24',
                    'Shelf': '5',
                    'Partition': '1'
                },
            },
            {
                'name': 'correct location 1',
                'location': 'TEL-L6-R02-S10-P1',
                'expected_result': {
                    'Lab': 'TEL-L6',
                    'Frame': 'R02',
                    'Shelf': '10',
                    'Partition': '1'
                },
            },
        ]
        for case in test_cases:
            actual_result = parse_location(case['location'])
            expected_result = case['expected_result']
            self.assertEqual(expected_result, actual_result)

    def test_parse_invalid_location(self):
        """ Parse the invalid location
        """

        test_cases = [
            {
                'name': 'wrong start',
                'location': 'TE00L-L3-F24-S5-PK1',
            },
            {
                'name': 'empty location',
                'location': '',
            }
        ]

        for case in test_cases:
            actual_result = parse_location(case['location'])
            self.assertEqual({}, actual_result)


if __name__ == '__main__':
    unittest.main()
