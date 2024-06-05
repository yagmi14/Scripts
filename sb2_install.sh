#!/bin/bash
set -e

bash <(curl -fsSL https://sing-box.app/deb-install.sh)

mkdir -p /usr/local/etc/sb2/conf

echo '{"log":{"disabled":false,"level":"info","timestamp":true}}' > /usr/local/etc/sb2/conf/00_log.json

echo '{"route":{"rule_set":[{"tag":"geosite-openai","type":"remote","format":"binary","url":"https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-openai.srs"}],"rules":[{"domain":"api.openai.com","outbound":"direct"},{"rule_set":"geosite-openai","outbound":"direct"}]}}' > /usr/local/etc/sb2/conf/02_route.json

echo '{"experimental":{"cache_file":{"enabled":true,"path":"/usr/local/etc/sb2/cache.db"}}}' > /usr/local/etc/sb2/conf/03_experimental.json

echo '{"dns":{"servers":[{"address":"local"}]}}' > /usr/local/etc/sb2/conf/04_dns.json

echo -e "[Unit]\nDescription=sing-box service\nDocumentation=https://sing-box.sagernet.org\nAfter=network.target nss-lookup.target\n\n[Service]\nUser=root\nType=simple\nNoNewPrivileges=yes\nTimeoutStartSec=0\nExecStart=/usr/bin/sing-box run -C /usr/local/etc/sb2/conf/\nExecReload=/bin/kill -HUP \$MAINPID\nRestart=on-failure\nRestartSec=10\nLimitNOFILE=infinity\n\n[Install]\nWantedBy=multi-user.target" | sudo tee /etc/systemd/system/sb2.service

sudo systemctl enable sb2
