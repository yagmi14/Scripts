#!/bin/bash

echo "请选择:"
echo "1) vless-xtls-grpc-reality"
echo "2) vless-xtls-vision-reality"
echo "3) shadowsocks"
echo "4) reality+ss"

read -p "输入(1-4):" choice

case $choice in
  1)
    echo "vless-xtls-grpc-reality"
    read -p "domain:" domain
    service_file="/etc/systemd/system/sing-box.service"; if [ -f "$service_file" ]; then echo "Service file exists."; sudo systemctl stop sing-box; else echo "Service file does not exist."; fi
    folder="/usr/local/etc/sing-box"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":443,"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc"}}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > /usr/local/etc/sing-box/config.json; \
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  2)
    echo "vless-xtls-vision-reality"
    read -p "domain:" domain
    service_file="/etc/systemd/system/sing-box.service"; if [ -f "$service_file" ]; then echo "Service file exists."; sudo systemctl stop sing-box; else echo "Service file does not exist."; fi
    folder="/usr/local/etc/sing-box"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi    
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":443,"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}], "outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > /usr/local/etc/sing-box/config.json; \
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  3)
    read -p "listening port:" port
    echo "shadowsocks"
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":'$port',"sniff":true,"sniff_override_destination":true,"method":"2022-blake3-aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"}]}' > "$folder/config.json"
    /usr/local/bin/sing-box run -c "$folder/config.json"
    ;;
  4)
    echo "shadowsocks"
    read -p "listening port:" port1
    read -p "domain:" domain
    read -p "ip:" ip
    read -p "remote port:" port2
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":'$port1',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"$domain","reality":{"enabled":true,"handshake":{"server":"$domain","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc"}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"$ip","server_port":'$port2',"method":"2022-blake3-aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}' > "$folder/config.json"
    /usr/local/bin/sing-box run -c "$folder/config.json"
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac

