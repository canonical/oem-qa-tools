# jira-card-creator

jira-card-creator is a tool to generate QA PC task cards on Canonical Jira Service.

This tool creates card based on Project Books.

## How To Use

This tool is depend on [Jira](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira) and [GoogleSheet](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet) APIs services. Please `Copy` these two APIs to this directory, you will see the following structure before you start.

### APIs preparation

Please follow API's README to set them up.
- [Jira Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira/README.md)
- [GoogleSheet Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet/README.md)

To sum up, the `api access token` for `Jira` and `service-account` or `OAuth credentials` for `GoogleSheet` are must needed.

### Structure
```
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

```bash
$ source setup.sh
```

#### 1. Show help message

```bash
$ python create_qa_jira_card.py -h
usage: create_qa_jira_card.py [-h] -p {sutton,somerville,stella,all} [-d]

optional arguments:
  -h, --help            show this help message and exit
  -p {sutton,somerville,stella,all}, --project {sutton,somerville,stella,all}
                        select one of supported projects
  -o {console,file}, --output {console,file}
                        select one of supported output type. Default is 'console', it will show you the result on console in JSON format.
                        Option 'file' will log the data to 'output.json' file
  -d, --dry-run         get project data from project book only, won't create Jira Card
```

#### 2. Get Somerville data and create Jira task card

```bash
$ pwd
# /oem-qa-tools/Tools/PC/jira-card-creator
$ python create_qa_jira_card.py -p somerville
```

#### 3. `Dry run` to get Somerville data from Project book only

```bash
$ pwd
# /oem-qa-tools/Tools/PC/jira-card-creator
$ python create_qa_jira_card.py -p somerville -d
```

## Contributing

Please make sure the test cases are passed before commit.

`Dry run` is a super helpful way to get and check the information from project book. Please reference Example 3 to see how to use it.

### Unit Test

``` bash
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
