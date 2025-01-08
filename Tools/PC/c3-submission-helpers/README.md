# C3 Submission Helpers

This folder contains helper scripts that makes reading C3
submission files more friendly for humans.

## `parse-suspend-30-logs.py`

This file helps break down the `com.canonical.certification__
stress-tests_suspend-30-cycles-
with-reboot-3-log-attach` to a more human friendly format.

Examples:

- ```bash
  python3 parse-suspend-30-logs.py -f path/to/submission-202408-12345.tar.xz
  ```

   will print out the **indexes** (starts at 1) of the runs with failures.

- ```bash
  python3 parse-suspend-30-logs.py \
      -f path/to/submission-202408-12345.tar.xz \
      -w
  ```

   will print the output from above AND write the individual runs into its own
   file.
  - A new directory will be created in the current working directory named
   "submission-202408-12345.tar.xz-split" and there will be
   90 files inside named `1.txt, 2.txt, ..., 90.txt`

- ```bash
   python3 parse-suspend-30-logs.py \
       -f path/to/submission-202408-12345.tar.xz \
       -w \
       -d path/to/output/dir
   ```

   Specify an output directory of where the 1.txt, 2.txt... will be saved to.
   If this directory doesn't exist, the script will try to create it.

## `summarize_reboot_check_test.py`

This script combines all the results from cold & warm boot tests that uses the
new `reboot_check_test.py`.

<!-- markdownlint-disable MD013 -->
```plaintext
usage: summarize-reboot-check-test.py [-h] [-g] [-v] [-n EXPECTED_N_RUNS] filename

Parses the outputs of reboot_check_test.py from a C3 submission tar file

positional arguments:
  filename              path to the stress test tarball

options:
  -h, --help            show this help message and exit
  -g, --group-by-err    Group run-indices by error messages. Similar messages might be shown twice
  -v, --verbose         Whether to print detailed messages
  -n EXPECTED_N_RUNS, --num-runs EXPECTED_N_RUNS
                        Specify a value to show a warning when the number of boot files != the number of runs you expect. Default=30. Note that this number applies to both cold and
                        warm boot since checkbox doesn't use a different number for CB/WB either.
```
<!-- markdownlint-enable MD013 -->

Example usage:

```bash
python3 summarize_reboot_check_test.py -g /path/to/stress/test/submission.tar.xz
```
