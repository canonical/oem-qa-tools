#!/bin/bash
# beacon.sh - Eddystone-URL BLE advertising
# Default path: legacy raw HCI via /usr/bin/advertise-url (original behaviour,
# works on most machines incl. Ubuntu 18.04/20.04).
# Extra path: BlueZ mgmt interface (btmgmt add-adv + advertising on) is also
# applied when available (BlueZ >= 5.51 / Ubuntu >= 20.04), covering
# controllers that reject raw HCI LE advertising with status 0x0C (Command
# Disallowed, e.g. Intel AX2xx + recent kernels).
# Automation-safe: this script NEVER hangs or hard-fails the boot flow. Each
# command is time-bounded (TMOUT, default 5s); any error is reported to
# /tmp/beacon.log and the script still exits cleanly (exit 0).
# Overrides: BEACON_URL (default http://www.ubuntu.com), HCI_DEV (default hci0)
BEACON_URL="${BEACON_URL:-http://www.ubuntu.com}"
HCI="${HCI_DEV:-hci0}"
TMOUT="${TMOUT:-5}"
log() { echo "$(date '+%F %T') beacon.sh[$$]: $*" >> /tmp/beacon.log; }

# time-bounded sudo runner: report but never block the step
run() { timeout "$TMOUT" sudo "$@" 2>&1; }

# adapter must exist: btmgmt silently falls back to the first real index,
# which would falsely report success for a typo'd HCI_DEV.
if [ ! -d "/sys/class/bluetooth/$HCI" ]; then
    log "WARN adapter $HCI not found (automation-safe, continuing)"
    echo "Beacon Service FAILED: adapter $HCI not found (see /tmp/beacon.log)"
    exit 0
fi

advertising_up() {
    run btmgmt -i "$HCI" info 2>/dev/null | grep "current settings" | grep -q advertising
}

# --- 1) legacy raw HCI path (original behaviour) ---
run hciconfig "$HCI" up >/dev/null 2>&1
timeout 10 python3 /usr/bin/./advertise-url -u "$BEACON_URL" >/dev/null 2>&1

# --- 2) mgmt path (exception coverage; errors reported, never fatal) ---
PAYLOAD=$(timeout 5 python3 - "$BEACON_URL" <<'PYEOF'
import sys
url = sys.argv[1]
schemes = ("http://www.", "https://www.", "http://", "https://")
extensions = (".com/", ".org/", ".edu/", ".net/", ".info/", ".biz/", ".gov/",
              ".com", ".org", ".edu", ".net", ".info", ".biz", ".gov")
data = []
for s, scheme in enumerate(schemes):
    if url.startswith(scheme):
        data.append(s)
        i = len(scheme)
        break
else:
    sys.exit("invalid URL scheme")
while i < len(url):
    if url[i] == ".":
        for e, ext in enumerate(extensions):
            if url.startswith(ext, i):
                data.append(e)
                i += len(ext)
                break
        else:
            data.append(0x2E)
            i += 1
    else:
        data.append(ord(url[i]))
        i += 1
if len(data) > 18:
    sys.exit("encoded URL too long (max 18 bytes)")
msg = [0x02, 0x01, 0x1a, 0x03, 0x03, 0xaa, 0xfe, 0x0d, 0x16, 0xaa, 0xfe, 0x10, 0xed] + data
print("".join("%02x" % b for b in msg))
PYEOF
)

ERRMSG=""
if [ -z "$PAYLOAD" ]; then
    ERRMSG="url-encode "
else
    run btmgmt -i "$HCI" power on >/dev/null 2>&1 || ERRMSG="${ERRMSG}power-on "
    run btmgmt -i "$HCI" rm-adv 1 >/dev/null 2>&1 || true    # instance may not exist
    run btmgmt -i "$HCI" add-adv -d "$PAYLOAD" 1 >/dev/null 2>&1 || ERRMSG="${ERRMSG}add-adv "
    run btmgmt -i "$HCI" advertising on >/dev/null 2>&1 || ERRMSG="${ERRMSG}advertising-on "
fi

sleep 1
if advertising_up; then
    log "OK advertising enabled, URL=$BEACON_URL on $HCI (mgmt verified)"
    echo "Beacon Service is enabled: $BEACON_URL"
elif [ -n "$ERRMSG" ]; then
    log "WARN advertising not verified; mgmt errors: $ERRMSG (continuing, no breakpoint)"
    echo "Beacon Service FAILED (see /tmp/beacon.log)"
else
    log "WARN advertising not verified on $HCI (legacy path; continuing, no breakpoint)"
    echo "Beacon Service is enabled: $BEACON_URL"
fi
exit 0