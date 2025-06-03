# C3 Submission Helpers

This folder contains helper scripts that makes reading C3
submission files more friendly for humans.

## `parse-suspend-30-logs.py`

This file helps break down the `com.canonical.certification__
stress-tests_suspend-30-cycles-with-reboot-3-log-attach` to a more human friendly format.

```plaintext
usage: parse-suspend-30-logs.py [-h] [-s] [-m] [-w] [-d WRITE_DIR] [-v]
                                [-nb NUM_BOOTS] [-ns NUM_SUSPENDS] [-t] [-c] [-iw]
                                filenames [filenames ...]

positional arguments:
  filenames             The path to the stress test submission .tar files

options:
  -h, --help            show this help message and exit
  -s, --no-summary      Don't print the summary file at the top (default: False)
  -m, --no-meta         Don't write the metadata section when -w is specified. (The
                        date/time/kernel section) (default: False)
  -w, --write-individual-files
                        If specified, the logs will be split up into individual
                        files in a directory specified with -d (default: False)
  -d WRITE_DIR, --directory WRITE_DIR
                        The top level dir of where to write the individual logs.
                        Inside this directory, subdirectories called {your original
                        file name}-split will be created to contain the individual
                        .txt files of each run (default: /your/current/directory)
  -v, --verbose         Show line numbers of where the errors are in th input file
                        (default: False)
  -nb NUM_BOOTS, --num-boots NUM_BOOTS
                        Set the expected number of boots in the input file.
                        (default: 3)
  -ns NUM_SUSPENDS, --num-suspends-per-boot NUM_SUSPENDS
                        Set the expected number of runs in the input file. (default:
                        30)
  -t, --no-transform    Disables any form of error message tranformation except
                        trimming whitespaces. By default, this script will attempt
                        to remove timestamps and certain numbers to better group the
                        error messages. This option disables this behavior.
                        (default: False)
  -c, --no-color        Disables all colors and styles (default: False)
  -iw, --ignore-warnings
                        Ignore warnings like checkbox's sleep_test_log_check.py
                        (default: False)

```

Examples:

- ```bash
  python3 parse-suspend-30-logs.py path/to/submission-202408-12345.tar.xz
  ```

  will print out error messages and the associated failed run/boot index

- ```bash
  python3 parse-suspend-30-logs.py \
      path/to/submission-202408-12345.tar.xz \
      -w
  ```

  will print the output from above AND write the individual runs into its own
  file.

  - A new directory will be created in the current working directory named
    "submission-202408-12345.tar.xz-split" and there will be
    90 files inside named `boot-1-suspend-1.txt, boot-1-suspend-2.txt, ..., boot-3-suspend-30.txt`

- ```bash
   python3 parse-suspend-30-logs.py \
       path/to/submission-202408-12345.tar.xz \
       -w \
       -d path/to/output/dir
  ```

  Specify a top level output directory of where the individual files will be written to.
  If this directory doesn't exist, the script will try to create it.

## `summarize_reboot_check_test.py`

This script combines all the results from cold & warm boot tests that uses the
new `reboot_check_test.py`.

<!-- markdownlint-disable MD013 -->

```plaintext
usage: summarize-reboot-check-test.py [-h] [-g] [-i] [-v] [-n EXPECTED_N_RUNS]
                                      [--no-color]
                                      filenames [filenames ...]

Parses the outputs of reboot_check_test.py from a C3 submission tar file

positional arguments:
  filenames             Path to the stress test tarball. If multiple paths are
                        specified, run the script for each of them

options:
  -h, --help            show this help message and exit
  -g, --group-by-err    Group run-indices by error messages. Similar messages might
                        be shown twice (default: False)
  -i, --index-only      Only show the indices of the failed runs (default: False)
  -v, --verbose         Whether to print detailed messages (default: False)
  -n EXPECTED_N_RUNS, --num-runs EXPECTED_N_RUNS
                        Specify a value to show a warning when the number of boot
                        files != the number of runs you expect. Note that this
                        number applies to both cold and warm boot since checkbox
                        doesn't use a different number for CB/WB. (default: 30)
  --no-color            Removes all colors and styles (default: False)

```

<!-- markdownlint-enable MD013 -->

Example usage:

```bash
python3 summarize_reboot_check_test.py /path/to/stress/test/submission.tar.xz
```

## Multiple input files

Both scripts accept multiple input files. For now they just loop through them as if the command was called for each individual file.