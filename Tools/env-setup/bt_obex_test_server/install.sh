#!/bin/bash
#
echo " "
printf " \033[1;35m Install Obex server  \033[0m\n"

USER_HOME=$(eval echo ~"${SUDO_USER}")

apt install python3-pydbus python3-gi -y
mkdir -p "${USER_HOME}/obex"
chown "${SUDO_USER}":"${SUDO_USER}" "${USER_HOME}/obex"
sed -i.bak "s#ExecStart.*#ExecStart=/usr/libexec/bluetooth/obexd -a -r ${USER_HOME}/obex -P pcsuite#g" /usr/lib/systemd/user/obex.service
systemctl daemon-reload
systemctl restart bluetooth.service
cp bt_obex_test_server.py "${USER_HOME}/"

#Create service
cat <<EOF > "${USER_HOME}/.config/systemd/user/bt_obex_test_server.service"
[Unit]
Description=Bluetooth Obex Test Server
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${USER_HOME}/bt_obex_test_server.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF

systemctl --user -M "$SUDO_USER@" daemon-reload
systemctl --user -M "$SUDO_USER@" enable bt_obex_test_server.service
systemctl --user -M "$SUDO_USER@" start bt_obex_test_server.service
