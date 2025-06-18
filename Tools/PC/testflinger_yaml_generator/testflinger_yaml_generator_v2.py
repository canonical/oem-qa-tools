#!/usr/bin/env python3

import argparse
import glob
import json
import os
import re
import shutil
import subprocess as sp
import warnings
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Literal

import yaml

COMMAND_TIMEOUT = 5

# for these literals, the 1st value is used as default in the arg parser
CheckboxType = Literal["deb", "snap"]
ProvisionType = Literal["distro", "url"]


def shellcheck_for_cmd_str(cmd_str: str, shell_name="bash") -> bool:
    if not shutil.which("shellcheck"):
        warnings.warn(
            "Can't find the shellcheck executable in your $PATH. "
            "Please install shellcheck if you want to do this check.",
            Warning,
        )
        return False

    shell_list = ("sh", "bash", "dash", "ksh")
    if shell_name not in shell_list:
        raise ValueError(f"Invalid shell name. Expected one of: {shell_list}")

    with open("./tmp.sh", "w") as tmp_file:
        tmp_file.write(cmd_str)
        ret = sp.run(
            ["shellcheck", "-s", shell_name, tmp_file.name],
            text=True,
            timeout=COMMAND_TIMEOUT,
            # no need to capture the output
        )

        if ret.returncode == 0:
            print("Shellcheck: Pass")
            return True

        warnings.warn(
            "\n".join(
                [
                    "Shellcheck: Fail",
                    f"Please check the file: {tmp_file.name}",
                ]
            ),
            Warning,
        )
        return False


class ConfigOperation:
    def __init__(
        self, delimiters=("=",), optionform=lambda optionstr: str(optionstr)
    ):
        self.config_object = ConfigParser(delimiters=delimiters)
        self.config_object.optionxform = optionform

    def merge_with_file(
        self,
        file_path: Path,
        import_file_type="conf",
        json_conf_section_name="manifest",
    ):
        file_type_list = ("conf", "json", ".conf", ".json")
        if import_file_type not in file_type_list:
            raise ValueError(
                f"Invalid file type. Expected one of: {file_type_list}"
            )
        if os.path.exists(file_path):
            real_file_type = os.path.splitext(file_path)[1]
            if real_file_type == "":
                file_type = import_file_type
            else:
                if real_file_type not in file_type_list:
                    raise ValueError(
                        f"Invalid file type. Expected one of: {file_type_list}"
                    )
                file_type = real_file_type

            if file_type in ("conf", ".conf"):
                self.config_object.read(file_path)
            elif file_type in ("json", ".json"):
                with open(file_path, "r", encoding="utf-8") as file:
                    conf_dict = {json_conf_section_name: json.load(file)}
                    self.merge_with_dict(conf_dict)
            # no else path, already checked
        else:
            raise FileNotFoundError(f"File does not exist: {file_path}")

    def merge_with_dict(self, dict_content: dict[str, dict[str, Any]]):
        sections = dict_content.keys()
        for section in sections:
            if self.config_object.has_section(section) is False:
                self.config_object.add_section(section)
        for section in sections:
            inner_dict = dict_content[section]
            fields = inner_dict.keys()
            for field in fields:
                value = inner_dict[field]
                self.config_object.set(section, field, str(value))

    def remove_section_value(self, section_name: str, key: str):
        if self.config_object.has_section(section_name):
            self.config_object.remove_option(section_name, key)

    def update_section_value(self, section_name, key, value):
        self.config_object.set(section_name, key, str(value))

    def generate_config_file(
        self,
        file_path=Path("./final_launcher"),
        checkbox_bin="/usr/bin/env checkbox-cli",
    ):
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"#!{checkbox_bin}\n")
            self.config_object.write(file)
        with open(file_path, "r+", encoding="utf-8") as file:
            file.seek(0, os.SEEK_END)
            pos = file.tell() - 1
            while pos > 0 and file.read(1) != "\n":
                pos -= 1
                file.seek(pos, os.SEEK_SET)
            if pos > 0:
                file.seek(pos, os.SEEK_SET)
                file.truncate()


