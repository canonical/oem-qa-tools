'''
    CERTSETUP Jira Board Handler
'''

import json

from Jira.apis.base import JiraAPI
from handlers.c3_handler import get_duts_info_from_c3


def create_card_in_certsetup(data: list) -> None:
    """ Create card to TELOPS board for contractor using, the type of card is
        "DUT Send To Cert"

        @param:data, a list contains CID information.
            e.g
                [
                    {
                        'CID': '202303-12345',
                        'Location': ''
                    },
                ]
    """
    issue_updates = []  # Put tasks in this list

    telops_jira_api = JiraAPI(
        path_of_jira_board_conf='./configs',
        jira_board_conf='jira_certsetup.json'
    )

    new_data = get_duts_info_from_c3(data)

    for d in new_data:
        # Template of "fields" payload in Jira's request
        fields = telops_jira_api.create_jira_fields_template(
            task_type='Task')

        # FIXME:need to always assign to Jonathan
        # Remove the reporter field since CERTSETUP cannot set the reporter
        del fields['reporter']

        # Assign Summary
        fields['summary'] = 'Patrick Test -- CID#{} {} {}'.format(
            d['cid'],
            d['make'],
            d['model']
        )

        issue_updates.append({'fields': fields, 'update': {}})

    response = telops_jira_api.create_issues(
        payload={'issueUpdates': issue_updates})
    if not response.ok:
        print('*' * 50)
        print(json.dumps(issue_updates, indent=2))
        raise Exception(
            'Error: Failed to create card to CERTSETUP board',
            'Reason: {}'.format(response.text)
        )
    print('Created the following cards to CERTSETUP board successfully')
    print(json.dumps(response.json(), indent=2))
