from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import read_text
from pathlib import Path
from typing import Literal, final


@dataclass
class TestData:
    # if using a plain string, each command needs to be newline separated
    test_cmds: list[str] | str


@final
class BuiltInTestSteps(StrEnum):
    INITIAL = "00_initial"
    DIST_UPGRADE = "01_dist_upgrade"
    INSTALL_CHECKBOX_DEB = "02_install_checkbox_deb"
    INSTALL_CHECKBOX_SNAP = "02_install_checkbox_snap"
    INSTALL_CHECKBOX_ON_TF_AGENT = "15_install_checkbox_on_agent"
    BEFORE_TEST = "20_before_test"
    START_TEST = "90_start_test"


class TestCommandBuilder:
    """
    An OOP builder for the test_cmds section
    - The basic idea is to separate each step in test_cmds into smaller shell
      files to allow them to be combined in a modular way
    - The built-in ones are loaded by their number prefix
    - The scripts are combined in alphabetical order (hence the number prefix)
    """

    # use importlib.resources to read this
    TEMPLATE_DIR = "template/shell_scripts/"

    def __init__(self, checkbox_type: Literal["snap", "deb"]) -> None:
        # have to get checkbox_type from the constructor since only 1 of them
        # should be installed
        assert checkbox_type in ("snap", "deb")
        self.checkbox_type = checkbox_type
        self.inserted_command_files: dict[int, Path] = {}

    def insert_command_file(self, index: int, file_path: Path) -> None:
        """
        Inserts the commands in file_path at the specified index
        - Check the 00_initial file to see built-in functions like _run, _put

        :param index: insert before this index
        :param file_path: path to the shell file
        :rases ValueError: when index is already taken
        """
        # t = read_text("testflinger-yaml-sdk", self.TEMPLATE_DIR)
        if index in self.inserted_command_files:
            raise ValueError(f"{index} is already taken")
        self.inserted_command_files[index] = file_path

    def finish_build(self) -> TestData: ...
