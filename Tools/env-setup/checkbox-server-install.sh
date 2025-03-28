#!/bin/bash

###########################################################
# Checkbox Server Installation Script#
# The server username is "s", and the password is "s".
# The script is supported with 18.04 LTS and 20.04 LTS.
# Originally migrate from https://git.launchpad.net/oem-qa-tools/tree/checkbox-server-install.sh
###########################################################

setup_environment()
{
    echo " "
    printf " \033[1;35m Setup Environment \033[0m\n"
    echo "%s ALL =(root) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/allowall

    # Disable auto upgrade
    echo 's' | sudo -S mv /etc/apt/apt.conf.d/20auto-upgrades /etc/apt/apt.conf.d/20auto-upgrades.orig
    cat << "EOF" | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "0";
APT::Periodic::AutocleanInterval "0";
APT::Periodic::Unattended-Upgrade "0";
EOF

    #Turn off auto suspend and screen saving
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
    gsettings set org.gnome.desktop.session idle-delay 'uint32 0'
}

setup_obex()
{
    echo " "
    printf " \033[1;35m Install Obex server  \033[0m\n"
    sudo apt install obexftp -y
    sudo add-apt-repository ppa:lihow731/ppa -y
    sudo apt-get update
    sudo apt purge bluez-obexd bluez-cups -y
    sudo apt install obex-data-server -y
    sudo mkdir /home/s/obexftp
    sudo sed -i.bak 's#ExecStart.*#ExecStart=/usr/lib/bluetooth/bluetoothd --compat#g' /usr/lib/systemd/system/bluetooth.service
    sudo sed -i.bak 's#ExecStart.*#ExecStart=/usr/lib/bluetooth/bluetoothd --compat#g' /etc/systemd/system/dbus-org.bluez.service
    sudo systemctl daemon-reload
    sudo systemctl restart bluetooth.service
    sudo rm -rf /var/lib/bluetooth/*
    echo "s" |sudo -S -k gnome-terminal -- obexftpd -c /home/s/.obexftp -b

    #Create obex.sh
    printf " \033[1;35m Setup Obex  \033[0m\n"
    echo 's' | sudo -S bash -c 'echo "#!/bin/bash
sudo chmod 777 /var/run/sdp
sudo rm -rf /var/lib/bluetooth/*
sudo hciconfig hci0 piscan
sudo obexftpd -c /home/s/.obexftp -b" > /usr/bin/obex.sh'
    sudo chmod 755 /usr/bin/obex.sh

    #Add obex.desktop
    echo 's' | sudo -S bash -c 'echo "[Desktop Entry]
Type=Application
Exec=gnome-terminal -- bash -c \"/usr/bin/obex.sh;bash\"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=true
Name[en_US]=Starup script_obex
Name=Starup script_obex
Comment[en_US]=#
Comment=#" > /etc/xdg/autostart/obex.desktop'
}

setup_eddystone()
{
    #Download advertise-url file to /usr/bin
    echo " "
    printf " \033[1;35m Download Advertise-url file  \033[0m\n"
    sudo apt-get install git -y
    git clone https://github.com/google/eddystone.git
    sudo cp eddystone/eddystone-url/implementations/linux/advertise-url /usr/bin/
    rm -rf eddystone/

    #Create beacon.sh
    printf " \033[1;35m Setup Beacon  \033[0m\n"
    echo 's' | sudo -S bash -c 'echo "#!/bin/bash
python3 /usr/bin/./advertise-url -u http://www.ubuntu.com
echo \"Beacon Service is enabled\"" > /usr/bin/beacon.sh'
    sudo chmod 755 /usr/bin/beacon.sh
    sudo hciconfig hci0 leadv 3
    sudo hciconfig hci0 piscan

    #Add beacon.desktop
    echo 's' | sudo -S bash -c 'echo "[Desktop Entry]
Type=Application
Exec=gnome-terminal -- bash -c \"/usr/bin/beacon.sh;bash\"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=true
Name[en_US]=Starup script_beacon
Name=Starup script_beacon
Comment[en_US]=#
Comment=#" > /etc/xdg/autostart/beacon.desktop'
    printf '\n'
}

setup_iperf()
{
    #Install Iperf
    echo " "
    printf " \033[1;35m Setup Iperf  \033[0m\n"
    sudo apt update
    sudo apt install iperf3 -y

    #Add Iperf.desktop
    echo 's' | sudo -S bash -c 'echo "[Desktop Entry]
Type=Application
Exec=gnome-terminal -- iperf3 -s
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=true
Name[en_US]=Starup script_iperf
Name=Starup script_iperf
Comment[en_US]=#
Comment=#" > /etc/xdg/autostart/iperf.desktop'	
}


setup_wakeonlan()
{
    #Install Wake-on-Lan server
    echo " "
    printf " \033[1;35m Wake-on-Lan server  \033[0m\n"
    sudo apt update
    sudo apt install wakeonlan -y
    sudo apt install python3-fastapi -y
    sudo apt install uvicorn -y
    sudo cp wol_server.py /usr/bin/

    #Add Wakeonlan.desktop
    echo 's' | sudo -S bash -c 'echo "[Desktop Entry]
Type=Application
Exec=gnome-terminal -- bash -c \"cd /usr/bin && uvicorn wol_server:app --host 0.0.0.0 --port 8090 > /tmp/wol.log 2>&1\"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=true
Name[en_US]=Starup script_Wake-on-Lan
Name=Starup script_Wake-on-Lan
Comment[en_US]=#
Comment=#" > /etc/xdg/autostart/Wake-on-Lan.desktop'
}

setup_ptp4l()
{
    # Install linuxptp
    echo " "
    printf " \033[1;35m Setup ptp4l  \033[0m\n"
    sudo apt update
    sudo apt install linuxptp -y

    # Get the first ethernet name
    KEYWORDS="hardware-transmit
              hardware-receive
              hardware-raw-clock"
    for iface in /sys/class/net/*; do
        iface=${iface##*/}
        supported=true
        if [[ $iface == e* ]]; then
            output=$(ethtool -T "$iface")
            for keyword in $KEYWORDS; do
                if ! grep -q "$keyword" <<< "$output"; then
                    supported=false
                    break
                fi
            done
            if [[ $supported == true ]]; then
                echo "ptp4l supported eth-interface: $iface"
                if sudo ethtool "$iface" | grep -q "Link detected: yes"; then
                    echo "The link status of $iface is UP."
                    echo "ptp4l will be started on this interface."
                    ptp4l_iface=$iface
                    break
                else
                    echo "The link status of $iface is DOWN."
                    echo "ptp4l will not be started on this interface."
                fi
            fi
        fi
    done
    if [ -z "$ptp4l_iface" ]; then
        echo "No suitable Ethernet interface which support ptp4l found."
        exit 1
    fi

    # Check the link status
    LINK_STATUS=$(ip link show "$ptp4l_iface" | grep "state" | awk '{print $9}')

    if [ "$LINK_STATUS" != "UP" ]; then
        echo "The link status of $ptp4l_iface is DOWN. ptp4l will not be started."
        exit 1
    fi
    # Add ptp4l.desktop with the correct ethernet interface name
    echo 's' | sudo -S bash -c "echo '[Desktop Entry]
Type=Application
Exec=gnome-terminal -- sudo ptp4l -i $ptp4l_iface -m --step_threshold=1 --logAnnounceInterval=0 --logSyncInterval=-3 --network_transport=L2
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=true
Name[en_US]=Startup script_ptp4l
Name=Startup script_ptp4l
Comment[en_US]=#
Comment=#' > /etc/xdg/autostart/ptp4l.desktop"
}

setup_server()
{
    setup_environment
    setup_obex
    setup_eddystone
    setup_iperf
    setup_ptp4l
    setup_wakeonlan

    printf "\033[1;42;37m Done\033[0m\n"
    echo " "
    printf "\033[1;31m Please reboot the system to active all services  \033[0m\n"
}

setup_server