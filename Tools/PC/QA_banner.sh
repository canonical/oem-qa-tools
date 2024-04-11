#!/bin/bash

################################################################################# 
#Purpose:
#This script is used to add or remove QA_banner 
#
#################################################################################

set -e

help()
{
        echo "Usage:"
        echo "1. Put this script and QA_banner file to DUT's home directory."
        echo "2. Add banner: sh QA_banner.sh -a"
        echo "3. Remove banner: sh QA_banner.sh -r"
}

add_qa_ssh_banner()
{
    echo "Start adding QA_banner..."
    sudo cp QA_banner /etc/ssh/QA_banner
    echo "Banner /etc/ssh/QA_banner" | sudo tee -a /etc/ssh/sshd_config.d/banner.conf
    sudo systemctl restart sshd
    echo "End of adding QA_banner..."
}

remove_qa_ssh_banner()
{
    echo "Start removing QA_banner..."
    sudo rm -f /etc/ssh/QA_banner /etc/ssh/sshd_config.d/banner.conf
    sudo systemctl restart sshd
    echo "End of removing QA_banner..."
}

while getopts ":har" option; do
	case $option in
		h)
			help
			exit
			;;
		a)
                        add_qa_ssh_banner
			exit
			;;
		r)
                        remove_qa_ssh_banner
			exit
			;;
		\?)
			echo "Error: Invalid option"
			echo "Please type 'sh QA_banner.sh -h'"
			exit 1
			;;
	esac
done
