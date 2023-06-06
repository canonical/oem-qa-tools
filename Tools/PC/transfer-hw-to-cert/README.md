# transfer-hw-to-cert

This tool handles the automated procedure of Hardware Transering to Cert Lab.

Please see this [Jira Card](https://warthogs.atlassian.net/browse/CQT-1912) for more details

## How To Use

<!-- markdownlint-configure-file { "MD013": { "line_length": 100 } } -->
This tool is depend on [Jira](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira) and
[GoogleSheet](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet) APIs services.

Please see [example section](#example) to learn how to use it.

### APIs preparation

Please follow API's README to set them up.

- [Jira Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/Jira/README.md)
- [GoogleSheet Readme](https://github.com/canonical/oem-qa-tools/blob/main/API/GoogleSheet/README.md)

To sum up, the `api access token` for `Jira` and `service-account`
or `OAuth credentials` for `GoogleSheet` are must needed.

### Structure

```sh
.
├── cert_team_google_sheet_handler.py
├── configs
│   └── google_sheet_link.json
├── __init__.py
├── jira_card_handler.py
├── main.py
├── README.md
├── setup.sh
├── tests
│   ├── __init__.py
│   ├── mock_import.py
│   ├── test_cert_team_google_sheet_handler.py
│   ├── test_data
│   │   ├── __init__.py
│   │   └── jira_card_handler_data.py
│   │       ├── __init__.cpython-310.pyc
│   │       └── jira_card_handler_data.cpython-310.pyc
│   ├── test_jira_card_handler.py
│   └── test_utils_common.py
└── utils
    ├── common.py
    └── __init__.py
```

Here is a brief explanation about each part:

- `configs`: The configure files used by this tool
- `utils`: The directory to store small and helpful tools
- `tests`: The directory of test scripts
- `setup.sh`: The script helps you to create running environment
- `main.py`: The `entry script` for this tool
- `jira_card_handler.py`: The script is responsible for getting the content from specific Jira Card
- `cert_team_google_sheet_handler.py`: The script is responsible for updating the Cert Lab Google Sheet

### Example

#### 0. Setup virtual environment

```sh
source setup.sh
```

- After finishing the step above, don't forget to put the configures to the right place. See [APIs preparation](#apis-preparation)

#### 1. Show help message

```sh
$ python main.py -h
usage: main.py [-h] -k KEY

options:
  -h, --help         show this help message and exit
  -k KEY, --key KEY  The key string of specific Jira Card. e.g. CQT-2023
```

#### 2. Start the procedure

```sh
# Get the content from CQT-1234 Jira Card and update Cert Lab Google Sheet
python main.py -k CQT-1234
```

## Contributing

All of the helpful documents can be found on Google Drive - [Transfer HW To Cert](https://drive.google.com/drive/folders/1xh6ceRl5fILwn4c5Kd755IWUtqA7GwJS?usp=share_link)

- Jira: [Vic's Sandbox](https://warthogs.atlassian.net/jira/software/projects/VS/boards/577)
- Cert Lab Google Sheet: [Clone - Machine in Certification Lab](https://docs.google.com/spreadsheets/d/14LouOL8as5fPaCWcat_lpsufLmzOsKVjCNNztiOrR0c/edit#gid=0)

Please make sure the test cases are passed before commit.

### Unit Test

``` sh
$ pwd
# /oem-qa-tools/Tools/PC/transfer-hw-to-cert

# Execute unit test
$ python -m unittest -v
```

## TODOs

- [] Upate C3 holder
- [] Add more test case for cert_team_google_sheet_handler.py
- [] Finish the task listed on Jira [CQT-1912](https://warthogs.atlassian.net/browse/CQT-1912)
