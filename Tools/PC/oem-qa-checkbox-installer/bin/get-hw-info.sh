#!/bin/bash

echo -e "\nGetting hardware info..."

myCPU=$(sudo dmidecode -s processor-version)
myGPU=$(lspci -nnv | grep "VGA controller\|NVIDIA\|Display controller" | cut -c 9- | sed '2,4s/^/		/')
myWireless=$(lspci -nnv | grep 'Network controller' | cut -c 36-)
myWiFiSub=$(lspci -nnv | grep -A 2 'Network controller' | grep -i subsystem | cut -c 13-)
myManifest=$(ubuntu-report show | grep DCD | awk '{print $2}' | sed 's/"//g')
myKernel=$(uname -a)
myBIOSvers=$(sudo dmidecode -s bios-version)

{
    echo -e "CPU:\t\t${myCPU} "
    echo -e "GPU:\t\t${myGPU} "
    echo -e "Wireless:\t\t${myWireless} "
    echo -e "WiFi Sub ID:\t${myWiFiSub} "
    echo -e "Manifest Info:\t${myManifest}"
    echo -e "Kernel Version:\t${myKernel}"
    echo -e "BIOS:\t\t${myBIOSvers} "
}   >> "./hardware_info.txt"
