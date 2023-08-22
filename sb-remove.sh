#!/bin/bash

read -p "name:" name

if [ -f /etc/systemd/system/$name.service ]; then
  systemctl disable --now $name
  rm -f /etc/systemd/system/$name.service
  rm -rf /usr/local/etc/$name
else
  echo "Service $name does not exist."
fi
