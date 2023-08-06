#!/bin/bash

echo "Enter config name:"
read name

echo "Enter listening port:"
read port1

echo "Enter destination ip:"
read ip

echo "Enter destination port:"
read port2

cat > /usr/local/etc/gost/$name.json <<EOF
{
  "Retries": 0,
  "ServeNodes": [
    "tcp://:$port1/$ip:$port2",
    "udp://:$port1/$ip:$port2"
  ],
  "ChainNodes": []
}#
EOF

cat > /etc/systemd/system/$name.service <<EOF
[Unit]
Description=gost service
After=network.target nss-lookup.target

[Service]
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
ExecStart=/usr/local/bin/gost -C /usr/local/etc/gost/$name.json
Restart=on-failure
RestartSec=1800s
TasksMax=infinity
LimitCPU=infinity
LimitFSIZE=infinity
LimitDATA=infinity
LimitSTACK=infinity
LimitCORE=infinity
LimitRSS=infinity
LimitNOFILE=infinity
LimitAS=infinity
LimitNPROC=infinity
LimitMEMLOCKS=infinity
LimitSIGPENDING=infinity
LimitMSGQUEUE=infinity
LimitRPTRIO=infinity
LimitRTTIME=infinity

[Install]
WantedBy=multi-user.target
EOF

systemctl enable --now $name && systemctl status $name
