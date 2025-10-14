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
