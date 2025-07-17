from dataclasses import dataclass
from pathlib import Path
from urllib3.util import Url


@dataclass
class Attachment:
    local: Path  # verifiable, can check if the file exists, readable etc.
    agent: Path | None  # unverifiable, can only do basic checks


@dataclass
class SimpleUrlProvisionData:
    url: Url
    attachments: list[Attachment] = []


@dataclass
class SimpleDistroProvisionData:
    # https://canonical-testflinger.readthedocs-hosted.com/en/latest/reference/
    # test-phases.html#provision
    distro: str = "noble"  # jammy seems to still work
    kernel: str | None = None  #  hwe-22.04
    attachments: list[Attachment] = []


@dataclass
class OEMAutoInstallProvisionData:
    # https://canonical-testflinger.readthedocs-hosted.com/en/latest/
    # reference/device-connector-types.html#oem-autoinstall
    url: Url
    # token_file must be specified if url requires auth
    # the format is listed in the testflinger doc linked above
    token_file: Path
    # user_data file should contain info for autoinstall and cloud-init
    user_data: Path
    # authorized_keys file will literally be copied to the DUT
    authorized_keys: Path


# add more here if needed
ProvisionData = (
    SimpleDistroProvisionData
    | SimpleUrlProvisionData
    | OEMAutoInstallProvisionData
)
