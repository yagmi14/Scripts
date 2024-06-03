#!/bin/bash
set -e

bash <(curl -fsSL https://sing-box.app/deb-install.sh)

mkdir -p /usr/local/etc/sb3/conf

echo '{"log":{"disabled":false,"level":"info","timestamp":true}}' > /usr/local/etc/sb3/conf/00_log.json

echo -e "[Unit]\nDescription=sing-box service\nDocumentation=https://sing-box.sagernet.org\nAfter=network.target nss-lookup.target\n\n[Service]\nUser=root\nType=simple\nNoNewPrivileges=yes\nTimeoutStartSec=0\nExecStart=/usr/bin/sing-box run -C /usr/local/etc/sb3/conf/\nExecReload=/bin/kill -HUP \$MAINPID\nRestart=on-failure\nRestartSec=10\nLimitNOFILE=infinity\n\n[Install]\nWantedBy=multi-user.target" | sudo tee /etc/systemd/system/sb3.service

sudo systemctl enable sb3
