#!/bin/bash

read -p "name:" name

cat > /etc/init.d/$name <<EOF
#!/sbin/openrc-run
# singbox - Example service script for sing-box

command="/usr/local/bin/sing-box"
command_args="run -c /usr/local/etc/$name/config.json"

depend() {
    need net
}

start() {
    ebegin "Starting $name"
    start-stop-daemon --start --exec \$command -- \$command_args
    eend 0
}

stop() {
    ebegin "Stopping $name"
    start-stop-daemon --stop --exec \$command -- \$command_args
    eend 0
}

restart() {
    ebegin "Restarting $name"
    start-stop-daemon --stop --exec \$command -- \$command_args
    sleep 1
    start-stop-daemon --start --exec \$command -- \$command_args
    eend 0
}
EOF

chmod +x /etc/init.d/$name;
rc-update add $name default;
rc-service $name start;
rc-service $name status





