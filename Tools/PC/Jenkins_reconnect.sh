#!/bin/bash

################################################################################# 
#Purpose:
#To save time to install alloem image that can trigger via Jenkins again, 
#we can set up the DUT by following steps for further testing if the image 
#is installed by USB key or installed by Stock Ubuntu image locally.
#
#Note:
#The DUT must install the alloem image first time to create its unique Jenkins Job.
#################################################################################

set -e
user='ubuntu'

help()
{
        echo "Usage:"
        echo "1. Put this script to DUT's home directory."
        echo "2. sh Jenkins_reconnect.sh."
        echo "3. Enter the password for ubuntu account, typically type 'u'."
        echo "4. Put this DUT back to the stock in QA-Lab."
        echo "5. Get IP address from HIC and ping this DUT to make sure it work properly."
}

while getopts ":h" option; do
	case $option in
		h)
			help
			exit
			;;
		\?)
			echo "Error: Invalid option"
			echo "Please type 'sh Jenkins_reconnect.sh -h'"
			exit 1
			;;
	esac
done

setup_user()
{
	#Create an user
	if ! [ "$(id ${user} 2>/dev/null)" ]; then
		echo "Create a new user called '${user}'..."
		sudo useradd -m ${user}
	else
		echo "The ${user} user already exist"
	fi
	echo ''
	printf " \033[1;35mPlease set %s account with 'u' password \033[0m" "${user}"
	sudo passwd ${user}
	echo ''
	sudo usermod -aG sudo ${user}
	sudo usermod --shell /bin/bash ${user}
	echo "${user} ALL=(ALL:ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/${user}
}

setup_ssh()
{
	#Install SSH
	sudo apt install openssh-server
}

import_key()
{
	#import oem-taipei-bot ce-certification-qa key
	sudo su -c 'ssh-import-id oem-taipei-bot ce-certification-qa' ${user}
}

setup_user
setup_ssh
import_key
