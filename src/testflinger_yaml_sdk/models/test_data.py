import json
import re
import shutil
from configparser import ConfigParser
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import read_text
from io import StringIO
from pathlib import Path
from subprocess import check_call
from tempfile import NamedTemporaryFile
from typing import Final, Literal, Self, final, overload

import testflinger_yaml_sdk  # only here for read_text to consume


@dataclass(slots=True)
class TestData:
    # if using a plain string, each command needs to be newline separated
    test_cmds: list[str] | str


class BuiltInTestSteps(StrEnum):
    # exports utility functions and variables, must be included
    INITIAL = "00_initial"
    # run dist_upgrade if specified
    DIST_UPGRADE = "01_dist_upgrade"
    # install checkbox deb or snap, only one of them should be used
    INSTALL_CHECKBOX_DEB = "02_install_checkbox_deb"
    INSTALL_CHECKBOX_SNAP = "02_install_checkbox_snap"
    # install checkbox control on the testflinger agent
    INSTALL_CHECKBOX_ON_TF_AGENT = "15_install_checkbox_on_agent"
    # by default this just reboots the DUT and waits for ssh to be ready
    BEFORE_TEST = "20_before_test"
    # this step actually runs `checkbox-cli control`
    # and submits the tarball to c3
    START_TEST = "90_start_test"


