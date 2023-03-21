# PC

PC is in charge of generating the PC task card for each platform based on project book.

## Contributing

### Prerequisite

Before developing, here are some necessary preparations you have to follow

- Copy the `somerville.json`, `stella.json` and `sutton.json` from [Lyoncore](https://git.launchpad.net/~lyoncore-team/lyoncore/+git/oem-kpitool/tree/qa_jira/config/projects) and put them under the `configs/projects/pc` directory


### Start developing

Create the real Jira card to Vic's Jira porject
``` bash
$ pwd
# /home/.../oem-qa-tools/API/Jira          

$ python -m tests.dev_create_pc_tasks 
```

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
- `TBD` - PC project testing



### Action Item

- Refactor PC scenario
