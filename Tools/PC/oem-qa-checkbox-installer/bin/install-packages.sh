#!/bin/bash

echo -e "\nInstalling other essential packages..."

pwd='u'

# Install bugit
echo "Installing bugit..."
echo ${pwd} | sudo -S snap install bugit --edge --devmode

# Install openssh
echo "Installing openssh-server..."
echo ${pwd} | sudo apt install -y openssh-server
echo "Enabling ssh.service..."
echo ${pwd} | sudo systemctl enable ssh --now
