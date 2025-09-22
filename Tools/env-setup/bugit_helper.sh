#!/bin/bash

CID=$1
C3_PROXY=""

MACHINE_INFO=$(curl -sL "${C3_PROXY}/api/v2/machines/${CID}")

echo "${MACHINE_INFO}" | jq -r \
'. | .projects[0].name |= ascii_upcase | "#!/bin/bash\nbugit.bugit-v2 jira -p \(.projects[0].name) --platform-tags \"\(.launchpad_tag)\" -k \(.canonical_label) -c \(.canonical_id)"' \
> jira_bug.sh

echo "${MACHINE_INFO}" | jq -r \
'. | .projects[0].name |= ascii_downcase | "#!/bin/bash\nbugit.bugit-v2 -p \(.projects[0].name) -t \"\(.launchpad_tag)\" -k \(.canonical_label) -c \(.canonical_id)"' \
> lp_bug.sh

echo "${MACHINE_INFO}" | jq -r '. | {canonical_id, secure_id, canonical_label}' > hardware_info.json
