from dataclasses import asdict
import testflinger_yaml_sdk.models as tfm
from urllib3.util import parse_url

uu = "https://tel-image-cache.canonical.com/oem-share/stella/releases/noble/oem-24.04b/20250716-539/stella-noble-oem-24.04b-20250716-539.iso"
j = tfm.TestflingerJob(
    job_queue="bah",
    provision_data=tfm.SimpleUrlProvisionData(
        url=parse_url(uu),
    ),
)

print(asdict(j))
