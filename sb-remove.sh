#!/bin/bash

read -p "name:" name

systemctl disable --now $([ -f /etc/systemd/system/$name.service ] && echo $name); rm -f /etc/systemd/system/$name.service; rm -rf /usr/local/etc/$name
