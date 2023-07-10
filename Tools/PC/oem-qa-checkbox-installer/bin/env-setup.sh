#!/bin/bash

echo -e "\nSetting up the testing environment..."

pwd='u'

# Disable auto upgrade
echo ${pwd} | sudo -S mv /etc/apt/apt.conf.d/20auto-upgrades /etc/apt/apt.conf.d/20auto-upgrades.orig
echo -e "\033[1;32mModify 20auto-upgrades file: \033[0m"
cat << "EOF" | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "0";
APT::Periodic::AutocleanInterval "0";
APT::Periodic::Unattended-Upgrade "0";
EOF
echo -e "\033[1;42;37mdone\033[0m"

# back up dconf setting
echo -e "\033[1;32mBack up gnome setting by dconf dump\033[0m"
dconf dump / > ./conf/env-for-restore-dconf

# change dconf setting for checkbox testing
echo -e "\033[1;32mChanging setting by dconf load\033[0m"
dconf load / < ./conf/checkbox-testing-env-dconf

# set current to be autologing
sudo ./bin/autologin.sh "$(whoami)"