@final
class TestCommandBuilder:
    # use importlib.resources to read this dir, don't open() it directly
    TEMPLATE_DIR: Final = "template"

    checkbox_type: Literal["snap", "deb"]
    do_dist_upgrade: bool
    manifest_override: dict[str, bool] | None

    @classmethod
    def build_run_command(cls, command: str):
        """
        Translate a plain command to one that can be sent by testflinger to
        be run on the DUT

        :param command: the "local" version of the command to run on the DUT
        :return: the testflinger version of the command
        """
        return (
            f'ssh -t $SSH_OPTS $TARGET_DEVICE_USERNAME@"$DEVICE_IP" {command}'
        )

    def __init__(
        self,
        checkbox_type: Literal["snap", "deb"] = "deb",
        run_checkbox: bool = True,
        do_dist_upgrade: bool = False,
        manifest_override: dict[str, bool] | None = None,
    ) -> None:
        """
        An OOP builder for the test_cmds section
        - The basic idea is to separate each step in test_cmds into smaller
          shell files to allow them to be combined in a modular way
        - The built-in ones are loaded by their number prefix
        - The scripts are combined in alphabetical order (hence the
          number prefix)

        :param checkbox_type: debian or snap checkbox
        :param do_dist_upgrade: do a dist upgrade immediately after basic setup
          in 00_initial
        """
        # have to get checkbox_type from the constructor since only 1 of them
        # should be installed
        assert checkbox_type in (
            "snap",
            "deb",
        ), f"Bad checkbox type: {checkbox_type}"

        self.checkbox_type = checkbox_type
        self.do_dist_upgrade = do_dist_upgrade
        self.manifest_override = manifest_override
        self.checkbox_conf = ConfigParser()
        self.checkbox_conf.read_string(
            read_text(
                testflinger_yaml_sdk, f"{self.TEMPLATE_DIR}/checkbox.conf"
            )
        )
        self.inserted_command_strings: dict[BuiltInTestSteps, str] = {}
        self.replaced_command_strings: dict[BuiltInTestSteps, str] = {}

    def set_test_plan(self, test_plan_name: str) -> Self:
        if "::" not in test_plan_name:
            raise ValueError(
                f"Namespace must be included, got: {test_plan_name}"
            )
        self.checkbox_conf["test plan"]["unit"] = test_plan_name
        return self

    def set_test_case_exclude(self, exclude_pattern: str) -> Self:
        _ = re.compile(exclude_pattern)  # this will raise on invalid patterns
        self.checkbox_conf["test selection"]["exclude"] = exclude_pattern
        return self

    @overload
    def insert_commands_before(
        self, step: BuiltInTestSteps, commands: list[Path]
    ) -> Self: ...

    @overload
    def insert_commands_before(
        self, step: BuiltInTestSteps, commands: list[str]
    ) -> Self: ...

    def insert_commands_before(
        self, step: BuiltInTestSteps, commands: list[Path] | list[str]
    ) -> Self:
        """
        Inserts the commands in file_path BEFORE the specified `step`
        - Check the 00_initial file to see built-in functions like _run, _put
        - This is useful if you want to keep the original steps but just add a
          few more commands before it. If you need to completely rewrite a step
          use self.replace_step()

        :param step: insert the commands before this step
        :param file_path: one of the following
            - list[Path] paths to the shell files
            - list[str] literal command strings to append
        :rases FileNotFoundError: if any of the path in file_paths is not found
        """
        self.inserted_command_strings[step] = ""
        self.replaced_command_strings[step] = ""

        for file_paths_or_cmd_strs in commands:
            if type(file_paths_or_cmd_strs) is str:
                self.inserted_command_strings[step] += file_paths_or_cmd_strs

            elif type(file_paths_or_cmd_strs) is Path:
                if not file_paths_or_cmd_strs.exists():
                    raise FileNotFoundError(
                        f"{file_paths_or_cmd_strs} not found"
                    )
                if not file_paths_or_cmd_strs.is_file():
                    raise FileNotFoundError(
                        f"{file_paths_or_cmd_strs} is not a file"
                    )

                with open(file_paths_or_cmd_strs) as f:
                    self.inserted_command_strings[step] += f.read()

        return self

    def replace_step(
        self, step: BuiltInTestSteps, commands: list[Path] | list[str]
    ) -> Self:
        self.inserted_command_strings[step] = ""
        self.replaced_command_strings[step] = ""

        for file_paths_or_cmd_strs in commands:
            if type(file_paths_or_cmd_strs) is str:
                self.replaced_command_strings[step] += file_paths_or_cmd_strs

            elif type(file_paths_or_cmd_strs) is Path:
                if not file_paths_or_cmd_strs.exists():
                    raise FileNotFoundError(
                        f"{file_paths_or_cmd_strs} not found"
                    )
                if not file_paths_or_cmd_strs.is_file():
                    raise FileNotFoundError(
                        f"{file_paths_or_cmd_strs} is not a file"
                    )

                with open(file_paths_or_cmd_strs) as f:
                    self.replaced_command_strings[step] += f.read()

        return self

    def finish_build(self, skip_shellcheck: bool = False) -> TestData:
        final_shell_commands: list[str] = []

        for step in BuiltInTestSteps:
            # special handling steps
            match step:
                case BuiltInTestSteps.DIST_UPGRADE:
                    if not self.do_dist_upgrade:
                        continue
                case BuiltInTestSteps.INSTALL_CHECKBOX_DEB:
                    if not self.checkbox_type == "deb":
                        continue
                case BuiltInTestSteps.INSTALL_CHECKBOX_SNAP:
                    if not self.checkbox_type == "snap":
                        continue
                case BuiltInTestSteps.INSTALL_CHECKBOX_ON_TF_AGENT:
                    # write the new checkbox conf
                    final_shell_commands.append(
                        "cat << EOF > checkbox-launcher"
                    )
                    # add manifest to launcher
                    self.checkbox_conf.add_section("manifest")
                    if self.manifest_override is not None:
                        manifest_json = self.manifest_override
                    else:
                        manifest_json: dict[str, bool] = json.loads(
                            read_text(
                                testflinger_yaml_sdk,
                                f"{self.TEMPLATE_DIR}/manifest.json",
                            )
                        )
                    assert isinstance(manifest_json, dict)
                    for key, is_true in manifest_json.items():
                        self.checkbox_conf["manifest"][key] = str(is_true)

                    with StringIO() as s:
                        self.checkbox_conf.write(s)
                        final_shell_commands.append(s.getvalue().strip())
                    # have to put newlines here
                    final_shell_commands.append("\nEOF\n")
                case _:
                    # not all cases need to be handled
                    pass

            if step in self.inserted_command_strings:
                final_shell_commands.append(
                    self.inserted_command_strings[step]
                )

            if step in self.replaced_command_strings:
                final_shell_commands.append(
                    self.inserted_command_strings[step]
                )
            else:
                final_shell_commands.append(
                    read_text(
                        testflinger_yaml_sdk,
                        f"{self.TEMPLATE_DIR}/shell_scripts/{step}",
                    )
                )

        if not skip_shellcheck and shutil.which("shellcheck") is None:
            print("Not doing shell check, it's not installed")
        else:
            with NamedTemporaryFile("w") as f:
                f.write("#! /usr/bin/bash\n")
                f.writelines(final_shell_commands)
                f.seek(0)
                check_call(["shellcheck", f.name])
                print("Shellcheck OK!")

        return TestData("\n".join(final_shell_commands).strip())
