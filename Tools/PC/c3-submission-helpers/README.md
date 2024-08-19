# C3 Submission Helpers

This folder contains helper scripts that makes reading C3
submission files more friendly for humans.

## `parse-suspend-30-logs.py`

This file helps break down the `com.canonical.certification__
stress-tests_suspend-30-cycles-
with-reboot-3-log-attach` to a more human friendly format.

Examples:

- `python3 parse-suspend-30-logs.py -f path/to/submission-202408-12345.tar`
will print out the **indexes** (starts at 1) of the runs with failures.
- `python3 parse-suspend-30-logs.py -f path/to/submission-202408-12345.tar -w`
will print the output from above AND write the individual runs into its own
file.
  - A new directory will be created in "." with the name
   "submission-202408-12345.tar-split" and there will be
   90 files inside named `1.txt, 2.txt, ..., 90.txt`
  
## `cbwb-diffs.py`

This script should be run on the DUT (for now).
It compares the device lists generated during cold boot/warm boot
tests and provides options to re-group them to help with readability

Examples:

- `python3 cbwb-diffs.py -p
/var/tmp/checkbox-ng/sessions/session_title-2024-08-12T09.16.15.
session` shows the diffs in this session grouped by index.

- `python3 cbwb-diffs.py -p path/to/session/share
   -g log-name` shows the diffs grouped by log names.
