#!/bin/bash

CID=$1
C3_PROXY=""

MACHINE_INFO=$(curl -sL "${C3_PROXY}/api/v2/machines/${CID}")

echo "${MACHINE_INFO}" | jq -r \
'. | .projects[0].name |= ascii_upcase | "#!/bin/bash\nbugit -p \(.projects[0].name) --platform-tags \"\(.launchpad_tag)\" -k \(.sku) -c \(.canonical_id) --jira"' \
> jira_bug.sh

echo "${MACHINE_INFO}" | jq -r \
'. | .projects[0].name |= ascii_downcase | "#!/bin/bash\nbugit -p \(.projects[0].name) -t \"\(.launchpad_tag)\" -k \(.sku) -c \(.canonical_id)"' \
> lp_bug.sh

echo "${MACHINE_INFO}" | jq -r '. | {canonical_id, secure_id, sku}' > hardware_info.json
