import unittest

from Jira.apis.base import JiraAPI


class JiraAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jira_api = JiraAPI()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_api_property(self):
        """ Check the properties of JiraAPI class are correct
        """
        self.assertEqual(
            self.jira_api.base_url, 'https://warthogs.atlassian.net')
        self.assertEqual(self.jira_api.jira_api_path, 'rest/api/3')
        
        dev_jira_project = {
            'id': '10350',
            'key': 'VS',
            'name': 'Vic\'s Sandbox',
            'issue_type': {
                'Task': '10635',
                'Story': '10634'
            },
            'epic': {
                'Somerville': '69110',
                'Stella': '69111',
                'Sutton': '69112',
                'Tooling & Process': '63215'
            },
            'card_fields': {
                'Test result': 'customfield_10186'
            }
        }
        self.assertDictEqual(self.jira_api.jira_project, dev_jira_project)

    def test_create_jira_fields_template(self):
        """ Check the most basic part of card's content is correct with those given ids

            The id of project and issuetype are mandatory value.
        """
        def expected_result_template(id_of_issue_type):
            """ Project id '10350' is for Vic's Jira project
            """
            return {
                'project': {
                    'id': '10350'
                },
                'issuetype': {
                    'id': f'{id_of_issue_type}'
                },
                'description': {
                    'type': 'doc',
                    'version': 1,
                    'content': []
                },
                'reporter': {
                    'id': ''
                },
                'labels': [],
            }

        tests = [
            # '10635' is the id of 'Task' in Vic's project
            {
                'issue_type': 'Task',
                'expected_result': expected_result_template('10635'),
            },
            # '10634' is the id of 'Story' in Vic's project
            {
                'issue_type': 'Story',
                'expected_result': expected_result_template('10634'),
            }
        ]
        for test in tests:
            self.assertDictEqual(
                self.jira_api.create_jira_fields_template(test['issue_type']),
                test['expected_result']
            )

    def test_create_paragraph_content(self):
        """ Check the format of paragraph matches the expected result
            Jira won't create the task with wrong paragraph format.

        """
        desired_content = [
            ('BIOS', 'V1234'),
            ('Tester', ''),
            ('Launchpad page', 'https://launchpad.net/', 'link', 'Launchpad'),
        ]

        expected_result = {
            'type': 'paragraph',
            'content': [
                {
                    'type': 'text',
                    'marks': [
                        {
                            'type': 'strong'
                        }
                    ],
                    'text': 'BIOS: '
                },
                {
                    'type': 'text',
                    'text': 'V1234'
                },
                {
                    'type': 'hardBreak'
                },
                {
                    'type': 'text',
                    'marks': [
                        {
                            'type': 'strong'
                        }
                    ],
                    'text': 'Tester: '
                },
                {
                    'type': 'hardBreak'
                },
                {
                    'type': 'text',
                    'text': 'Launchpad page: ',
                    'marks': [
                        {
                            'type': 'strong'
                        }
                    ]
                },
                {
                    'type': 'text',
                    'text': 'Launchpad',
                    'marks': [
                        {
                            'type': 'link',
                            'attrs': 
                                {
                                    'href': 'https://launchpad.net/'
                                }
                        }
                    ]
                },
                {
                    'type': 'hardBreak'
                }
            ]
        }

        self.assertDictEqual(
            self.jira_api.create_paragraph_content(desired_content),
            expected_result
        )

    def test_create_table_content(self):
        """ Check the format of table matches the expected result
            Jira won't create the task with wrong table format.
        """
        desired_table = {
            'attrs': {
                'isNumberColumnEnabled': False,
                'layout': 'default'
            },
            'headers': ['Header1', 'Fake Header2'],
            'row_contents': [
                ('', ''),
                ('cell-1-0', ''),
                ('', 'cell-2-1')
            ]
        }
        expected_result = {
            "type": "table",
            "attrs": {
                "isNumberColumnEnabled": False,
                "layout": "default"
            },
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableHeader",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Header1",
                                            "marks": [
                                                {
                                                    "type": "strong"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "tableHeader",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Fake Header2",
                                            "marks": [
                                                {
                                                    "type": "strong"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                    ]
                },
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": []
                                }
                            ]
                        },
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": []
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{
                                        "type": "text",
                                        "text": "cell-1-0",
                                    }]
                                }
                            ]
                        },
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": []
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": []
                                }
                            ]
                        },
                        {
                            "type": "tableCell",
                            "attrs": {},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{
                                        "type": "text",
                                        "text": "cell-2-1",
                                    }]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        self.assertDictEqual(
            self.jira_api.create_table_content(desired_table),
            expected_result
        )

if __name__ == '__main__':
    unittest.main()
