#!/bin/bash

echo "Enter name:"
read name

systemctl disable --now $name; rm -f /etc/systemd/system/$name.service; rm -rf /usr/local/etc/gost/$name.json
