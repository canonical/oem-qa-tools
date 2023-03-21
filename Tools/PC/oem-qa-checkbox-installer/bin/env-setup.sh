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

# Disable auto suspend when plugged in
echo -e "\033[1;32mDisable auto suspend when plugged in\033[0m"
# Settings > Power > Power > Automatic Suspend > Plugged in > Off
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing && echo -e "\033[1;42;37mdone\033[0m"

# Disable auto suspend when on battery power
echo -e "\033[1;32mDisable auto suspend when on battery\033[0m"
# Settings > Power > Power > Automatic Suspend > On Battery Power > Off
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type nothing && echo -e "\033[1;42;37mdone\033[0m"

# Disable auto blank screen
echo -e "\033[1;32mDisable auto blank screen\033[0m"
# Settings > Privacy > Screen > Blank Screen Delay > Never
gsettings set org.gnome.desktop.session idle-delay 0 && echo -e "\033[1;42;37mdone\033[0m"
