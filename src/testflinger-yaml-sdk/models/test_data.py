from dataclasses import dataclass
from importlib.resources import read_text


@dataclass
class TestData:
    # if using a plain string, each command needs to be newline separated
    test_cmds: list[str] | str


class TestCommandBuilder:
    """
    An OOP builder for the test_cmds section
    - It uses the shell scripts in the template/shell_scripts 
      directory of this library to build the final test_cmds
    - The scripts are combined in alphabetical order (hence the number prefix)
    """

    # use importlib.resources to read this
    TEMPLATE_DIR = "template/shell_scripts/"

    # def __init__(self) -> None:
    #     t = read_text("testflinger-yaml-sdk", self.TEMPLATE_DIR)
    #     print(t)
