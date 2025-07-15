from dataclasses import dataclass
from urllib3.util import Url


@dataclass
class OEMAutoinstallProvisionData:
    """Schema for the `provision_data` section of a OEM Autoinstall job."""

    url: Url
    # attachments = fields.List(fields.Nested(Attachment), required=False)
    token_file: str | None
    user_data: str | None
    redeploy_cfg: str | None
    authorized_keys: str | None
    zapper_iso_url: Url | None
    zapper_iso_type: str | None
