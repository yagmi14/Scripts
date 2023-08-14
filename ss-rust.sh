#!/bin/bash

echo "Enter listening port:"
read port

mkdir ss-rust && cd ss-rust
curl -Lo /root/ss-rust/ss-rust https://github.com/shadowsocks/shadowsocks-rust/releases/download/v1.15.3/shadowsocks-v1.15.3.x86_64-unknown-linux-gnu.tar.xz
sudo apt-get install xz-utils apt-utils -y
tar xvf ss-rust
chown root:root ./ss*
mv ./ss* /usr/local/bin/
cd && rm -rf ss-rust
mkdir /etc/ss-rust/

cat > /etc/ss-rust/config.json <<EOF
{
    "server": "::",
    "server_port": $port,
    "password": "W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=",
    "method": "aes-256-gcm",
    "fast_open": true,
    "mode": "tcp_and_udp",
    "user":"nobody",
    "timeout":300,
    "nameserver":"dns.google"
}
EOF
/usr/local/bin/ssserver -c /etc/ss-rust/config.json
