# WebGL Conformance Test Server setup

This script sets up the test server for Checkbox, enabling it to test automatically.
It uses local.patch to patch webgl-conformance-tests.html,
making it download the test results immediately after testing finishes.

## prerequestment

Please note you should have an environment for juju machine charm to deploy,
such as lxd

### Build this charm

```bash
charmcraft pack
```

## How to deploy

juju deploy -m [juju model name] webgl.charm --debug --verbose

## How to use the default WebGL Conformance Test Server

Simply open http://{IP}/local-tests.html in the browser
