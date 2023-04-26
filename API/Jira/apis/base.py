import requests
import json
import os
import pathlib
import copy
from requests.auth import HTTPBasicAuth

from Jira.utils.logging_utils import init_logger, get_logger
# logger
init_logger()
logger = get_logger(__name__)

JIRA_DIR_PATH = os.path.split(pathlib.Path(__file__).parent.resolve())[0]
CONF_DIR_PATH = os.path.join(JIRA_DIR_PATH, 'configs')
JIRA_CONF_DIR_PATH = os.path.join(CONF_DIR_PATH, 'jira_config')


class JiraAPI:
    def __init__(
            self,
            base_url='https://warthogs.atlassian.net',
            jira_api_path='rest/api/3'
    ):
        self._base_url = base_url
        self._jira_api_path = jira_api_path
        with open(os.path.join(JIRA_CONF_DIR_PATH, 'project.json')) as f:
            self._jira_project = json.load(f)

        with open(os.path.join(JIRA_CONF_DIR_PATH, 'api_token.json')) as f:
            self._api_token = json.load(f)

    @property
    def base_url(self):
        return self._base_url

    @property
    def jira_api_path(self):
        return self._jira_api_path

    @property
    def jira_project(self):
        return self._jira_project

    @property
    def api_token(self):
        return self._api_token

    def _request(self, http_method='GET', url='', payload={}):
        """ Wrapper for requests
        """
        auth = HTTPBasicAuth(
            self.api_token['email'], self.api_token['api_token'])

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            payload = json.dumps(payload)
            response = requests.request(http_method,
                                        url,
                                        data=payload,
                                        headers=headers,
                                        auth=auth)
            if response.status_code < 200 or response.status_code > 299:
                response.raise_for_status()
        except Exception as e:
            logger.error(e)
            logger.error('*' * 50)
            logger.error(payload)
            logger.error('*' * 50)
        finally:
            return response

    def update_epic(self, epic, issues_id=[], **kwargs):
        """ [Workaround] Update the epic of issues

            Parameters:
                epic {string}: Should field in the name of epic.
                issues_id {list}: The id number of issues
                    e.g. [73438, 73439]
        """
        epic_id = self._jira_project['epic'][epic]
        url = '{}/rest/internal/simplified/1.0/projects/{}/issues/{}/children'
        payload = {'issueIds': issues_id}
        response = self._request(
            "POST",
            url=url.format(self._base_url, self._jira_project['id'], epic_id),
            payload=payload
        )
        return response

    def get_issues(self, **kwargs):
        """ Get one or more issues
        """
        api_endpoint = "{}/{}/search".format(
            self._base_url, self._jira_api_path)
        payload = kwargs['payload']
        response = self._request("POST", url=api_endpoint, payload=payload)
        return response

    def create_an_issue(self, **kwargs):
        """ Create an issue
        """
        api_endpoint = "{}/{}/issue".format(
            self._base_url, self._jira_api_path)
        payload = kwargs['payload']
        response = self._request("POST", url=api_endpoint, payload=payload)
        return response

    def create_issues(self, **kwargs):
        """ Create bulk issues
        """
        api_endpoint = "{}/{}/issue/bulk".format(
            self._base_url, self._jira_api_path)
        payload = kwargs['payload']
        response = self._request("POST", url=api_endpoint, payload=payload)

        return response

    def create_jira_fields_template(self, task_type='Task'):
        """
            Parameters:
                task_type {str}: The type of Jira Card
                                 Should be 'Story' or 'Task'
        """
        fields = {
            'project': {
                'id': self._jira_project['id']
            },
            'issuetype': {
                'id': self._jira_project['issue_type'][task_type]
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

        return fields

    def create_link_issue_content(
        self, issuelinks_type='10003', target_issues=[]
    ):
        """
            Params:
                issuelinks_type {str}: the type of link between issues
                    10003: means "relates to"
                target_issues {list}: the tasks we want to link
                    ex:
                        [{'key': 'VS-1234'}, {'key': 'VS-3453'}]
        """
        update = {
            'issuelinks': [{
                'add': {
                    'values': [{
                        'type': {
                            'id': issuelinks_type
                        },
                        'inwardIssues': target_issues
                    }]
                }
            }]
        }
        return update

    def create_paragraph_content(self, desired_content=[]):
        """ Used to generate the content of description from desired_content

            Parameters:
                desired_content {list}: A list contains one or more tuples
                    tuple format: (key, value, type, link_text)
                        e.g.
                            1. Only title without any value
                                ('BIOS', '')
                            2. Title with value
                                ('Platform Tag', platform_tag)
                            3. Title with value which is link type
                                (
                                    'Launchpad Bug List',
                                    bug_list_link,
                                    'link',
                                    'Bug List'
                                )

            return {dict}
                e.g.
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'Model Name: Pr 7960'},
                            {'type': 'hardBreak'},
                            {'type': 'text', 'text': 'Engineer Plan: '},
                            {'type': 'hardBreak'}
                        ]
                    }
        """
        # fixed syntax for Jira
        jira_hard_break = {"type": "hardBreak"}
        new_content = []

        for key, value, *t in desired_content:
            if t and t[0] == 'link':
                new_content.append({
                    'type': 'text',
                    'text': '{}: '.format(key),
                    'marks': [{'type': 'strong'}]
                })
                new_content.append({
                    'type': 'text',
                    'text': t[-1],
                    'marks': [{
                        'type': 'link',
                        'attrs': {
                            'href': value
                        }
                    }]
                })
            else:
                new_content.append({
                    'type': 'text',
                    'marks': [{'type': 'strong'}],
                    'text': '{}: '.format(key)
                })
                if value:
                    new_content.append({
                        'type': 'text',
                        'text': value
                    })

            new_content.append(jira_hard_break)

        # return paragraph content
        rp = {
            'type': 'paragraph',
            'content': new_content
        }
        return rp

    def create_table_content(self, desired_table={}):
        """ Used to generate the table from desired_table
            e.g.
                desired_table = {
                    'attrs': {
                        'isNumberColumnEnabled': False,
                        'layout': 'default'
                    },
                    'headers': ['CID', 'SKU Name', 'Location'],
                    'row_contents': [
                        ('', '', '')
                    ]
                }

            Return example:
                {
                    "type": "table",
                    "attrs": {
                        "isNumberColumnEnabled": false,
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
                                                    "text": "CID",
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
                                                    "text": "SKU Name",
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
                                                    "text": "Location",
                                                    "marks": [
                                                        {
                                                            "type": "strong"
                                                        }
                                                    ]
                                                }
                                            ]
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
                        }
                    ]
                }
        """
        table = {
            'attrs': {},
            'type': 'table',
            'content': []
        }

        table_row = {
            'type': 'tableRow',
            'content': []
        }

        table_header = {
            'type': 'tableHeader',
            'attrs': {},
            'content': []
        }

        table_cell = {
            'type': 'tableCell',
            'attrs': {},
            'content': [
                {
                    'type': 'paragraph',
                    'content': []
                }
            ]
        }

        t = copy.deepcopy(table)
        t['attrs'] = desired_table['attrs']

        if 'headers' in desired_table:
            tr = copy.deepcopy(table_row)
            for h in desired_table['headers']:
                p = {
                    'type': 'paragraph',
                    'content': [
                        {
                            'marks': [{'type': 'strong'}],
                            'text': '{}'.format(h),
                            'type': 'text'
                        }
                    ]
                }
                th = copy.deepcopy(table_header)
                th['content'].append(p)
                tr['content'].append(th)

            # append header row to table
            t['content'].append(tr)

            # handle content rows
            for each_row in desired_table['row_contents']:
                tr = copy.deepcopy(table_row)
                for each_cell in each_row:
                    cell = copy.deepcopy(table_cell)
                    # each_cell is not empty
                    if each_cell:
                        cell['content'][0]['content'].append({
                            'type': 'text',
                            'text': '{}'.format(each_cell)
                        })
                    tr['content'].append(cell)
                t['content'].append(tr)

        return t

    def add_comment_to_issue(self, keyOrID='', comment_data={}):
        """ Add a comment to an issue

            Parameters:
                keyOrID {str}: The key or ID of Jira issue
                    e.g. key -> CQT-1234
                comment_data {dict}: The valid format of Jira comment
                    ref:
                        https://developer.atlassian.com/cloud/jira/platform/
                        rest/v3/api-group-issue-comments/#api-rest-api-3-
                        issue-issueidorkey-comment-post
        """
        api_endpoint = "{}/{}/issue/{}/comment".format(
            self._base_url, self._jira_api_path, keyOrID)
        payload = {'body': comment_data}
        response = self._request('POST', url=api_endpoint, payload=payload)

        return response


def get_jira_members():
    """ Get the members who have the permission to access the Jira Project

        Return {dict}:
        {
            "<launchpad_id>": {
                "jira_uid": "<70982:1643143b-15dc-42a7-ab31-4560609c4ad3>"
            },
        }
    """
    with open(os.path.join(JIRA_CONF_DIR_PATH, 'members.json')) as f:
        members = json.load(f)
        return members
