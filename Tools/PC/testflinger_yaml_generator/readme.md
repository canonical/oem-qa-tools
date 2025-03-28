# Ideal and the srtucture

Create seperate the template for building the yaml file, and make it more flexible.

So the template structure will like this:

- Yaml file

- Execute cmds files which will be included in test_cmds fields.

- Launcher files which is only used for checkbox testing

## Launcher

- main part:
  - launcher, ui, daemon(agent), transport, exporter, report

- env part:
  - environment (testing environment config)

- manifest part:
  - manifest (it can be config file, or json file),
    if we write the manifest in launcher,
    it will still create/overwrite the json file in DUT.

- testplan part:
  - test plan, test selection

## test cmd in yaml file

- execute bash script will be in alphabetical order
  (File’s prefix is two digital number, ie 00_xxx, …, 99_xxx)

## Usage

This script provide some arguments for generating the yaml file:
<!-- markdownlint-configure-file { "MD013": { "line_length": 200 } } -->

```text
usage: testflinger_yaml_generator.py [-h] -c CID -o OUTPUTFILENAME [--outputFolder OUTPUTFOLDER] [--dist-upgrade] [--testplan TESTPLAN] [--excludeJobs EXCLUDEJOBS]
                                     [--sessionDesc SESSIONDESC] [--checkboxType {deb,snap}] [--provisionType {distro,url}] [--provisionImage PROVISIONIMAGE]
                                     [--provisionToken PROVISIONTOKEN] [--provisionUserData PROVISIONUSERDATA] [--provisionAuthKeys PROVISIONAUTHKEYS] [--provisionOnly]
                                     [--globalTimeout GLOBALTIMEOUT] [--outputTimeout OUTPUTTIMEOUT] [--manifestJson MANIFESTJSON] [--needManifest] [--no-needManifest]
                                     [--checkboxConf CHECKBOXCONF] [--LauncherTemplate LAUNCHERTEMPLATE] [--LpID LPID] [--reserveTime RESERVETIME] [--TFYamlTemplate TFYAMLTEMPLATE]
                                     [--binFolder BINFOLDER]

Testflinger yaml file generator

options:
  -h, --help            show this help message and exit

Required:
  -c CID, --CID CID     CID (default: None)
  -o OUTPUTFILENAME, --outputFileName OUTPUTFILENAME
                        Set the output yaml file Name (default: None)

general options:
  --outputFolder OUTPUTFOLDER
                        Set the output folder path (default: ./)
  --dist-upgrade        Set to allow the dist-upgrade before run checkbox test (default: False)
  --testplan TESTPLAN   Set the checkbox test plan name. If didn't set this will not run checkbox test (default: )
  --excludeJobs EXCLUDEJOBS
                        Set the exclude jobs pattern. ie".*memory/memory_stress_ng". (default: )
  --sessionDesc SESSIONDESC
                        Set the session description (default: CE-QA-PC_Test)
  --checkboxType {deb,snap}
                        Set which checkbox type you need to install and test. (default: deb)
  --provisionType {distro,url}
                        Set the provision type (default: distro)
  --provisionImage PROVISIONIMAGE
                        The provision image. ie, desktop-22-04-2-uefi. If didn't set this mean no provision (default: )
  --provisionToken PROVISIONTOKEN
                        Optional file with username and token when image URL requires authentication (i.e Jenkins artifact). This file must be in YAML format, i.e: "username:
                        $JENKINS_USERNAME \n token: $JENKINS_API_TOKEN" (default: )
  --provisionUserData PROVISIONUSERDATA
                        user-data file for autoinstall and cloud-init provisioning. This argument is a MUST required if deploy the image using the autoinstall image (i.e. 24.04 image)
                        (default: )
  --provisionAuthKeys PROVISIONAUTHKEYS
                        ssh authorized_keys file to add in provisioned system (default: )
  --provisionOnly       Run only provisioning without tests. Removes test_data before generating the yaml. (default: False)
  --globalTimeout GLOBALTIMEOUT
                        Set the testflinger's global timeout. Max:43200 (default: 43200)
  --outputTimeout OUTPUTTIMEOUT
                        Set the output timeout if the DUT didn't response to server, it will be forced closed this job. It should be set under the global timeout. (default: 9000)

Launcher settion  options:
  --manifestJson MANIFESTJSON
                        Set the manifest json file to build the launcher. (default: $SCRIPT_PATH/template/manifest.json)
  --needManifest        Set if need the Manifest. (default: True)
  --no-needManifest
  --checkboxConf CHECKBOXCONF
                        Set the checkbox configuration file to build the launcher. (default: $SCRIPT_PATH/template/checkbox.conf)
  --LauncherTemplate LAUNCHERTEMPLATE
                        Set the launcher template folder (default: $SCRIPT_PATH/template/launcher_config/)

Testflinger yaml options:
  --LpID LPID           If you want to reserve the DUT, please input your Launchpad ID (default: )
  --reserveTime RESERVETIME
                        Set the timeout (sec) for reserve. (default: 1200)
  --TFYamlTemplate TFYAMLTEMPLATE
                        Set the testflinger template yaml file (default: $SCRIPT_PATH/template/template.yaml)

Test command in testflinger yaml:
  --binFolder BINFOLDER
                        Set the testflinger test command folder (default: $SCRIPT_PATH/template/shell_scripts/)
```

