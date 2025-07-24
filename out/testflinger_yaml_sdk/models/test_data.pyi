from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, overload

from _typeshed import Incomplete

@dataclass(slots=True)
class TestData:
    test_cmds: list[str] | str

class BuiltInTestSteps(StrEnum):
    INITIAL = "00_initial"
    DIST_UPGRADE = "01_dist_upgrade"
    INSTALL_CHECKBOX_DEB = "02_install_checkbox_deb"
    INSTALL_CHECKBOX_SNAP = "02_install_checkbox_snap"
    INSTALL_CHECKBOX_ON_TF_AGENT = "15_install_checkbox_on_agent"
    BEFORE_TEST = "20_before_test"
    START_TEST = "90_start_test"

class TestCommandBuilder:
    TEMPLATE_DIR: Final[str]
    checkbox_type: Literal["snap", "deb"]
    do_dist_upgrade: bool
    manifest_override: dict[str, bool] | None
    @classmethod
    def build_run_command(cls, command: str): ...
    checkbox_conf: Incomplete
    inserted_command_strings: dict[BuiltInTestSteps, str]
    replaced_command_strings: dict[BuiltInTestSteps, str]
    def __init__(
        self,
        checkbox_type: Literal["snap", "deb"] = "deb",
        run_checkbox: bool = True,
        do_dist_upgrade: bool = False,
        manifest_override: dict[str, bool] | None = None,
    ) -> None: ...
    def set_test_plan(self, test_plan_name: str) -> Self: ...
    def set_test_case_exclude(self, exclude_pattern: str) -> Self: ...
    @overload
    def insert_commands_before(
        self, step: BuiltInTestSteps, commands: list[Path]
    ) -> Self: ...
    @overload
    def insert_commands_before(
        self, step: BuiltInTestSteps, commands: list[str]
    ) -> Self: ...
    def replace_step(
        self, step: BuiltInTestSteps, commands: list[Path] | list[str]
    ) -> Self: ...
    def finish_build(self, skip_shellcheck: bool = False) -> TestData: ...
