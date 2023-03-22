#!/bin/bash

pwd='u'

echo -e "\nGetting hardware info..."

# Get hardware info
myCPU=$(echo ${pwd} | sudo -S dmidecode -s processor-version)
myGPU=$(lspci -nnv | awk -F ': ' '/VGA controller|NVIDIA|Display controller/{for(i=2;i<=NF;i++)printf("%s ",$i);print ""}')
myWireless=$(lspci -nnv | grep 'Network controller' | cut -c 36-)
myWiFiSub=$(lspci -nnv | grep -A 2 'Network controller' | grep -i subsystem | cut -c 13-)
myManifest=$(ubuntu-report show | grep DCD | awk '{print $2}' | sed 's/"//g')
myKernel=$(uname -r)
myBIOSvers=$(echo ${pwd} | sudo -S dmidecode -s bios-version)

{
    echo -e "CPU:\t\t${myCPU} "
    echo -e "GPU:\t\t${myGPU} "
    echo -e "Wireless:\t\t${myWireless} "
    echo -e "WiFi Sub ID:\t${myWiFiSub} "
    echo -e "Manifest Info:\t${myManifest}"
    echo -e "Kernel Version:\t${myKernel}"
    echo -e "BIOS:\t\t${myBIOSvers} "
}   >> "./hardware_info.txt"
