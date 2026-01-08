#!/bin/bash

apt install python3-pydbus python3-gi

mkdir $HOME/obex

# modify /usr/lib/systemd/user/obex.service
# obexd -a -r $HOME/obex -P pcsuite

#reboot
