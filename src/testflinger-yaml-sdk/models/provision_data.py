from dataclasses import dataclass
from pathlib import Path
from urllib3.util import Url


@dataclass
class Attachment:
    local: Path  # verifiable, can check if the file exists, readable etc.
    agent: Path | None  # unverifiable, can only do basic checks


@dataclass
class UrlProvisionData:
    url: Url
    attachments: list[Attachment] = []


@dataclass
class DistroProvisionData:
    distro: str = "noble"
    kernel: str | None = None
    attachments: list[Attachment] = []


@dataclass
class OEMAutoInstallProvisionData:
    url: Url
    # token_file must be specified if url requires auth
    token_file: Path 
    # user_data should contain directives for autoinstall and cloud-init
    # https://canonical-testflinger.readthedocs-hosted.com/en/latest/
    # reference/device-connector-types.html#oem-autoinstall
    user_data: Path
    # authorized keys file will literally be copied to the DUT
    authorized_keys: Path

type ProvisionData = DistroProvisionData | DistroProvisionData | OEMAutoInstallProvisionData
