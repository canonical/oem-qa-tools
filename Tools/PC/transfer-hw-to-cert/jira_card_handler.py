import json

from Jira.apis.base import JiraAPI


def get_table_content_from_a_jira_card(key: str) -> list[dict]:
    """ Get the content of table in a specific Jira card

        @param: key, the key of jira card. e.g. CQT-1234

        @return
            [
                {
                    'cid': '202212-12345',
                    'sku': '',
                    'location:': 'TEL-L3-F24-S5-P1'
                }
            ]
    """
    # Check parameter type
    if not isinstance(key, str):
        raise TypeError()

    # Get Jira content via API
    jira_api = JiraAPI()
    payload = {
        'jql': 'project = {} AND issuekey = "{}"'.format(
            jira_api.jira_project['key'], key
        ),
        'fields': [jira_api.jira_project['card_fields']['Test result']],
    }
    response = jira_api.get_issues(payload=payload)
    # print(type)
    parsed = json.loads(response.text)
    print(json.dumps(parsed, indent=2))

    # Retrieve candidate DUT info from table
    try:
        # Index is 0 because we searched by the key of Jira card
        # Only one issue is expected
        card_fields = parsed['issues'][0]['fields']
        # By design, the "Test result" field is the default field
        # in each Jira card on QA's Jira project
        test_result_field = card_fields[
            jira_api.jira_project['card_fields']['Test result']]
        # Get the table content, by design, index of table is 1
        table_content = test_result_field['content'][1]['content']
    except TypeError:
        print(f'Error: Failed to get the table content of card \'{key}\'')
        raise

    return table_content


def get_candidate_dut(key: str) -> list[dict]:
    """
    """
    table = get_table_content_from_a_jira_card(key)

    # Check format CID, Location
    start_idx = 2
    # print(table[2])
    return []


def sanitize_record(record: dict) -> dict:
    pass


if __name__ == '__main__':
    get_candidate_dut(key='VS-2623')
