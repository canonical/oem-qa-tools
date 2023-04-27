# C3

C3 is a tool to interact with the Certification Canonical website.


## Structure

```
.
├── apis
│   ├── base.py
│   └── __init__.py
├── configs
│   ├── api_token.json
│   └── c3_conf.json
├── __init_.py
├── README.md
├── tests
│   ├── dev_c3.py
│   └── __init__.py
└── utils
    ├── __init__.py
    └── logging_utils.py
```

Here is a brief explanation about each part:

- `apis`: The wrapper of C3 API
- `configs`: Configs for C3
- `tests`: The unittest scripts folder
- `utils`: Helpful functions

## Contributing

### Prerequisite

Before developing, here are some necessary preparations you have to follow

- Generate your C3 api token and put it into `api_token.json` file, you can find it under the `configs` directory
  - Content of `api_token.json`
    ```json
    {
        "launchpad_id": "<launchpad_id>",
        "api_token": "<c3_api_token>"
    }
    ```
  - Get the token by visiting C3 website
    - Production: https://certification.canonical.com/me/
    - Staging: https://certification.staging.canonical.com/me/

### Start developing

### Testing

Please make sure the test cases are passed before commit.

- Once you update the codes in `apis` directory.
    ``` bash
    # Change direcotry to C3
    $ pwd
    # /home/.../oem-qa-tools/API/C3

    # Play the methods
    $ python -m tests.dev_c3

    # Execute unit test
    $ python -m unittest -v
    ```
