import json
import re

from Jira.apis.base import JiraAPI


def get_table_content_from_a_jira_card(key: str) -> list[dict]:
    """ Get the content of table from the 'Test result' field in a specific
        Jira card.

        @param:key, the key of jira card. e.g. CQT-1234

        @return, a list contains dictionary. Please see the value of
                'VALID_RESULT_FROM_API' in tests/testdata
    """
    # Get the content of specific Jira card via API
    response, target_field = api_get_jira_card(key)
    if 'errorMessages' in response:
        err_msg = 'Error: Failed to get the card \'{}\'. {}'.format(
            key, re.sub('\[\]', '', response['errorMessages']))  # noqa: W605
        raise Exception(err_msg)

    # Check if only one issue we got
    if len(response['issues']) != 1:
        err_msg = 'Error: expect only 1 jira issue but got {} issues'.format(
            len(response['issues']))
        raise Exception(err_msg)

    # Retrieve candidate DUT info from table
    try:
        # Index is 0 because we search the Jira card by key,
        # only one issue is expected.
        # By design, the "Test result" field is the default field
        # in each Jira card on QA's Jira project.
        test_result_field = response['issues'][0]['fields'][target_field]

        # Get the table content
        table_idx = None
        for idx in range(len(test_result_field['content'])):
            # Find the index fo 'table' dict in the content list
            if 'type' in test_result_field['content'][idx] and \
                    test_result_field['content'][idx]['type'] == 'table':
                table_idx = idx
                break
        # Get the content list from table dict
        table_content = test_result_field['content'][table_idx]['content']
    except TypeError:
        print(f'Error: Failed to get the table content from card \'{key}\'')
        raise

    return table_content


def api_get_jira_card(key: str) -> tuple[dict, str]:
    """ Get the content of specific Jira card via API

        @param:key, the key of jira card. e.g. CQT-1234

        @return
            @parsed, the respone returned from Jira API. Type: dict
            @field, the 'Test reulst' field in specific Jira project. Type: str
    """
    jira_api = JiraAPI()
    payload = {
        'jql':
        'project = {} AND issuekey = "{}"'.format(jira_api.jira_project['key'],
                                                  key),
        'fields': [jira_api.jira_project['card_fields']['Test result']],
    }
    response = jira_api.get_issues(payload=payload)
    parsed = json.loads(response.text)

    # By design, the "Test result" field is the default field
    # in each Jira card on QA's Jira project
    return parsed, jira_api.jira_project['card_fields']['Test result']


def is_valid_cid(cid: str) -> bool:
    """ Check if it's valid of the format of CID
    """
    pattern = re.compile(r'^20\d{2}0[1-9]-\d{5}$|^20\d{2}1[0-2]-\d{5}$')
    return True if re.match(pattern, cid) else False


def is_valid_location(location: str) -> bool:
    """ Check if it's valid of the format of Location
    """
    pattern = re.compile(
        r'^TEL-L\d-F\d{2}-S\d-P[12]$|^TEL-L\d-R\d{2}-S\d{1,2}-P0$')
    return True if re.match(pattern, location) else False


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
            row.append(i['content'][0]['content'][0]['text'])
        else:
            row.append('')

    is_valid = is_valid_cid(row[0]) and is_valid_location(row[2])

    return is_valid, row


def get_candidate_duts(key: str) -> dict:
    """ Get the candidate DUT(s) from specific Jira Card's table

        @param:key, the key of jira card. e.g. CQT-1234

        @return
        {
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
    # Return dictionary
    re_dict = {'valid': [], 'invalid': []}

    table = get_table_content_from_a_jira_card(key)

    # Sanitize each dut
    #
    # Why start from 2?
    # Ans:
    #   According to our Jira template
    #     - idx 0 is table's header
    #     - idx 1, aka row 1, is the example placeholder
    #   So the real data should be started from idx 2
    if len(table) < 3:
        err_msg = 'Error: expect more than 2 rows in table but got {}'.format(
            len(table))
        raise Exception(err_msg)

    for i in range(2, len(table)):
        valid, data = sanitize_row_data(table[i])
        re_dict['valid'].append(data) if valid else \
            re_dict['invalid'].append(data)

    return re_dict


if __name__ == '__main__':
    print(get_candidate_duts(key='VS-2623'))