class YamlGenerator:
    def __init__(
        self, default_yaml_file_path=Path("./template/template.yaml")
    ):
        if os.path.exists(default_yaml_file_path):
            with open(default_yaml_file_path, "r", encoding="utf-8") as file:
                self.yaml_dict = yaml.load(file, Loader=yaml.SafeLoader)
        else:
            self.yaml_dict = {}

    def yaml_update_field(self, input_dict: dict[str, Any]):
        self.yaml_dict.update(input_dict)

    def yaml_remove_field(self, field_name: str):
        if field_name in self.yaml_dict:
            self.yaml_dict.pop(field_name)

    def generate_yaml_file(self, file_path=Path("./final_testflinger.yaml")):
        def str_representer(
            dumper: yaml.representer.SafeRepresenter,
            data: str,
        ):
            if data.count("\n") > 0:
                return dumper.represent_scalar(
                    "tag:yaml.org,2002:str", data, style="|"
                )
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        yaml.representer.SafeRepresenter.add_representer(str, str_representer)
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data=self.yaml_dict, stream=file)


class CheckboxLauncherBuilder(ConfigOperation):
    def __init__(self, template_folder=Path("./template/launcher_config")):
        super().__init__(delimiters=("=",), optionform=str)
        launcher_template_list = glob.glob(f"{template_folder}/*.conf")

        if len(launcher_template_list) == 0:
            raise ValueError(
                f"Couldn't find the .conf file under launcher \
                                template folder: {template_folder}"
            )

        for file in launcher_template_list:
            self.merge_with_file(Path(file), "conf")

    def merge_manifest_json(self, json_file_path):
        if os.path.exists(json_file_path):
            self.merge_with_file(json_file_path, "json", "manifest")

    def merge_checkbox_conf(self, conf_path):
        if os.path.exists(conf_path):
            self.merge_with_file(conf_path, "conf")

    def set_test_plan(self, test_plan_name="client-cert-desktop-20-04-auto"):
        if "com.canonical.certification" not in test_plan_name:
            test_plan_name = f"com.canonical.certification::{test_plan_name}"
        self.update_section_value("test plan", "unit", test_plan_name)

    def set_exclude_job(self, exclude_job_pattern_str=""):
        if not exclude_job_pattern_str:
            self.remove_section_value("test selection", "exclude")
            return
        self.update_section_value(
            "test selection", "exclude", exclude_job_pattern_str
        )


class TestCommandGenerator(CheckboxLauncherBuilder):
    default_session_desc = "CE-QA-PC_Test"

    def __init__(
        self,
        template_bin_folder=Path("./template/shell_scripts/"),
        launcher_temp_folder=Path("./template/launcher_config"),
    ):
        super().__init__(template_folder=launcher_temp_folder)

        self.bin_folder = template_bin_folder
        self.shell_file_list = sorted(
            Path(template_bin_folder) / f
            for f in os.listdir(self.bin_folder)
            if re.search(r"^(\d{2}).*", f)  # starts with 2 digits
        )

    def build_launcher(
        self,
        manifest_json_path: Path,
        checkbox_conf_path: Path,
        test_plan_name: str,
        exclude_job_pattern_str: str,  # this is for checkbox to consume
        file_path=Path("./final_launcher"),
        checkbox_bin="/usr/bin/env checkbox-cli",
        need_manifest=True,
    ):
        self.set_test_plan(test_plan_name)
        self.set_exclude_job(exclude_job_pattern_str)

        if need_manifest:
            self.merge_manifest_json(json_file_path=manifest_json_path)

        self.merge_checkbox_conf(conf_path=checkbox_conf_path)
        self.generate_config_file(
            file_path=file_path, checkbox_bin=checkbox_bin
        )

    def generate_test_cmd(
        self,
        manifest_json_path: Path,
        checkbox_conf_path: Path,
        test_plan_name: str,
        exclude_job_pattern_str: str,
        is_dist_upgrade=False,
        checkbox_type: CheckboxType = "deb",
        is_runtest=True,
        need_manifest=True,
        session_desc=default_session_desc,
    ):
        # the lines in the final test_cmd field
        command_strings = []  # type: list[str]
        for shell_file in self.shell_file_list:
            # the file name without path
            basename = os.path.basename(shell_file)
            if (
                "Install_checkbox" in basename
                and checkbox_type not in basename
            ):
                continue

            if basename == "90_start_test" and not is_runtest:
                continue
            if basename == "01_dist_upgrade" and not is_dist_upgrade:
                continue

            if basename == "90_start_test":
                launcher_file_path = Path("./final_launcher")
                self.build_launcher(
                    manifest_json_path,
                    checkbox_conf_path,
                    test_plan_name,
                    exclude_job_pattern_str,
                    launcher_file_path,
                    "/usr/bin/env checkbox-cli",
                    need_manifest,
                )

                with open(
                    launcher_file_path, "r", encoding="utf-8"
                ) as launcher_file:
                    command_strings.append("cat <<EOF > checkbox-launcher")

                    for line in launcher_file:
                        if line.strip() != "":
                            command_strings.append(line.strip())

                    command_strings.append("EOF")

            with open(shell_file, "r", encoding="utf-8") as f_file:
                content = f_file.read().strip()
                if content:
                    if (
                        self.default_session_desc != session_desc
                        and f'SESSION_DESC="{self.default_session_desc}"'
                        in content
                    ):
                        content = content.replace(
                            f'SESSION_DESC="{self.default_session_desc}"',
                            f'SESSION_DESC="{session_desc}"',
                        )

                    for content_line in content.splitlines():
                        clean_line = content_line.strip("\n")
                        if clean_line:
                            command_strings.append(clean_line)

        # test_cmd field
        test_cmd = "\n".join(command_strings)
        shellcheck_ok = shellcheck_for_cmd_str(test_cmd)

        if not shellcheck_ok:
            warnings.warn(
                "Shellcheck failed after combining the files under "
                + str(self.bin_folder),
                Warning,
            )

        return test_cmd


