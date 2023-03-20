import unittest

from create_qa_jira_card import combine_duplicate_tag

from .test_data.data_combine_duplicate_tag import (
    somerville_rts_raw_data,
    somerville_prts_raw_data
)


class CreateQaJiraCardTest(unittest.TestCase):
    def test_combine_duplicate_tag_somerville_rts(self):
        """ Check the combine_duplicate_tag can properly handle the rts data

            For somerville project, we expect the records who have same
            value of platform_tag should be combined together as one record
            in rts milestone. 
        """
        primary_key = "platform_tag"
        excepted_result = {
            "rts": [
                {
                    "status": "in-flight",
                    "pm": "pm1",
                    "fe": "fe1",
                    "swe": "swe1",
                    "qa": "qa1",
                    "bug_link": "https://bugs.launchpad.net",
                    "start_date": ["2022-09-14", "2022-12-08", ""],
                    "end_date": ["2022-09-22", "2022-12-16", ""],
                    "platform_name": ["Galio 16 Haha", "Galio 15 Haha"],
                    "product_name": ["G16 7777", "G15 5555"],
                    "platform_tag": "jellyfish-gardevoir"
                },
                {
                    "status": "in-flight",
                    "pm": "pm2",
                    "fe": "fe2",
                    "swe": "",
                    "qa": "",
                    "bug_link": "https://bugs.launchpad.net",
                    "start_date": ["2022-12-21", "2023-02-10", "2023-03-09"],
                    "end_date": ["2022-12-30", "2023-02-24", "2023-03-23"],
                    "platform_name": ["MAYA BAY 333"],
                    "product_name": ["Precision 6688"],
                    "platform_tag": "jellyfish-muk"
                }
            ]
        }

        output = combine_duplicate_tag(somerville_rts_raw_data, primary_key)
        self.assertDictEqual(output, excepted_result)

    def test_combine_duplicate_tag_somerville_prts(self):
        """ Check the combine_duplicate_tag can properly handle the prts data

            For somerville project, we expect the records who have same
            value of platform_tag should NOT be combined together as one record
            in prts milestone. 
        """
        primary_key = "platform_tag"
        excepted_result = {
            "prts": [
                {
                    "status": "in-flight",
                    "pm": "pm1",
                    "fe": "",
                    "swe": "swe1",
                    "qa": "qa1",
                    "bug_link": "https://bugs.launchpad.net",
                    "request": "Fix rear audio port",
                    "request_date": "2023-01-16",
                    "start_date": ["2023-03-10", "", ""],
                    "end_date": ["2023-03-17", "", ""],
                    "platform_name": ["Dolphin N"],
                    "platform_tag": "fossa-davos-adl"
                },
                {
                    "status": "in-flight",
                    "pm": "pm1",
                    "fe": "",
                    "swe": "swe1",
                    "qa": "qa1",
                    "bug_link": "https://bugs.launchpad.net",
                    "request": "Fix rear audio port",
                    "request_date": "2023-01-16",
                    "start_date": ["2023-03-10", "", ""],
                    "end_date": ["2023-03-17", "", "" ],
                    "platform_name": ["Dolphin V MT"],
                    "platform_tag": "fossa-davos-adl"
                }
            ]
        }

        output = combine_duplicate_tag(somerville_prts_raw_data, primary_key)
        self.assertDictEqual(output, excepted_result)


if __name__ == '__main__':
    unittest.main()
