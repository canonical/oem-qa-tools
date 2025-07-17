from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import read_text
from pathlib import Path
import re
from typing import Final, Literal, final
from configparser import ConfigParser
import testflinger_yaml_sdk


@dataclass
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
    # must be included to install checkbox control on the testflinger agent
    INSTALL_CHECKBOX_ON_TF_AGENT = "15_install_checkbox_on_agent"
    # by default this just reboots the DUT and waits for ssh to be ready
    BEFORE_TEST = "20_before_test"
    # this will actually call `checkbox-cli control`
    # it also submits the submission to c3
    START_TEST = "90_start_test"


@final
class TestCommandBuilder:
    # use importlib.resources to read this dir
    TEMPLATE_DIR: Final = "template"

    checkbox_type: Literal["snap", "deb"]
    do_dist_upgrade: bool

    def __init__(
        self,
        checkbox_type: Literal["snap", "deb"] = "deb",
        do_dist_upgrade: bool = False,
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
        self.checkbox_conf = ConfigParser()
        self.checkbox_conf.read_string(
            read_text(
                testflinger_yaml_sdk, f"{self.TEMPLATE_DIR}/checkbox.conf"
            )
        )
        self.inserted_command_files: dict[BuiltInTestSteps, list[Path]] = {}

    def set_test_plan(self, test_plan_name: str):
        if "::" not in test_plan_name:
            raise ValueError(
                f"Namespace must be included, got: {test_plan_name}"
            )
        self.checkbox_conf["test plan"]["unit"] = test_plan_name

    def set_test_case_exclude(self, exclude_pattern: str):
        _ = re.compile(exclude_pattern)  # this will raise on invalid patterns
        self.checkbox_conf["test selection"]["exclude"] = exclude_pattern

    def insert_command_files(
        self, step: BuiltInTestSteps, file_paths: list[Path]
    ) -> None:
        """
        Inserts the commands in file_path BEFORE the specified `step`
        - Check the 00_initial file to see built-in functions like _run, _put

        :param step: insert before this index
        :param file_path: paths to the shell file
        :rases FileNotFoundError: if any of the path in file_paths is not found
        """
        for file_path in file_paths:
            if not file_path.exists():
                raise FileNotFoundError(f"{file_path} not found")
            if not file_path.is_file():
                raise FileNotFoundError(f"{file_path} is not a file")

        self.inserted_command_files[step] = file_paths

    def finish_build(self) -> TestData:
        final_shell_scripts: list[str] = []
        for step in BuiltInTestSteps:
            if (
                step == BuiltInTestSteps.DIST_UPGRADE
                and not self.do_dist_upgrade
            ):
                continue
            if (
                step == BuiltInTestSteps.INSTALL_CHECKBOX_SNAP
                and self.checkbox_type != "snap"
            ):
                continue
            if (
                step == BuiltInTestSteps.INSTALL_CHECKBOX_DEB
                and self.checkbox_type != "deb"
            ):
                continue

            if step in self.inserted_command_files:
                for file_path in self.inserted_command_files[step]:
                    with open(file_path) as f:
                        final_shell_scripts.append(f.read())

            final_shell_scripts.append(
                read_text(
                    testflinger_yaml_sdk,
                    f"{self.TEMPLATE_DIR}/shell_scripts/{step}",
                )
            )

        return TestData("\n".join(final_shell_scripts))
