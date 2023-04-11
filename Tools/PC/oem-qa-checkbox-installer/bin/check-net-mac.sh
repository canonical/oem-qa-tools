#!/bin/bash

help()
{
    echo "Usage:sh $0 -f black_mac_address_list_file"
}

check_black_list_file_is_exist()
{
    # If file doesn't exist, exit with code 1.
    if [ ! -f "$1" ];then
        echo "File:[$1] doesn't exist"
        exit 1
    fi
}

check_no_black_mac_on_dut()
{
    ERROR_FLAG=0
    while IFS= read -r BLACK_MAC
    do
      TMP="$(grep -irl "${BLACK_MAC}" /sys/class/net/*/address | grep -v "lo")"
      if [ "${TMP}" != "" ];then
	      echo -e "\033[0;31mBLACK_MAC_DEVICE:[$(echo "${TMP}" | cut -d '/' -f 5)], MAC:[$(grep -irh "${BLACK_MAC}" /sys/class/net/*/address | grep -v "lo")]\033[0m"
          ERROR_FLAG=1
      fi
    done < "$1"
    # If found one MAC address in the black list, exit with code 1.
    if [ ${ERROR_FLAG} -eq 1 ];then
        exit 1
    fi
}

while getopts ":hf:" option; do
    case ${option} in
    h)
        help
        exit
        ;;
    f)
	check_black_list_file_is_exist "${OPTARG}"
        check_no_black_mac_on_dut "${OPTARG}"
        ;;
    \?)
        echo "Error: Invalid option"
	echo "Please type 'sh $0 -h'"
        exit 1
        ;;
    esac
done


