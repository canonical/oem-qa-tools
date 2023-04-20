import json
from argparse import ArgumentParser

from jira_card_handler import get_candidate_duts
from cert_team_google_sheet_handler import update_cert_lab_google_sheet


def register_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        "-k", "--key",
        help="The key string of specific Jira Card. e.g. CQT-2023",
        type=str, required=True,
    )
    return parser.parse_args()


def main():
    args = register_arguments()

    key = args.key

    print('-' * 5 + 'Retrieving data from Jira Card' + '-' * 5)
    # Get data from specific Jira Card
    data = get_candidate_duts(key)
    print(json.dumps(data, indent=2))

    # Update Cert Lab Google Sheet
    gm_image_link = data['gm_image_link']
    for d in data['valid']:
        d['gm_image_link'] = gm_image_link

    print('-' * 5 + 'Updating Cert Lab Google Sheet' + '-' * 5)
    update_cert_lab_google_sheet(data['valid'])

    # TODO: Update C3 holder


if __name__ == '__main__':
    main()
