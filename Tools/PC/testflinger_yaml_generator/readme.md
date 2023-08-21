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
<!-- markdownlint-configure-file { "MD013": { "line_length": 150 } } -->
```text
usage: testflinger_ymal_generator.py [-h] -c CID -o OUTPUTFILENAME
                                     [--outputFolder OUTPUTFOLDER] [--testplan TESTPLAN]
                                     [--excludeJobs EXCLUDEJOBS] [--checkboxType {deb,snap}]
                                     [--provisionType {distro,url}]
                                     [--provisionImage PROVISIONIMAGE]
                                     [--globalTimeout GLOBALTIMEOUT]
                                     [--outputTimeout OUTPUTTIMEOUT]
                                     [--sessionDesc SESSIONDESC]
                                     [--manifestJson MANIFESTJSON]
                                     [--LauncherTemplate LAUNCHERTEMPLATE]
                                     [--reserveTime RESERVETIME]
                                     [--TFYamlTemplate TFYAMLTEMPLATE]
                                     [--binFolder BINFOLDER]

Testflinger yaml file generator

optional arguments:
  -h, --help            show this help message and exit

Required:
  -c CID, --CID CID     CID (default: None)
  -o OUTPUTFILENAME, --outputFileName OUTPUTFILENAME
                        Set the output yaml file Name (default: None)

general options:
  --outputFolder OUTPUTFOLDER
                        Set the output folder path (default: ./)
  --testplan TESTPLAN   Set the checkbox test plan name. If didn't set this will not run
                        checkbox test (default: )
  --excludeJobs EXCLUDEJOBS
                        Set the exclude jobs pattern. ie".*memory/memory_stress_ng.*".
                        (default: )
  --checkboxType {deb,snap}
                        Set which checkbox type you need to install and test. (default: deb)
  --provisionType {distro,url}
                        Set the provision type (default: distro)
  --provisionImage PROVISIONIMAGE
                        The provision image. ie, desktop-22-04-2-uefi. If didn't set this
                        mean no provision (default: )
  --globalTimeout GLOBALTIMEOUT
                        Set the testflinger's global timeout. Max:43200 (default: 43200)
  --outputTimeout OUTPUTTIMEOUT
                        Set the output timeout if the DUT didn't response to server, it will
                        be forced closed this job. It should be set under the global
                        timeout. (default: 9000)

Launcher settion  options:
  --sessionDesc SESSIONDESC
                        Set the session description (default: CE-QA-PC_Test)
  --manifestJson MANIFESTJSON
                        Set the manifest json file to build the launcher. (default:
                        ./template/manifest.json)
  --LauncherTemplate LAUNCHERTEMPLATE
                        Set the launcher template folder (default:
                        ./template/launcher_config/)

Testflinger yaml options:
  --LpID LPID           If you want to reserve the DUT, please input your Launchpad ID
                        (default: )
  --reserveTime RESERVETIME
                        Set the timeout (sec) for reserve. (default: 1200)
  --TFYamlTemplate TFYAMLTEMPLATE
                        Set the testflinger template yaml file (default:
                        ./template/template.yaml)

Test command in testflinger yaml:
  --binFolder BINFOLDER
                        Set the testflinger test command folder. (default:
                        ./template/shell_scripts/)
```

### Basically usage

we using the default timeout, and we don’t need to have insert the template
path

1. We  need to modify the `./template/shell_scripts/*`
(mostly we only need to modify `20_before_test`, `99_end_test`)

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --provisionImage $IMAGE_NAME --manifestJson $MANIFEST_JSON_PATH`

1. If we only want to provision and reserve the machine:

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --provisionImage $IMAGE_NAME`

1. If we only want to test w/ noprovision:

> `./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --manifestJson $MANIFEST_JSON_PATH`

## How do we do for testing (w/ provision) cert lab’s DUT w/ this script

**Prepare:** CID, provision_image_name, manifest_json_file, test_plan_name.

**Modify file:** `20_before_test` (if we want to add the staging ppa repo or
something else), `99_end_test` (maybe copy some file in artifacts folder)

```sh
git clone --depth 1 --branch main git@github.com:canonical/ce-oem-dut-checkbox-configuration.git
# if `$CID` in `PC/` folder, we can use the `PC/$CID/manifest.json` as `$MANIFEST_JSON_PATH`
# else we can use the `PC/default/manifest.json` or `./template/manifest.json` we modify by our self
./testflinger_ymal_generator.py -c $CID -o $OUTPUT_YAML --LpID $LP_ID --testplan $TEST_PLAN --provisionImage $IMAGE_NAME --manifestJson $MANIFEST_JSON_PATH
JOB_ID=$(testflinger-cli -q $OUTPUT_YAML)
testflinger-cli poll $JOB_ID
TEST_STATUS=$(testflinger results $JOB_ID |jq -r .test_status)
testflinger artifacts $JOB_ID
```
