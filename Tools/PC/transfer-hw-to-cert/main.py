import json
from argparse import ArgumentParser

from handlers.cqt_handler import get_candidate_duts
from handlers.telops_handler import create_send_dut_to_cert_card_in_telops
from handlers.certsetup_handler import create_card_in_certsetup
from handlers.cert_team_google_sheet_handler import (
    update_cert_lab_google_sheet
)
from handlers.c3_handler import update_duts_info_on_c3
from handlers.notifier import add_comment
from utils.common import is_valid_cid, is_valid_location


def register_arguments():
    parser = ArgumentParser()
    parser.add_argument(
        '-k', '--key',
        help='The key string of specific Jira Card. e.g. CQT-2023',
        type=str,
        required=True
    )
    parser.add_argument(
        '-j', '--jenkins-job-link',
        help='The link of jenkins job.',
        type=str,
        default='http://<ip>/view/qa-services/job/qa-transfer-hw-to-cert-lab/',
    )
    parser.add_argument(
        '-c', '--c3-holder',
        help='The DUT holder on C3. Please feed the launchpad id',
        type=str,
        default='kevinyeh'
    )
    parser.add_argument(
        '-s', '--scenario',
        help='The scenarios of this transfer hardware. Default is qa_process',
        type=str,
        choices=['qa_process', 'contractor_process'],
        default='qa_process',
    )
    return parser.parse_args()


def main():
    args = register_arguments()

    key = args.key
    try:
        print('-' * 5 + 'Retrieving data from Jira Card' + '-' * 5)
        # Get data from specific Jira Card
        data = get_candidate_duts(key)
        print(json.dumps(data, indent=2))

        if args.scenario == 'qa_process':
            # Sanitize
            for d in data['data']:
                if not is_valid_cid(d['cid']) \
                        or not is_valid_location(d['location']):
                    raise Exception(
                        f'Error: invalid CID or Location in Jira Card {key}')

            # Update Cert Lab Google Sheet
            gm_image_link = data['gm_image_link']
            for d in data['data']:
                d['gm_image_link'] = gm_image_link

            print('-' * 5 + 'Updating Cert Lab Google Sheet' + '-' * 5)
            update_cert_lab_google_sheet(data['data'])

            # Update DUT holder and location on C3
            print('-' * 5 + 'Updating C3' + '-' * 5)
            update_duts_info_on_c3(
                data=data['data'], new_holder=args.c3_holder)
        else:
            # Sanitize
            for d in data['data']:
                # Don't care the Location data
                if not is_valid_cid(d['cid']):
                    raise Exception(
                        f'Error: invalid CID in Jira Card {key}')
            # Create Jira card to TELOPS board
            print('-' * 5 + 'Creating card to TELOPS board' + '-' * 5)
            create_send_dut_to_cert_card_in_telops(
                cqt_card=key,
                reporter=data['qa_launchpad_id'],
                data=data['data']
            )

        # Create Jira card to CERTSETUP board
        print('-' * 5 + 'Creating card to CERTSETUP board' + '-' * 5)
        create_card_in_certsetup(data=data['data'])

        #  notify: leave successful comment to Jira card
        add_comment(
            comment_type='success',
            key=key,
            data={
                'jenkins_job_link': args.jenkins_job_link
            }
        )
    except Exception:
        # notify: leave failed comment to Jira card
        add_comment(
            comment_type='error',
            key=key,
            data={
                'jenkins_job_link': args.jenkins_job_link
            }
        )
        raise


if __name__ == '__main__':
    main()
