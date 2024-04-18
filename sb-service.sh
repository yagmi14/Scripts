#!/bin/bash

read -p "name:" name

cat > /etc/systemd/system/$name.service <<EOF
[Unit]
Description=sing-box service
Documentation=https://sing-box.sagernet.org
After=network.target nss-lookup.target

[Service]
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
ExecStart=/usr/bin/sing-box run -c /usr/local/etc/$name/config.json
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

systemctl enable --now $name; \
systemctl status $name
