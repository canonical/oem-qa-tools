# jira-card-creator

jira-card-creator is a tool to generate QA PC task cards on Canonical Jira Service.

This tool creates card based on Project Books.

## How To Use

<!-- markdownlint-configure-file { "MD013": { "line_length": 100 } } -->
This tool is depend on [Jira](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira) and
[GoogleSheet](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet) APIs services.

Please see [example section](#example) to learn how to use it.

### APIs preparation

Please follow API's README to set them up.
<!-- markdownlint-configure-file { "MD013": { "line_length": 90 } } -->
- [Jira Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira/README.md)
<!-- markdownlint-configure-file { "MD013": { "line_length": 110 } } -->
- [GoogleSheet Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet/README.md)

To sum up, the `api access token` for `Jira` and `service-account`
or `OAuth credentials` for `GoogleSheet` are must needed.

### Structure

```sh
.
├── Jira
├── GoogleSheet
├── configs
    └── google_sheet_link.json
├── tests
├── pc_platform_tracker.py
├── setup.sh
└── create_qa_jira_card.py
```

Here is a brief explanation about each part:

- `Jira`: The Jira API service
- `GoogleSheet`: The GoogleSheet API service
- `configs`: The configure files used by this tool
- `setup.sh`: The script helps you to create running environment
- `create_qa_jira_card.py`: The `entry scripts` for this tool

### Example

#### 0. Setup virtual environment

```sh
source setup.sh
```

- After finishing the step above, don't forget to put the configures
  to the right place. See [APIs preparation](#apis-preparation)
- You will see the [structure](#structure) before you start.

#### 1. Show help message

```sh
$ python create_qa_jira_card.py -h
usage: create_qa_jira_card.py [-h] -p {sutton,somerville,stella,all} [-d]

optional arguments:
  -h, --help            show this help message and exit
  -p {sutton,somerville,stella,all}, --project {sutton,somerville,stella,all}
                        select one of supported projects
  -o {console,file}, --output {console,file}
                        select one of supported output type. Default is 'console',
                        it will show you the result on console in JSON format.
                        Option 'file' will log the data to 'output.json' file
  -d, --dry-run         get project data from project book only, won't create Jira Card
```

#### 2. Get Somerville data and create Jira task card

```sh
$ pwd
# /oem-qa-tools/Tools/PC/jira-card-creator
$ python create_qa_jira_card.py -p somerville
```

#### 3. `Dry run` to get Somerville data from Project book only

```sh
$ pwd
# /oem-qa-tools/Tools/PC/jira-card-creator
$ python create_qa_jira_card.py -p somerville -d
```

## Contributing

Please make sure the test cases are passed before commit.

`Dry run` is a super helpful way to get and check the information
from project book. Please reference Example 3 to see how to use it.

### Unit Test

```sh
$ pwd
# /oem-qa-tools/Tools/PC/jira-card-creator

# Execute unit test
$ python -m unittest -v tests.test_create_qa_jira_card
```

### Integration Test

TBD

## TODOs

- [] Add unit test for pc_platform_tracker.py
- [] Add integration test
