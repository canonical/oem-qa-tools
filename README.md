# Testflinger Job YAML SDK

This branch is a OOP library for building testflinger's job.yaml files
that can be submitted with `testflinger-cli submit`.


## Installation

This package has 2 parts:
1. The python library itself that can be imported by other python programs
2. A CLI tool

Installation URL is the same, we just need to use different package managers.

### Installing the Library

With `pip`

```
pip install git+https://github.com/canonical/oem-qa-tools.git@testflinger-yaml-sdk
```

With `poetry`

```sh
poetry add git+https://github.com/canonical/oem-qa-tools.git@testflinger-yaml-sdk
```

### Installing the CLI Tool

> [!Note]  
> The sdk library does **NOT** need to be installed first. pipx will do that for us.

With `pipx`

```
pipx install git+https://github.com/canonical/oem-qa-tools.git@testflinger-yaml-sdk
```

To get the latest commit, specify `--force`

```
pipx install git+https://github.com/canonical/oem-qa-tools.git@testflinger-yaml-sdk --force
```

## Development

Requires python3.10+

### Install tools
(Requires ubuntu 22.04+ if you are installing pipx from apt)

Install pipx and poetry:

```sh
sudo apt update && sudo apt install -y pipx
pipx install poetry
```

> [!WARNING]  
> Do not install python3-poetry from apt. It's way too old


If pipx is being installed on the system for the 1st time, add this line to .bashrc or .zshrc

```sh
export PATH=$HOME/.local/bin:$PATH
```

`pipx` will prompt about this too so don't worry about memorizing this.

After installation, the `poetry` command will be available in $PATH:

```
$ poetry -V
Poetry (version 2.1.3)
```

### Environment setup

For a fresh setup:
```sh
git clone https://github.com/canonical/oem-qa-tools.git
cd oem-qa-tools
git checkout testflinger-yaml-sdk
eval $(poetry env activate)
poetry install
```
A new virtual environment has been setup and all dependencies are installed.

To leave the environment:

```sh
$ deactivate
```

To re-enter this environment, run `eval $(poetry env activate)` in the project directory

```sh
cd oem-qa-tools
git checkout testflinger-yaml-sdk
eval $(poetry env activate)
```