class TFYamlBuilder:
    def __init__(
        self,
        cid: str,
        default_yaml_file_path=Path("./template/template.yaml"),
        global_timeout=43200,  # seconds
        output_timeout=3600,  # seconds
        template_bin_folder=Path("./template/shell_scripts/"),
        launcher_temp_folder=Path("./template/launcher_config/"),
        is_run_test=True,
        need_manifest=True,
        is_dist_upgrade=False,
    ):
        self.yaml_generator = YamlGenerator(
            default_yaml_file_path=default_yaml_file_path
        )
        self.test_command_generator = TestCommandGenerator(
            template_bin_folder, launcher_temp_folder
        )
        self.yaml_generator.yaml_update_field(
            {"global_timeout": global_timeout}
        )
        self.yaml_generator.yaml_update_field(
            {"output_timeout": output_timeout}
        )
        self.yaml_generator.yaml_update_field({"job_queue": cid})
        self.is_runtest = is_run_test
        self.need_manifest = need_manifest
        self.is_dist_upgrade = is_dist_upgrade

    def provision_setting(
        self,
        is_provision: bool,
        image="desktop-22-04-2-uefi",
        provision_type: Literal["distro", "url"] = "distro",
        provision_token="",
        provision_auth_keys="",
        provision_user_data="",
    ):
        if not is_provision:
            self.yaml_generator.yaml_remove_field("provision_data")
            return
        setting_dict: dict[str, dict[str, Any]] = {
            "provision_data": {provision_type: image}
        }

        # additional parameters if use oem_autoinstall connector
        attachments: list[dict[str, str]] = []
        if provision_user_data:
            setting_dict["provision_data"]["user_data"] = provision_user_data
            attachments.append({"local": provision_user_data})
        if provision_token:
            setting_dict["provision_data"]["token_file"] = provision_token
            attachments.append({"local": provision_token})
        if provision_auth_keys:
            setting_dict["provision_data"][
                "authorized_keys"
            ] = provision_auth_keys
            attachments.append({"local": provision_auth_keys})
        if attachments:
            setting_dict["provision_data"]["attachments"] = attachments

        self.yaml_generator.yaml_update_field(setting_dict)

    def reserve_setting(self, is_reserve: bool, lp_username: str, timeout=120):
        if not is_reserve:
            self.yaml_generator.yaml_remove_field("reserve_data")
            return

        self.yaml_generator.yaml_update_field(
            {
                "reserve_data": {
                    "timeout": timeout,
                    "ssh_keys": [f"lp:{lp_username}"],
                }
            }
        )

    def test_cmd_setting(
        self,
        manifest_json_path=Path("./template/manifest.json"),
        checkbox_conf_path=Path("./template/checkbox.conf"),
        test_plan_name="client-cert-desktop-20-04-automated",
        exclude_job_pattern_str="",  # this is directly passed to checkbox
        checkbox_type: CheckboxType = "deb",
        session_desc="CE-QA-PC_Test",
    ):
        test_cmds_str = self.test_command_generator.generate_test_cmd(
            manifest_json_path,
            checkbox_conf_path,
            test_plan_name,
            exclude_job_pattern_str,
            self.is_dist_upgrade,
            checkbox_type,
            self.is_runtest,
            self.need_manifest,
            session_desc,
        )
        self.yaml_generator.yaml_update_field(
            {"test_data": {"test_cmds": test_cmds_str}}
        )


