# The stressor test utility

## Purpose
This script is uses to launch stress-ng tests with different stressors directly. 

## Requirement
1. Install stress-ng snap from snap store
2. Install checkbox provider snap
3. Install generic checkbox snap or project checkbox 

## Usage
Switch to this directory and run stress-ng-stressor-test.sh script
```sh
cd Tools/stressor-test/
./stress-ng-stressor-test.sh
``` 

If you met any issues during the testing, likes system hand or the script was killed by OOM, etc...
You could just follow above steps to relaunch the same test or marked as failed.
```sh
$ ./stress-ng-stressor-test.sh 
## Start stress-ng test...
Remaing stressors: 298
Is this stressor af-alg test failed?
	input [yes] to skip it.
	Or
	press [Enter] to run
```
