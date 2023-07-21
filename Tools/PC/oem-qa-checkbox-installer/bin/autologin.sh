#!/bin/bash
################################################################
# Purpose:
# This script is used to set user enbale auto login automatically
################################################################

NEW_USER="$1"
CONFIG_FILE="/etc/gdm3/custom.conf"
if [ -e "${CONFIG_FILE}" ]; then
    AUTOLOGIN=$(grep "^[^#\[]" "${CONFIG_FILE}"| grep "AutomaticLoginEnable" | cut -d '=' -f 2)
    if [[ -z ${AUTOLOGIN} ]]; then
        echo "Set user [${NEW_USER}] to auto login"
        sed -i "s/\[daemon\]/[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=${NEW_USER}/1" "${CONFIG_FILE}"
    elif [[ ${AUTOLOGIN} == "True" ]]; then
        CUR_USER=$(grep "^[^#\[]" "${CONFIG_FILE}" | grep "AutomaticLogin=" | cut -d '=' -f 2)
        echo "Changing auto login user from [${CUR_USER}] to [${NEW_USER}]"
	sed -i "s/AutomaticLogin=${CUR_USER}/AutomaticLogin=${NEW_USER}/1" "${CONFIG_FILE}"
    else
        CUR_USER=$(grep "^[^#\[]" "${CONFIG_FILE}" | grep "AutomaticLogin=" | cut -d '=' -f 2)
        echo "Set user [${NEW_USER}] to auto login"
	sed -i "s/AutomaticLoginEnable=${AUTOLOGIN}/AutomaticLoginEnable=True/1" "${CONFIG_FILE}"
	sed -i "s/AutomaticLogin=${CUR_USER}/AutomaticLogin=${NEW_USER}/1" "${CONFIG_FILE}"
    fi
else
    echo "There is no gdm3 setting file:[${CONFIG_FILE}] in this system"
fi
