#!/bin/bash

##############################################################################
# Purpose:
#   Check and prepare the required environment and package are ready.
#   Once you execute this script, it checks those dependencies code and
#   install the python packages in virtual environment.
#
# Note:
#   Don't use "exit" in this script since we need to enter the python virtual
#   environment by source or .
#   The bash environment, aka terminal, will be gone once the "exit" is called
#
# Usage:
#   source setup.sh
##############################################################################

# Name of virtual environment
VENV="transfer-hw-to-cert-env"
DEPENDENCIES=("Jira" "GoogleSheet" "C3")

# Check dependency api
check_dependency_api()
{
    for dependency in "${DEPENDENCIES[@]}"; do
        # Copy the dependency if it doesn't exist
        if [ ! -d "./$dependency" ]; then
            echo "Copying the dependency \"$dependency\" ..."
            cp -r "../API/$dependency" .
            # shellcheck disable=SC2181
            if [[ "$?" -ne 0 ]]; then
                echo "Error: fail to copy the dependency \"$dependency\""
                return 1
            fi
        fi
    done
    return 0
}

in_python_venv()
{
    # Create virtual env
    echo "Creating the virtual environment called \"$VENV\" ..."
    [ ! -d "$VENV" ] &&  python3 -m venv $VENV

    # Enter virtual env
    echo "Entering the virtual environment ..."
    # shellcheck disable=SC1091
    . "$VENV/bin/activate"

    # Check we're in virtual env
    echo "Checking we are in virtual environment or not..."
    echo "$VIRTUAL_ENV" | grep -i $VENV
    # shellcheck disable=SC2181
    if [[ "$?" -ne 0 ]]; then
        echo "Error: Got problem of active virtual environment"
        return 1
    fi

    # Install python packages
    for dependency in "${DEPENDENCIES[@]}"; do
        pathOfRequirements="./$dependency/requirements.txt"
        if [ -f "$pathOfRequirements" ]; then
            pip install -r "$pathOfRequirements"
        fi
    done
}

# main
check_dependency_api && in_python_venv