"""
The top-level keys that appear in a testflinger job.yaml file
"""

from collections.abc import MutableMapping
from dataclasses import asdict, dataclass, field
from typing import Literal, TextIO, override, Any

import yaml
from testflinger_yaml_sdk.models.provision_data import ProvisionData
from testflinger_yaml_sdk.models.test_data import TestData
from urllib3.util import Url


@dataclass(slots=True)
class SshKeyProvider:
    # lp: launchpad
    # gh: github
    provider_name: Literal["lp", "gh"]
    username: str  # username on launchpad/github

    @override
    def __str__(self) -> str:
        # lp:some-name
        return f"{self.provider_name}:{self.username}"


@dataclass(slots=True)
class ReserveData:
    ssh_keys: list[SshKeyProvider]
    # how many seconds to reserve
    timeout: int


@dataclass(slots=True)
class FirmwareUpdateData:
    ignore_failure: bool
    version: Literal["latest"] = "latest"


@dataclass(slots=True)
class TestflingerJob:
    # basic info
    job_queue: str
    tags: list[str] = field(default_factory=list)
    global_timeout: int = 14400  # seconds
    output_timeout: int = 900  # seconds

    # the big sections
    provision_data: ProvisionData | None = None
    firmware_update_data: FirmwareUpdateData | None = None
    test_data: TestData | None = None
    # allocate_data = None
    reserve_data: ReserveData | None = None

    allocation_timeout: int = 7200
    # this needs to be a valid Url
    job_status_webhook: Url | None = None
    # Needs auth to set job priority
    # https://canonical-testflinger.readthedocs-hosted.com/latest/reference/
    # job-schema.html#test-job-schema
    job_priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        def stringify_urls(d: MutableMapping[Any, Any]):
            """
            Recursively change Url objects to string

            :param d: the dict to modify
            """
            for k, v in d.items():
                if isinstance(v, dict):
                    stringify_urls(
                        v  # pyright: ignore[reportUnknownArgumentType]
                    )
                if isinstance(v, Url):
                    d[k] = v.url

        d = asdict(self)
        stringify_urls(d)
        return d

    def dump_yaml(self, file: TextIO) -> None:
        def str_representer(
            dumper: yaml.representer.SafeRepresenter,
            s: str,
        ) -> yaml.Node:
            if "\n" in s:
                clean_lines = "\n".join(
                    [line.rstrip() for line in s.splitlines()]
                )  # Remove any trailing spaces, then put it back together again
                return dumper.represent_scalar(  # pyright: ignore[reportUnknownMemberType]
                    "tag:yaml.org,2002:str", clean_lines, style="|"
                )
            return dumper.represent_scalar(  # pyright: ignore[reportUnknownMemberType]
                "tag:yaml.org,2002:str", s
            )

        yaml.representer.SafeRepresenter.add_representer(str, str_representer)
        yaml.safe_dump(self.to_dict(), file)
