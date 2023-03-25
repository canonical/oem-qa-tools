import unittest

from jira_card_handler import (
    sanitize_row_data,
    is_valid_cid,
    is_valid_location
)

from .test_data.jira_card_handler_data import (
    INVALID_DATA,
    VALID_DATA
)


# class GetCandidateDutFromJiraCardTest(unittest.TestCase):
#     def test_paramtere_key_is_wrong_type(self):
#         """ Check the parameter type must need to be string
#         """
#         for t in [123, ('c', 'd'), {'hola': 'canonical'}]:
#             self.assertRaises(TypeError, get_table_content_from_a_jira_card, t)

class SanitizeRowDataTest(unittest.TestCase):
    def test_catches_invalid_data(self):
        """ Check if sanitize_row_data function can catch invalid data
        """
        expect_result = ['ABCmar-98765', '', 'Adc-L3-@34-S2-p0']
        is_valid, row = sanitize_row_data(data=INVALID_DATA)
        self.assertEqual(False, is_valid)
        self.assertCountEqual(expect_result, row)

    def test_catches_valid_data(self):
        """ Check if sanitize_row_data function can catch valid data
        """
        expect_result = ['202303-23456', '', 'TEL-L3-F24-S5-P1']
        is_valid, row = sanitize_row_data(data=VALID_DATA)
        self.assertEqual(True, is_valid)
        self.assertCountEqual(expect_result, row)

    def test_is_valid_cid(self):
        """ Check if the format of cid is wrong
        """
        test_cases = [
            {
                'name': 'correct cid',
                'cid': '202303-23456',
                'expect_value': True
            },
            {
                'name': 'correct cid 2',
                'cid': '204312-39768',
                'expect_value': True
            },
            {
                'name': 'cid has too many numbers',
                'cid': '2023010-2956754',
                'expect_value': False
            },
            {
                'name': 'cid contains non-numeric character',
                'cid': '2023@k-2okhel',
                'expect_value': False
            },
            {
                'name': 'no hyphen in cid',
                'cid': '20230329123',
                'expect_value': False
            },
            {
                'name': 'cid not starts with 20',
                'cid': '302303-29123',
                'expect_value': False
            },
            {
                'name': 'cid not in 12 month',
                'cid': '202399-29123',
                'expect_value': False
            }
        ]

        for case in test_cases:
            valid = is_valid_cid(case['cid'])
            self.assertEqual(
                case['expect_value'],
                valid,
                'case: \'{}\' expects {} but got {}'.format(
                    case['name'], case['expect_value'], valid
                )
            )

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
                case['expect_value'],
                valid,
                'case: \'{}\' expects {} but got {}'.format(
                    case['name'], case['expect_value'], valid
                )
            )


if __name__ == '__main__':
    unittest.main()
