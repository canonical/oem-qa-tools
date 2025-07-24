from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import SplitResult as SplitResult

@dataclass(slots=True)
class Attachment:
    local: Path
    agent: Path | None

@dataclass(slots=True)
class SimpleUrlProvisionData:
    url: SplitResult
    attachments: list[Attachment] = field(default_factory=list)

@dataclass(slots=True)
class SimpleDistroProvisionData:
    distro: str = ...
    kernel: str | None = ...
    attachments: list[Attachment] = field(default_factory=list)

@dataclass(slots=True)
class OEMAutoInstallProvisionData:
    url: SplitResult
    token_file: Path
    user_data: Path
    authorized_keys: Path

ProvisionData = (
    SimpleDistroProvisionData
    | SimpleUrlProvisionData
    | OEMAutoInstallProvisionData
)
