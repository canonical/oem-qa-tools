import unittest
import io
import sys
from unittest.mock import patch

# Make sure mock_import must need to be imported before our own modules
from . import mock_import  # noqa: F401
from jira_card_handler import (
    get_table_content_from_a_jira_card,
    sanitize_row_data,
    is_valid_cid,
    is_valid_location,
    get_candidate_duts,
)
from .test_data.jira_card_handler_data import (INVALID_ROW_DATA,
                                               VALID_ROW_DATA,
                                               TABLE_GOLDEN_SAMPLE,
                                               VALID_RESULT_FROM_API,
                                               VALID_TABLE_CONTENT_FROM_API,
                                               EMPTY_TABLE_RESULT_FROM_API)


class GetTableContentFromAJiraCardTest(unittest.TestCase):

    @patch('jira_card_handler.api_get_jira_card')
    def test_get_non_exist_jira_card(self, mock_api_get_jira_card):
        """ Should raise exception while getting non-exist jira card
        """
        fake_key = 'fake-12345'
        jira_error_msg = '\'Issue does not exist or you do not have ' + \
            'permission to see it.\''

        # Second returned value doesn't matter
        mock_api_get_jira_card.return_value = [{
            'errorMessages': jira_error_msg
        }, '_']

        with self.assertRaisesRegex(
             Exception, 'Error: Failed to get the card \'{}\'. {}'.format(
                    fake_key, jira_error_msg)):
            get_table_content_from_a_jira_card(key=fake_key)

    @patch('jira_card_handler.api_get_jira_card')
    def test_get_non_hw_tranfser_jira_card(self, mock_api_get_jira_card):
        """ Should raise exception while getting non hw transfer jira card

            There's no table at 'Test result' field in non hw transfer Jira
            card. So this case makes sure we can handle we trigger wrong
            card  properly.
        """
        # supress stdout to hide print message
        suppress_text = io.StringIO()
        sys.stdout = suppress_text

        # Second returned value does matter, it's the Jira specifci code of
        # 'Test result' in Vic's Sandbox project
        mock_api_get_jira_card.return_value = [
            EMPTY_TABLE_RESULT_FROM_API, 'customfield_10186']

        with self.assertRaises(TypeError):
            get_table_content_from_a_jira_card(key='fake_key')

        # release stdout
        sys.stdout = sys.__stdout__

    @patch('jira_card_handler.api_get_jira_card')
    def test_can_get_valid_table_data(self, mock_api_get_jira_card):
        """ Should get valid data from table on hw transfer jira card
        """

        # Second returned value does matter, it's the Jira specifci code of
        # 'Test result' in Vic's Sandbox project
        mock_api_get_jira_card.return_value = [
            VALID_RESULT_FROM_API, 'customfield_10186']

        expected_result = VALID_TABLE_CONTENT_FROM_API

        test_table = get_table_content_from_a_jira_card(key='fake_key')
        self.assertCountEqual(expected_result, test_table)


class SanitizeRowDataTest(unittest.TestCase):

    def test_catches_invalid_data(self):
        """ Check if sanitize_row_data function can catch invalid data
        """
        expected_result = ['ABCmar-98765', '', 'Adc-L3-@34-S2-p0']
        is_valid, row = sanitize_row_data(data=INVALID_ROW_DATA)
        self.assertEqual(False, is_valid)
        self.assertCountEqual(expected_result, row)

    def test_catches_valid_data(self):
        """ Check if sanitize_row_data function can catch valid data
        """
        expected_result = ['202303-23456', '', 'TEL-L3-F24-S5-P1']
        is_valid, row = sanitize_row_data(data=VALID_ROW_DATA)
        self.assertEqual(True, is_valid)
        self.assertCountEqual(expected_result, row)

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


class GetCandidateDutsTest(unittest.TestCase):

    @patch('jira_card_handler.get_table_content_from_a_jira_card')
    def test_raise_exception_as_table_row_number_is_less_than_3(
            self, mock_get_table_content_from_a_jira_card):
        """ Should raise the exception and message if table's length < 3
        """
        # Mock as there're only two rows in table
        mock_get_table_content_from_a_jira_card.return_value = [1, 2]

        with self.assertRaisesRegex(
                Exception,
                'Error: expect more than 2 rows in table but got 2'):
            get_candidate_duts(key='any')

    @patch('jira_card_handler.get_table_content_from_a_jira_card')
    def test_tell_valid_and_invalid_result(
            self, mock_get_table_content_from_a_jira_card):
        """ Should tell the valid and invalid results based on table data
        """
        # Mock as there're only two rows in table
        mock_get_table_content_from_a_jira_card.return_value = \
            TABLE_GOLDEN_SAMPLE

        expected_result = {
            'valid': [['202303-23456', '', 'TEL-L3-F24-S5-P1']],
            'invalid': [['202305-24689', '', 'Adc-L3-@34-S2-p0'], ['', '', ''],
                        ['ABCmar-98765', '', 'TEL-L3-F24-S5-P2'],
                        ['309041-3345534', '', 'TEL-L3-F24-S5-P99'],
                        ['202303-28754', '', '']]
        }

        test_result = get_candidate_duts(key='any')

        self.assertEqual(expected_result, test_result)


if __name__ == '__main__':
    unittest.main()
