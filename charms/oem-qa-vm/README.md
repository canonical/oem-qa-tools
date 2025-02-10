# oem-qa-vm

Used to set up an lxc container that preinstalled tmux, checkbox
and testflinger-cli.

## prerequestment
Please note you should have an environment for juju machine charm to deploy,
such as lxd

### Download libraries for this charm

```bash
charmcraft fetch-lib
```

### Build this charm

```bash
charmcraft pack
```

## How to deploy
juju deploy -m [juju model name] ./bundle.yaml --debug --verbose
