import os
import json
import copy
from argparse import ArgumentParser

from pc_platform_tracker import generate_platform_records
from Jira.scenarios.pc.pc import create_task_card

# Get path of the configs of PC project from PC scenario in Jira API
project_conf_folders = os.path.join(
    os.getcwd(), "Jira", "scenarios", "pc", "configs")

if not os.path.exists(project_conf_folders):
    raise Exception("Fail to find the path of PC configs")

SUPPORTED_PROJECTS = [
    os.path.splitext(i)[0] for i in os.listdir(project_conf_folders)
    if os.path.splitext(i)[1] == ".json"
]


def register_arguments():
    options = copy.deepcopy(SUPPORTED_PROJECTS)
    options.append("all")

    parser = ArgumentParser()
    parser.add_argument(
        "-p", "--project",
        help="select one of supported projects",
        type=str, required=True,
        choices=options,
    )
    parser.add_argument(
        "-o", "--output",
        help="select one of supported output type."
        " Default is 'console', it will show you the result on console in JSON"
        " format. Option 'file' will log the data to 'output.json' file",
        type=str,
        default='console',
        choices=['console', 'file'],
    )
    parser.add_argument(
        "-d", "--dry-run",
        help="get project data from project book only, won't create Jira Card",
        action='store_true'
    )
    return parser.parse_args()


def main():
    args = register_arguments()
    projects = SUPPORTED_PROJECTS if args.project == "all" else [args.project]
    payload = generate_platform_records(projects)

    if payload:
        print(args.output)
        if args.output == "console":
            print(json.dumps(payload, indent=4))
        elif args.output == "file":
            with open("output.json", "w") as outfile:
                outfile.write(json.dumps(payload, indent=4))
        if not args.dry_run:
            create_task_card(payload)


if __name__ == "__main__":
    main()
