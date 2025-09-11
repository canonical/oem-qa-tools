
# WebGL Conformance Test Server setup

## Nitoce

This script is utilized to setup the test server for
[checkbox](https://github.com/canonical/checkbox) could test it automatically.
 Therefore, it will use local.patch to pacth the webgl-conformance-tests.html
 to make it download the test result right atfer testing finished.

## Usage

Put this folder in the device (works for vm and lxc container).
Executing

```bash
sudo python3 install.py
```

Then, you should be able to reach http://{IP}/local-tests.html
