'''
    CQT Jira Board Handler
'''

import json

from Jira.apis.base import JiraAPI


def get_content_from_a_jira_card(key: str) -> dict:
    """ Get the content from the 'Test Results' field
        in a specific Jira card.

        @param:key, the key of jira card. e.g. CQT-1234

        @return, a dictionary contains gm_image_link, qa_launchpad_id and
                 table list. Please see the value of
                 'VALID_CONTENT_FROM_API' in tests/testdata
    """
    # Get the content of specific Jira card via API
    response, test_result_field_id = api_get_jira_card(key)
    if 'errorMessages' in response:
        print(response['errorMessages'][0])
        raise Exception(
            f"Error: Failed to get the card '{key}'. "
            f"{response['errorMessages'][0]}"
        )

    # Check if only one issue we got
    if len(response['issues']) != 1:
        raise Exception(
            f"Error: expect only 1 jira issue "
            f"but got {response['issues']} issues"
        )

    # Index is 0 because we search the Jira card by key,
    # only one issue is expected.
    # By design, the "Description" field is the default field
    # in each Jira card.
    # By design, the "Test Results" field is the default field
    # in each Jira card on CQT Jira project.
    description_field = response['issues'][0]['fields']['description']
    assignee_info = response['issues'][0]['fields'].get('assignee', {})
    assignee_id = assignee_info.get('accountId', '')
    test_result_field = response['issues'][0]['fields'][test_result_field_id]

    # Return dictionary
    re_dict = {
        'description_original_data': description_field,
        'assignee_original_id': assignee_id,
        'gm_image_link': '',
        'table': []
    }

    # Retrieve candidate DUT info from table
    try:
        table_idx = None
        for idx in range(len(test_result_field['content'])):
            # Find the index fo 'table' dict in the content list
            if 'type' in test_result_field['content'][idx] and \
                    test_result_field['content'][idx]['type'] == 'table':
                table_idx = idx
                break
        # Get the content list from table dict
        table_content = test_result_field['content'][table_idx]['content']
        re_dict['table'] = table_content
    except Exception as e:
        print(e)
        raise Exception(
            f"Error: Failed to get the table content from card '{key}'")

    # Get the link of gm image
    try:
        if len(description_field['content']):
            for idx in range(len(description_field['content'][0]['content'])):
                c = description_field['content'][0]['content'][idx]
                # Find the name first
                if 'text' in c and c['text'].strip() == 'GM Image Path:':
                    # The link will be in the next content if it's not empty
                    # value on Jira card
                    link = description_field['content'][0]['content'][idx+1]
                    if 'attrs' in link['marks'][0]:
                        # attrs could be one of href or url
                        attr_type = ['href', 'url']
                        for at in attr_type:
                            if at in link['marks'][0]['attrs']:
                                re_dict['gm_image_link'] = \
                                    link['marks'][0]['attrs'][at]
                                break
                        break
    except Exception as e:
        print(e)
        # Non mandatory field
        # TODO: Need a way to notify us instead of stdout
        print(
            f"Warning: Failed to get the GM Image Path from card '{key}'")

    return re_dict


def api_get_jira_card(key: str) -> tuple[dict, str]:
    """ Get the content of specific Jira card via API

        @param:key, the key of jira card. e.g. CQT-1234

        @return
            @parsed, the respone returned from Jira API.
            @field, the 'Test reulst' field in specific Jira project.
    """
    jira_api = JiraAPI()
    payload = {
        'jql':
        f"project = {jira_api.jira_project['key']} AND issuekey = \"{key}\"",
        'fields': [
            'description',
            'assignee',
            jira_api.jira_project['card_fields']['Test Results']
        ],
    }
    response = jira_api.get_issues(payload=payload)
    parsed = json.loads(response.text)

    # By design, the "Test Results" field is the default field
    # in each Jira card on QA's Jira project
    return parsed, jira_api.jira_project['card_fields']['Test Results']


def retrieve_row_data(data: dict) -> list:
    """ Retrieve the data from table

        @param:data, it's a row record in Jira table. Please see the
                    VALID_ROW_DATA to know its structure.

        @return
            @row, a list in ['cid', 'location'] format
    """
    row = []

    # Retrieve (CID, Location) and append them to row list
    for i in data['content']:
        if i['content'][0]['content']:
            row.append(i['content'][0]['content'][0]['text'].strip())
        else:
            row.append('')

    return row


def get_candidate_duts(key: str) -> dict:
    """ Get the candidate DUT(s) from specific Jira Card's table

        @param:key, the key of jira card. e.g. CQT-1234

        @return
        {
            'certify_planning_link': '',
            'gm_image_link': '',
            'qa_launchpad_id': '',
            'data': [{
                'cid': '202212-12345',
                'location:': 'TEL-L3-F24-S5-P1'
            }, {
                'cid': '202212-123xcc',
                'location:': ''
            }]
        }
    """
    content = get_content_from_a_jira_card(key)

    # Return dictionary
    re_dict = {
        'data': [],
        'description_original_data': content['description_original_data'],
        'assignee_original_id': content['assignee_original_id'],
        'gm_image_link': content['gm_image_link'],
    }

    # Sanitize each dut
    #
    # Why start from 2?
    # Ans:
    #   According to our Jira template
    #     - idx 0 is table's header
    #     - idx 1, aka row 1, is the example placeholder
    #   So the real data should be started from idx 2
    if len(content['table']) < 3:
        raise Exception(
            f"Error: expect more than 2 rows in table "
            f"but got {len(content['table'])}"
        )

    for i in range(2, len(content['table'])):
        data = retrieve_row_data(content['table'][i])
        # Filter out empty row. data[0] is cid, data[1] is location
        if not data[0] and not data[1]:
            continue
        tmp_d = {
            'cid': data[0],
            'location': data[1],
        }
        re_dict['data'].append(tmp_d)

    return re_dict
