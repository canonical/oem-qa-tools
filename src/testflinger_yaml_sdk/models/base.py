"""
The top-level keys that appear in a testflinger job.yaml file
"""

from dataclasses import dataclass
from typing import Literal, override

from testflinger_yaml_sdk.models.provision_data import ProvisionData
from testflinger_yaml_sdk.models.test_data import TestData


@dataclass
class SshKeyProvider:
    # lp: launchpad
    # gh: github
    provider_name: Literal["lp", "gh"]
    username: str  # username on launchpad/github

    @override
    def __str__(self) -> str:
        # lp:some-name
        return f"{self.provider_name}:{self.username}"


@dataclass
class ReserveData:
    ssh_keys: list[SshKeyProvider]
    # how many seconds to reserve
    timeout: int


@dataclass
class FirmwareUpdateData:
    version: Literal["latest"]
    ignore_failure: bool


@dataclass
class TestflingerJob:
    job_queue: str
    tags: list[str] | None = None
    global_timeout: int = 14400
    output_timeout: int = 900

    provision_data: ProvisionData | None = None
    firmware_update_data: FirmwareUpdateData | None = None
    test_data: TestData | None = None
    allocate_data = None
    reserve_data: ReserveData | None = None

    allocation_timeout: int = 7200
    job_status_webhook: str | None = None
    job_priority: int = 0
