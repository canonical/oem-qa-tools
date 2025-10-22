# WoL

Used to set up a Wake-up on LAN server

## prerequestment

Please note you should have an environment for juju machine charm to deploy,
such as lxd

### Build this charm

```bash
charmcraft pack
```

## How to deploy

juju deploy -m [juju model name] ./bundle.yaml --debug --verbose

## How to use the default wake up on lan server

<!-- markdownlint-disable MD013 -->
The usage can be found [here](https://github.com/canonical/checkbox/blob/main/providers/base/units/ethernet/wake-on-LAN-automatic-tests.md)