### Basically usage

we using the default timeout, and we don’t need to have insert the template
path

1. We  need to modify the `./template/shell_scripts/*` (mostly we only need to modify `20_before_test`, `99_end_test`)

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --provisionImage $IMAGE_NAME --manifestJson $MANIFEST_JSON_PATH`

1. If we only want to provision and reserve the machine:

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --provisionImage $IMAGE_NAME`

1. If we only want to test w/ noprovision:

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --manifestJson $MANIFEST_JSON_PATH`

1. If we only want to provision and w/o testcmd field

> `./testflinger_yaml_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --provisionImage $IMAGE_NAME --provisionOnly`

## How do we do for testing (w/ provision) cert lab’s DUT w/ this script

**Prepare:** CID, provision_image_name, manifest_json_file, test_plan_name.
**Modify file:** `20_before_test` (if we want to add the staging ppa repo or
something else), `99_end_test` (maybe copy some file in artifacts folder)

```sh
git clone --depth 1 --branch main git@github.com:canonical/ce-oem-dut-checkbox-configuration.git
# if `$CID` in `PC/` folder, we can use the `PC/$CID/manifest.json` and `PC/$CID/checkbox.conf`
# as `$MANIFEST_JSON_PATH` and `$CHECKBOX_CONF_PATH`
# else we can use the `PC/default/manifest.json` `PC/default/checkbox.conf` or
# `./template/manifest.json` `./template/checkbox.conf` we modify by ourselves
./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --provisionImage $IMAGE_NAME --manifestJson $MANIFEST_JSON_PATH --checkboxConf $CHECKBOX_CONF_PATH
JOB_ID=$(testflinger-cli -q $OUTPUT_YAML)
testflinger-cli poll $JOB_ID
TEST_STATUS=$(testflinger results $JOB_ID |jq -r .test_status)
testflinger artifacts $JOB_ID
```

## How do we do for testing w/o provision for IOT deivce via this script

**Prepare**: manifest_json_file, checkbox_conf ,test_plan_name, checkbox_snap_install_script.
**Modify file:** `/template/shell_scripts/02_Install_checkbox_snap` (based
on your checkbox snap install script and follow the original file structure).
**Note:** If you don't have the launcher or checkbox_conf which combined with manifest.
eg:

```text
[manifest]
abc::123 = true

[environment]
zxc = 123
```

You can use like this
`./testflinger_yaml_generator.py -c $CID --checkboxType snap --testplan $TEST_PLAN --no-needManifest --checkboxConf $CHECKBOX_CONF_WITH_MANIFEST`

```sh
git clone --depth 1 --branch main git@github.com:canonical/ce-oem-dut-checkbox-configuration.git
# if `$CID` in `IOT/` folder, we can modify the `IOT/$CID/launcher` and only
# left the `manifest` and `environment` field as `$CHECKBOX_CONF_PATH`
# else we need to create the `./template/manifest.json` and
# `./template/checkbox.conf` we by ourselves
./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --provisionImage $IMAGE_NAME --manifestJson $MANIFEST_JSON_PATH --checkboxConf $CHECKBOX_CONF_PATH
JOB_ID=$(testflinger-cli -q $OUTPUT_YAML)
testflinger-cli poll $JOB_ID
TEST_STATUS=$(testflinger results $JOB_ID |jq -r .test_status)
testflinger artifacts $JOB_ID
```