def is_cid(raw: str) -> str:
    pat = re.compile(r"\d{6}-\d{5}\b")
    if not pat.fullmatch(raw):
        # argparse looks for this exception
        raise argparse.ArgumentTypeError(
            "CID should look like 202408-12345 (6 digits, dash, 5 digits)"
        )
    return raw


def directory_exists(p: str, required_files: list[str] = []) -> str:
    path = Path(p)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"{p} is not a valid path")
    for f in required_files:
        if not os.path.exists(path / f):
            raise argparse.ArgumentTypeError(
                f"{path / f} is a required file but doesn't exist"
            )
    return str(path)


def file_exists(p: str, null_ok=False) -> str:
    """Checks if the file exists

    :param p: path to the file
    :param null_ok: whether to accept an empty string,
        - specify True when the path is optional
    :raises argparse.ArgumentTypeError: error for argparse to consume
    :return: cleaned up path
    """
    if null_ok and p == "":
        return p
    if not os.path.isfile(p):
        raise argparse.ArgumentTypeError(f"{p} is not a valid file")
    return str(Path(p))


def parse_args():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Testflinger yaml file generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    req_args = parser.add_argument_group(
        "Required Parameters",
    )
    req_args.add_argument(
        "-c", "--CID", type=is_cid, required=True, help="Canonical ID"
    )
    req_args.add_argument(
        "-o",
        "--output-file-name",
        type=str,
        required=True,
        help="Name of the output file",
    )

    opt_args = parser.add_argument_group("Optional Parameters")
    opt_args.add_argument(
        "--output-folder",
        type=directory_exists,
        default=script_dir,
        help="Set the output folder path",
    )
    opt_args.add_argument(
        "--dist-upgrade",
        action="store_true",
        help="Run dist-upgrade before checkbox tests",
    )
    opt_args.add_argument(
        "--test-plan",
        type=str,
        help=(
            "The checkbox test plan to run. "
            "If unspecified, not checkbox tests will be run"
        ),
    )
    opt_args.add_argument(
        "--exclude-jobs",
        type=str,
        default="",
        help='Regex exclude jobs pattern like ".*memory/memory_stress_ng"',
    )
    opt_args.add_argument(
        "--session-desc",
        type=str,
        default="CE-QA-PC_Test",
        help="Set the session description",
    )
    opt_args.add_argument(
        "--checkbox-type",
        # __args__ is tuple of values between CheckboxType's brackets
        # in this case ("deb", "snap")
        choices=CheckboxType.__args__,
        default=CheckboxType.__args__[0],
        help="The type of checkbox you need to install",
    )
    opt_args.add_argument(
        "--provision-type",
        choices=ProvisionType.__args__,
        default=ProvisionType.__args__[0],
        help="Set the provision type",
    )
    opt_args.add_argument(
        "--provision-image",
        type=str,
        default="",
        help=(
            'The provision image name/url like "desktop-22-04-2-uefi"'
            "If unspecified, don't provision"
        ),
    )
    opt_args.add_argument(
        "--provision-token",
        default="",
        required=False,
        type=lambda x: file_exists(x, True),
        help='Optional file with username and token \
                          when image URL requires authentication \
                          (i.e Jenkins artifact). This file must be \
                          in YAML format, i.e: \
                          "username: $JENKINS_USERNAME \\n \
                          token: $JENKINS_API_TOKEN"',
    )
    opt_args.add_argument(
        "--provision-user-data",
        default="",
        type=lambda x: file_exists(x, True),
        help=(
            "user-data file for autoinstall and cloud-init "
            "provisioning. This argument is REQUIRED "
            "if deploying an autoinstall image "
            "(i.e. 24.04 image)"
        ),
    )
    opt_args.add_argument(
        "--provision-auth-keys",
        default="",
        type=lambda x: file_exists(x, True),
        help="ssh authorized_keys file to add in provisioned system",
    )
    opt_args.add_argument(
        "--provision-only",
        action="store_true",
        help=(
            "Run only provisioning without tests. "
            "Removes test_data before generating the yaml."
        ),
    )
    opt_args.add_argument(
        "--global-timeout",
        type=int,
        default=43200,
        help="Testflinger's global timeout in seconds",
    )
    opt_args.add_argument(
        "--output-timeout",
        type=int,
        default=9000,
        help=(
            "Testflinger's output timeout if the DUT didn't "
            "respond to server, it will be forced closed "
            "this job. It should be set under the global "
            "timeout."
        ),
    )

    opt_launcher = parser.add_argument_group("Launcher options")

    manifest_group = opt_launcher.add_mutually_exclusive_group()
    manifest_group.add_argument(
        "--manifest-json",
        type=file_exists,
        default=f"{script_dir}/template/manifest.json",
        help="The manifest.json file to build the checkbox launcher",
    )
    manifest_group.add_argument(
        "--no-need-manifest",
        dest="need_manifest",
        action="store_false",
        help=(
            "Specify this flag if you are not using a manifest file. "
            "Useful if your manifest values are merged with checkbox.conf"
        ),
    )
    opt_launcher.set_defaults(need_manifest=True)
    opt_launcher.add_argument(
        "--checkbox-conf",
        type=file_exists,
        default=f"{script_dir}/template/checkbox.conf",
        help="Set the checkbox configuration file to build the launcher.",
    )
    opt_launcher.add_argument(
        "--launcher-template",
        type=directory_exists,
        default=f"{script_dir}/template/launcher_config/",
        help="Set the launcher template folder",
    )
    opt_tf_yaml = parser.add_argument_group("Testflinger yaml options")
    opt_tf_yaml.add_argument(
        "--launchpad-id",
        type=str,
        default="",
        help="A launchpad ID is required for reserving the machine",
    )
    opt_tf_yaml.add_argument(
        "--reserve-time",
        type=int,
        default=1200,
        help="Number of seconds to reserve the machine",
    )
    opt_tf_yaml.add_argument(
        "--tf-yaml-template",
        type=file_exists,
        default=f"{script_dir}/template/template.yaml",
        help="Set the testflinger template yaml file",
    )

    opt_shell = parser.add_argument_group("Test command in testflinger yaml")
    opt_shell.add_argument(
        "--bin-folder",
        type=directory_exists,
        default=f"{script_dir}/template/shell_scripts/",
        help="Set the testflinger test command folder",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # do a simple bool conversion instead of testing each condition + default
    is_reserve = bool(args.launchpad_id)
    is_provision = bool(args.provision_image)
    is_run_test = bool(args.test_plan)
    is_dist_upgrade = bool(args.dist_upgrade)

    if os.path.splitext(args.output_file_name)[1] in (".yaml", ".yml"):
        tf_yaml_file_path = Path(args.output_folder) / Path(
            args.output_file_name
        )
    else:
        tf_yaml_file_path = Path(args.output_folder) / Path(
            f"{args.output_file_name}.yaml"
        )

    builder = TFYamlBuilder(
        cid=args.CID,
        default_yaml_file_path=args.tf_yaml_template,
        global_timeout=args.global_timeout,
        output_timeout=args.output_timeout,
        template_bin_folder=args.bin_folder,
        launcher_temp_folder=args.launcher_template,
        is_run_test=is_run_test,
        need_manifest=args.need_manifest,
        is_dist_upgrade=is_dist_upgrade,
    )

    builder.provision_setting(
        is_provision=is_provision,
        image=args.provision_image,
        provision_type=args.provision_type,
        provision_token=args.provision_token,
        provision_user_data=args.provision_user_data,
        provision_auth_keys=args.provision_auth_keys,
    )
    if args.provision_only:
        # remove test and reserve stages that were added by default
        builder.yaml_generator.yaml_remove_field("test_data")
        builder.yaml_generator.yaml_remove_field("reserve_data")
    else:
        builder.reserve_setting(
            is_reserve=is_reserve,
            lp_username=args.launchpad_id,
            timeout=args.reserve_time,
        )

        builder.test_cmd_setting(
            manifest_json_path=args.manifest_json,
            checkbox_conf_path=args.checkbox_conf,
            test_plan_name=args.test_plan,
            exclude_job_pattern_str=args.exclude_jobs,
            checkbox_type=args.checkbox_type,
            session_desc=args.session_desc,
        )

    builder.yaml_generator.generate_yaml_file(file_path=tf_yaml_file_path)
