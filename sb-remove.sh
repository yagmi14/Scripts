#!/bin/bash

read -p "name:" name

systemctl disable --now $name; rm -f /etc/systemd/system/$name.service; rm -rf /usr/local/etc/$name
