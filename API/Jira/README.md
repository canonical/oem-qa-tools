# Jira

Jira is a tool to generate the task cards on Canonical Jira Service.

You can find some interesting use cases under scenarios folder.

## Structure

```
.
├── apis
│   ├── base.py
│   └── __init__.py
├── configs
│   └── jira_config
│       └── project.json
├── __init__.py
├── README.md
├── scenarios
│   ├── __init__.py
│   └── pc
│       ├── configs
│       │   ├── somerville.json
│       │   ├── stella.json
│       │   └── sutton.json
│       ├── __init__.py
│       ├── pc.py
│       ├── README.md
│       └── templates
│           ├── __init__.py
│           └── transfer_hw_template.py
├── tests
│   ├── dev_create_pc_tasks.py
│   ├── __init__.py
│   ├── test_base_api.py
│   └── testing_data.json
└── utils
    ├── __init__.py
    └── logging_utils.py
```

Here is a brief explanation about each part:

- `apis`: The wrapper of Jira API
- `configs`: Configs for Jira and projects
- `scenarios`: The business logic for different purposes
- `tests`: The unittest scripts folder
- `utils`: Helpful functions

## Contributing

### Prerequisite

Before developing, here are some necessary preparations you have to follow

- Make sure you have the permission to access the [Vic's Sandbox](https://warthogs.atlassian.net/jira/software/projects/VS/boards/577) Jira project
- Generate your Jira api token named `api_token.json` and put it under the `configs/jira_config` directory
- Copy the `members.json` from [Lyoncore](https://git.launchpad.net/~lyoncore-team/lyoncore/+git/oem-kpitool/tree/qa_jira/config/jira_config) and put it under the `configs/jira_config` directory

For more detail of preparation, please visit this [QA Jira API Guide Line](https://docs.google.com/document/d/1s5CV6HqIWiPed2jJxGrcg49A-zJlX7yhIRMZoBbruho/edit?usp=sharing)

### Start developing

If you are working on a `huge project`, I highly recommend you put your business logic under `scenarios` directory, `pc project` for instance.
  - [jira-card-creator](https://github.com/canonical/oem-qa-tools/tree/main/Tools/PC/jira-card-creator) is a good example to learn how to leverage APIs with your idea.

Otherwise, please put your code snippet under `Tools` directory.

### Testing

Please make sure the test cases are passed before commit.

- Once you update the codes in `apis` directory.
    ``` bash
    # Change direcotry to Jira
    $ pwd
    # /home/.../oem-qa-tools/API/Jira

    # Execute unit test
    $ python -m unittest -v tests.test_base_api
    ```
- If you're developing your own scenario, please add the relevant test case.
