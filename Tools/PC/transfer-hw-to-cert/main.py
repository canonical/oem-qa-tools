from argparse import ArgumentParser

from jira_card_handler import get_candidate_duts


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

    # Get data from specific Jira Card
    data = get_candidate_duts(key)

    # TODO: Update Cert Lab Google Sheet


if __name__ == '__main__':
    main()
