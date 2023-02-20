# Jira

Jira is a tool to generate the task cards on Canonical Jira Service.

You can find some interesting use cases under scenarios folder.

## Structure

```
.
├── apis
├── configs
    ├── jira_config
    └── projects
        └── pc
├── scenarios
    └── pc
├── tests
└── utils
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

For more detail of preparation, please visit this [docs](https://not-creat-yet)

### Start developing

If you are working on a `huge project`, I highly recommend you put your business logic under `scenarios` directory, `pc project` for instance.

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
