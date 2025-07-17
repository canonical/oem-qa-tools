from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import read_text
from pathlib import Path
from typing import Literal, final
from configparser import ConfigParser


@dataclass
class TestData:
    # if using a plain string, each command needs to be newline separated
    test_cmds: list[str] | str


@final
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


class TestCommandBuilder:
    # use importlib.resources to read this dir
    TEMPLATE_DIR = "template"

    def __init__(
        self,
        checkbox_type: Literal["snap", "deb"] = "deb",
        do_dist_upgrade=False,
    ) -> None:
        """
        An OOP builder for the test_cmds section
        - The basic idea is to separate each step in test_cmds into smaller
          shell files to allow them to be combined in a modular way
        - The built-in ones are loaded by their number prefix
        - The scripts are combined in alphabetical order (hence the
          number prefix)

        :param checkbox_type: debian or snap checkbox
        :param do_dist_upgrade: do a dist upgrade immediately after t
        """
        # have to get checkbox_type from the constructor since only 1 of them
        # should be installed
        assert checkbox_type in ("snap", "deb")
        self.checkbox_type = checkbox_type
        self.do_dist_upgrade = do_dist_upgrade
        self.checkbox_conf = ConfigParser()
        self.checkbox_conf.read_string(
            read_text(
                "testflinger-yaml-sdk", f"{self.TEMPLATE_DIR}/checkbox.conf"
            )
        )
        self.inserted_command_files: dict[int, Path] = {}
    
    def set_test_plan(self, test_plan_name: str):
        self.checkbox_conf

    

    def insert_command_file(self, index: int, file_path: Path) -> None:
        """
        Inserts the commands in file_path at the specified index
        - Check the 00_initial file to see built-in functions like _run, _put

        :param index: insert before this index
        :param file_path: path to the shell file
        :rases ValueError: when index is already taken
        """
        if index in self.inserted_command_files:
            raise ValueError(f"{index} is already taken")
        self.inserted_command_files[index] = file_path

    def finish_build(self) -> TestData: ...
