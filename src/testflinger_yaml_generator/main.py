"""The CLI app that generates Testflinger job.yaml files.

For more details, check out testflinger's schema page
https://canonical-testflinger.readthedocs-hosted.com/latest/reference/job-schema.html
"""

import argparse


def parse_args() -> argparse.Namespace:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Testflinger job.yaml generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    req_args = parser.add_argument_group(
        "Required Arguments",
    )
    req_args.add_argument(
        "-c",
        "--CID",
        type=str,
        required=True,
        help=(
            "CID of the machine. "
            "This assumes a job queue with this name exists"
        ),
    )
    req_args.add_argument(
        "-o",
        "--output-file-name",
        "--outputFileName",
        type=str,
        required=True,
        help="Name of the output YAML file",
    )

    # optional args section

    opt_args = parser.add_argument_group("General Options")
    opt_args.add_argument(
        "-d",
        "--output-folder",
        "--outputFolder",
        type=str,
        default=".",
        help="Set the output folder path",
    )
    opt_args.add_argument(
        "--dist-upgrade",
        action="store_true",
        help=(
            "Specify this option to run `apt dist-upgrade` "
            "right after the image is installed"
        ),
    )
    opt_args.add_argument(
        "--test-plan",
        "--testplan",
        type=str,
        default="",
        help=(
            "Which checkbox test plan to run. "
            "If not specified, no tests will be run"
        ),
    )
    opt_args.add_argument(
        "--exclude-jobs",
        "--excludeJobs",
        type=str,
        default="",
        help=(
            "Regex pattern of the checkbox jobs to exclude. "
            "See checkbox's explanation on this."
        ),
    )
    opt_args.add_argument(
        "--session-description",
        "--sessionDesc",
        type=str,
        default="CE-QA-PC_Test",
        help=(
            "Sets the session description. "
            "This is the string that appears on C3"
        ),
    )
    opt_args.add_argument(
        "--checkbox-type",
        "--checkboxType",
        choices=["deb", "snap"],
        default="deb",
        help="Sets which checkbox type you need to install and test.",
    )
    opt_args.add_argument(
        "--provision-type",
        "--provisionType",
        choices=["distro", "url"],
        default="distro",
        help=(
            "Sets the provision type. "
            "Explanation is on testflinger provision phase's schema page"
        ),
    )
    opt_args.add_argument(
        "--provision-image",
        "--provisionImage",
        type=str,
        default="",
        help=(
            "The provision image. "
            "ie, desktop-22-04-2-uefi. "
            "If unspecified, provision phase will be skipped"
        ),
    )
    opt_args.add_argument(
        "--provision-token",
        "--provisionToken",
        default="",
        type=str,
        help=(
            "Optional file with username and token "
            "when image URL requires authentication "
            "(i.e Jenkins artifact). This file must be "
            "in YAML format, i.e: "
            "username: $JENKINS_USERNAME \n "
            "token: $JENKINS_API_TOKEN"
        ),
    )
    opt_args.add_argument(
        "--provision-user-data",
        "--provisionUserData",
        default="",
        type=str,
        help=(
            "user-data file for autoinstall and cloud-init "
            "provisioning. This argument is a MUST required "
            "if deploy the image using the autoinstall image "
            "(i.e. 24.04 image)"
        ),
    )
    opt_args.add_argument(
        "--provision-auth-keys",
        "--provisionAuthKeys",
        default="",
        type=str,
        help="The SSH `authorized_keys` file to add in provisioned system",
    )
    opt_args.add_argument(
        "--global-timeout",
        "--globalTimeout",
        type=int,
        default=43200,
        help=(
            "Sets the testflinger's global timeout. "
            "Default is 43200 seconds from testflinger's website."
        ),
    )
    opt_args.add_argument(
        "--output-timeout",
        "--outputTimeout",
        type=int,
        default=9000,
        help=(
            "Sets the output timeout if the DUT didn't "
            "response to server, it will be forced closed "
            "this job. It should be set under the global "
            "timeout."
        ),
    )

    # checkbox options

    opt_launcher = parser.add_argument_group("Checkbox options")
    opt_launcher.add_argument(
        "--manifest-json",
        "--manifestJson",
        type=str,
        help=(
            "Path to the manifest.json file. "
            "If not specified, all manifest entries are set to true"
        ),
    )
    opt_launcher.add_argument(
        "--checkbox-conf",
        "--checkboxConf",
        type=str,
        help=(
            "Path to the checkbox.conf file. "
            "If not specified, the default conf from here is used"
        ),
    )

    # yaml options

    opt_tf_yaml = parser.add_argument_group("Testflinger yaml options")
    opt_tf_yaml.add_argument(
        "--launchpad-id",
        "--LpID",
        type=str,
        default="",
        help=(
            "The Launchpad ID to use for the reserve phase. "
            "If specified, the person with this ID will be able "
            "to SSH into the machine"
        ),
    )
    opt_tf_yaml.add_argument(
        "--reserve-time",
        "--reserveTime",
        type=int,
        default=1200,
        help=(
            "Number of seconds to reserve the DUT. "
            "--launchpad-id must be specified together"
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Runs main."""
    parse_args()


if __name__ == "__main__":
    main()
