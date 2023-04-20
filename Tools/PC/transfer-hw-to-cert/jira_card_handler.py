import json

from Jira.apis.base import JiraAPI, get_jira_members
from utils.common import is_valid_cid, is_valid_location


def get_content_from_a_jira_card(key: str) -> dict:
    """ Get the content from the 'Test result' field in a specific Jira card.

        @param:key, the key of jira card. e.g. CQT-1234

        @return, a dictionary contains gm_image_link, qa_launchpad_id and
                 table list. Please see the value of
                 'VALID_CONTENT_FROM_API' in tests/testdata
    """
    # Get the content of specific Jira card via API
    response, test_result_field_id = api_get_jira_card(key)
    if 'errorMessages' in response:
        print(response['errorMessages'][0])
        err_msg = 'Error: Failed to get the card \'{}\'. {}'.format(
            key, response['errorMessages'][0])
        raise Exception(err_msg)

    # Check if only one issue we got
    if len(response['issues']) != 1:
        err_msg = 'Error: expect only 1 jira issue but got {} issues'.format(
            len(response['issues']))
        raise Exception(err_msg)

    # Index is 0 because we search the Jira card by key,
    # only one issue is expected.
    # By design, the "Description" field is the default field
    # in each Jira card.
    # By design, the "Test result" field is the default field
    # in each Jira card on CQT Jira project.
    description_field = response['issues'][0]['fields']['description']
    test_result_field = response['issues'][0]['fields'][test_result_field_id]

    # Return dictionary
    re_dict = {
        'gm_image_link': '',
        'qa_launchpad_id': '',
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
            f'Error: Failed to get the table content from card \'{key}\'')

    # Get QA launchpad ID
    try:
        for idx in range(len(test_result_field['content'][0]['content'])):
            c = test_result_field['content'][0]['content'][idx]
            # Find the name first
            if 'text' in c and c['text'].strip() == 'QA:':
                # The launchpad id will be in the next content
                next = test_result_field['content'][0]['content'][idx+1]
                if 'text' in next and next['text'].strip() != '<launchpad ID>':
                    lp_id = next['text'].strip()
                    members = get_jira_members()
                    # check launchpad id is one of QAs
                    if lp_id not in members:
                        err_msg = 'Error: Invalid Launchpad ID, couldn\'t' + \
                            ' find this person'
                        raise Exception(err_msg)
                    re_dict['qa_launchpad_id'] = lp_id
                else:
                    err_msg = 'Error: Please give the Launchpad ID'
                    raise Exception(err_msg)
    except Exception as e:
        print(e)
        raise Exception(
            f'Error: Failed to get the QA launchpad ID from card \'{key}\'')

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
            f'Warning: Failed to get the GM Image Path from card \'{key}\'')

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
        'project = {} AND issuekey = "{}"'.format(jira_api.jira_project['key'],
                                                  key),
        'fields': [
            'description',
            jira_api.jira_project['card_fields']['Test result']
        ],
    }
    response = jira_api.get_issues(payload=payload)
    parsed = json.loads(response.text)

    # By design, the "Test result" field is the default field
    # in each Jira card on QA's Jira project
    return parsed, jira_api.jira_project['card_fields']['Test result']


def sanitize_row_data(data: dict) -> tuple[bool, list]:
    """ Sanitize the data to see whether it's valid or not by checking
        the value of cid and location.

        @param:data, it's a row record in Jira table. Please see the
                    VALID_ROW_DATA to know its structure.

        @return
            @is_valid, the data is valid or not. True / False
            @row, a list in ['cid', 'sku', 'location'] format
    """
    is_valid = False
    row = []

    # Retrieve (CID, SKU, Location) and append them to row list
    for i in data['content']:
        if i['content'][0]['content']:
            row.append(i['content'][0]['content'][0]['text'].strip())
        else:
            row.append('')

    is_valid = is_valid_cid(row[0]) and is_valid_location(row[2])

    return is_valid, row


def get_candidate_duts(key: str) -> dict:
    """ Get the candidate DUT(s) from specific Jira Card's table

        @param:key, the key of jira card. e.g. CQT-1234

        @return
        {
            'gm_image_link': '',
            'qa_launchpad_id': '',
            'valid': [{
                'cid': '202212-12345',
                'sku': '',
                'location:': 'TEL-L3-F24-S5-P1'
            }],
            'invalid': [{
                'cid': '202212-123xcc',
                'sku': '',
                'location:': 'TELAc-L309-F24-S5-P1c'
            }]
        }
    """
    content = get_content_from_a_jira_card(key)

    # Return dictionary
    re_dict = {
        'valid': [],
        'invalid': [],
        'gm_image_link': content['gm_image_link'],
        'qa_launchpad_id': content['qa_launchpad_id']
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
        err_msg = 'Error: expect more than 2 rows in table but got {}'.format(
            len(content['table']))
        raise Exception(err_msg)

    for i in range(2, len(content['table'])):
        valid, data = sanitize_row_data(content['table'][i])
        tmp_d = {
            'cid': data[0],
            'sku': data[1],
            'location': data[2],
        }
        re_dict['valid' if valid else 'invalid'].append(tmp_d)

    return re_dict
