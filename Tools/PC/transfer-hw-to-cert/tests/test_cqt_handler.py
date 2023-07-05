import unittest
import io
import sys
from unittest.mock import patch

# Make sure mock_import must need to be imported before our own modules
from . import mock_import  # noqa: F401
from handlers.cqt_handler import (
    get_content_from_a_jira_card,
    retrieve_row_data,
    get_candidate_duts,
)
from .test_data.jira_card_handler_data import (
                                               VALID_ROW_DATA,
                                               VALID_CONTENT_FROM_API,
                                               VALID_RESULT_FROM_API,
                                               EMPTY_TABLE_RESULT_FROM_API)


class GetContentFromAJiraCardTest(unittest.TestCase):

    @patch('handlers.cqt_handler.api_get_jira_card')
    def test_get_non_exist_jira_card(self, mock_api_get_jira_card):
        """ Should raise exception while getting non-exist jira card
        """
        fake_key = 'fake-12345'
        jira_error_msg = 'Issue does not exist or you do not have ' + \
            'permission to see it.'

        # Second returned value doesn't matter
        mock_api_get_jira_card.return_value = [{
            'errorMessages': [jira_error_msg]
        }, '_']

        with self.assertRaisesRegex(
            Exception,
            f"Error: Failed to get the card {fake_key}. {jira_error_msg}"
        ):
            get_content_from_a_jira_card(key=fake_key)

    @patch('handlers.cqt_handler.api_get_jira_card')
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

        # with self.assertRaises(TypeError):
        #     get_content_from_a_jira_card(key='fake_key')
        fake_key = 'fake-2345'
        with self.assertRaisesRegex(
            Exception,
            f"Error: Failed to get the table content from card {fake_key}"
        ):
            get_content_from_a_jira_card(key=fake_key)

        # release stdout
        sys.stdout = sys.__stdout__

    @patch('handlers.cqt_handler.api_get_jira_card')
    @patch('handlers.cqt_handler.get_jira_members')
    def test_can_get_valid_content(
        self,
        mock_get_jira_members,
        mock_api_get_jira_card
    ):
        """ Should get valid data from hw transfer jira card
        """

        # Second returned value does matter, it's the Jira specific code of
        # 'Test result' in Vic's Sandbox project
        mock_api_get_jira_card.return_value = [
            VALID_RESULT_FROM_API, 'customfield_10186']

        mock_get_jira_members.return_value = {
            'fake-valid-launchpad_id': {}
        }

        expected_result = VALID_CONTENT_FROM_API

        test_table = get_content_from_a_jira_card(key='fake_key')
        self.assertCountEqual(expected_result, test_table)


class RetrieveRowDataTest(unittest.TestCase):

    def test_retrieve_row_data(self):
        """ Check if retrieve_row function can get data frm table and return
            it as a list for a row
        """
        expected_result = ['202303-23456', 'TEL-L3-F24-S5-P1']
        row = retrieve_row_data(data=VALID_ROW_DATA)
        self.assertCountEqual(expected_result, row)


class GetCandidateDutsTest(unittest.TestCase):

    @patch('handlers.cqt_handler.get_content_from_a_jira_card')
    def test_raise_exception_as_table_row_number_is_less_than_3(
            self, mock_get_content_from_a_jira_card):
        """ Should raise the exception and message if table's length < 3
        """
        # Mock as there're only two rows in table
        mock_get_content_from_a_jira_card.return_value = {
            'table': [1, 2],
            'gm_image_link': '',
            'qa_launchpad_id': ''
        }

        with self.assertRaisesRegex(
                Exception,
                'Error: expect more than 2 rows in table but got 2'):
            get_candidate_duts(key='any')

    @patch('handlers.cqt_handler.get_content_from_a_jira_card')
    def test_get_expected_result(
            self, mock_get_content_from_a_jira_card):
        """ Should get the expected results based on table data
        """
        # Mock as there're only two rows in table
        mock_get_content_from_a_jira_card.return_value = \
            VALID_CONTENT_FROM_API

        expected_result = {
            'gm_image_link': 'https://oem-share.canonical.com/partners/sutton/share/bachman/sutton-workstation-2022-10-07/pc-sutton-bachman-focal-amd64-X00-20221004-139.iso',  # noqa: E501
            'qa_launchpad_id': 'fake-valid-launchpad_id',
            "data": [
                {
                    "cid": "202305-24689",
                    "location": "Adc-L3-@34-S2-p0"
                },
                {
                    "cid": "ABCmar-98765",
                    "location": "TEL-L3-F24-S5-P2"
                },
                {
                    "cid": "309041-3345534",
                    "location": "TEL-L3-F24-S5-P99"
                },
                {
                    "cid": "202303-23456",
                    "location": "TEL-L3-F24-S5-P2"
                },
                {
                    "cid": "202303-28754",
                    "location": ""
                }
            ]
        }

        test_result = get_candidate_duts(key='any')

        self.assertEqual(expected_result, test_result)


if __name__ == '__main__':
    unittest.main()
