"""
The top-level keys that appear in a testflinger job.yaml file
"""

from dataclasses import dataclass, field
from typing import Literal, override
from urllib3.util import Url
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
    ignore_failure: bool
    version: Literal["latest"] = "latest"


@dataclass
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
