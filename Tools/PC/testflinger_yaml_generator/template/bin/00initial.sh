set -x
sudo apt-get update
sudo apt-get install openssh-server -y

TARGET_DEVICE_USERNAME=ubuntu
#!/bin/bash
# convenience functions
#
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
_put() {{
    scp $SSH_OPTS $1 $TARGET_DEVICE_USERNAME@$DEVICE_IP:$2
}}
_get() {{
    scp $SSH_OPTS $TARGET_DEVICE_USERNAME@$DEVICE_IP:$1 $2
}}
_run() {{
    ssh -t $SSH_OPTS $TARGET_DEVICE_USERNAME@$DEVICE_IP "$@"
}}
_run_in_bg() {{
    ssh -f -t $SSH_OPTS $TARGET_DEVICE_USERNAME@$DEVICE_IP "$@"
}}
wait_for_ssh() {{
    loopcnt=0
    until timeout 120 ssh $SSH_OPTS $TARGET_DEVICE_USERNAME@$DEVICE_IP /bin/true
    do
        echo "Testing to see if system is back up"
        loopcnt=$((loopcnt+1))
        if [ $loopcnt -gt 40 ]; then
            echo "ERROR: Timeout waiting for ssh!"
            exit 1
        fi
        sleep 30
    done
}}

echo
echo "====== TARGET DEVICE CONNECTION INFO ======"
echo
echo DEVICE_IP: $TARGET_DEVICE_USERNAME@$DEVICE_IP
echo
echo "==========================================="
echo

_run sudo amixer set Master unmute
_run sudo amixer set Master 100
_run sudo amixer set Speaker 100
_run sudo amixer -c 1 set Master unmute
_run sudo amixer -c 1 set Master 100
_run sudo amixer -c 1 set Speaker 100

_run gsettings set org.gnome.desktop.screensaver ubuntu-lock-on-suspend false
_run gsettings set org.gnome.desktop.screensaver lock-enabled false
_run gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
_run gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
_run gsettings set org.gnome.desktop.session idle-delay 'uint32 0'
