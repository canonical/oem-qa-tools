#!/bin/bash

pwd='u'
output_file='./hardware_info.txt'

printf "\nGetting hardware info...\n"

# Get hardware info
myCPU=$(echo ${pwd} | sudo -S dmidecode -s processor-version)
myGPU=$(lspci -nnv | awk -F ': ' '/VGA controller|NVIDIA|Display controller/{for(i=2;i<=NF;i++)printf("%s ",$i);print ""}')
myWireless=$(lspci -nnv | grep 'Network controller' | cut -c 36-)
myWiFiSub=$(lspci -nnv | grep -A 2 'Network controller' | grep -i subsystem | cut -c 13-)
myManifest=$(ubuntu-report show | grep DCD | awk '{print $2}' | sed 's/"//g')
myKernel=$(uname -r)
myBIOSvers=$(echo ${pwd} | sudo -S dmidecode -s bios-version)

# output hardware info to output file
{
    printf "CPU: %s\n" "${myCPU}"
    printf "GPU: %s\n" "${myGPU}"
    printf "Wireless: %s\n" "${myWireless}"
    printf "WiFi Sub ID: %s\n" "${myWiFiSub}"
    printf "Manifest Info: %s\n" "${myManifest}"
    printf "Kernel Version: %s\n" "${myKernel}"
    printf "BIOS: %s\n" "${myBIOSvers}"
} >> "${output_file}"
