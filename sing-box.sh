#!/bin/bash

echo "请选择:"
echo "1) vless-xtls-grpc-reality"
echo "2) vless-xtls-vision-reality"
echo "3) shadowsocks"
echo "4) ShadowTLS v3"
echo "5) reality+shadowsocks"
echo "6) shadowsocks+shadowsocks"

read -p "请选择:" choice

case $choice in
  1)
    echo "vless-xtls-grpc-reality"
    read -p "listening port:" port
    read -p "domain:" domain
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":'$port',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"grpc"}}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl restart "sb${port1}" && sudo systemctl status "sb${port1}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  2)
    echo "vless-xtls-vision-reality"
    read -p "listening port:" port
    read -p "domain:" domain
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":'$port',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}], "outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl restart "sb${port1}" && sudo systemctl status "sb${port1}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  3)
    echo "shadowsocks"
    read -p "Select method:
    1. 2022-blake3-aes-256-gcm
    2. aes-256-gcm
    (press plz): " method_choice

    if [[ "$method_choice" == "1" ]]; then
      method="2022-blake3-aes-256-gcm"
    elif [[ "$method_choice" == "2" ]]; then
      method="aes-256-gcm"
    else
      method="2022-blake3-aes-256-gcm"
    fi
    
    read -p "listening port:" port
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":'$port',"sniff":true,"sniff_override_destination":true,"method":"'"$method"'","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl restart "sb${port}" && sudo systemctl status "sb${port}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  4)
    echo "ShadowTLS v3"
    read -p "listening port:" port
    read -p "domain:" domain
    service_file="/etc/systemd/system/sb${port}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port exists."; sudo systemctl stop "sb${port}"; else echo "Service file for port $port does not exist."; fi
    folder="/usr/local/etc/sb$port"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"shadowtls","tag":"st-in","listen":"::","listen_port":'$port',"version":3,"users":[{"name":"yagmi14","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"handshake":{"server":"'"$domain"'","server_port":443},"strict_mode":true,"detour":"ss-in"},{"type":"shadowsocks","tag":"ss-in","listen":"127.0.0.1","network":"tcp","method":"2022-blake3-aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl restart "sb${port1}" && sudo systemctl status "sb${port1}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  5)
    echo "reality+shadowsocks"
    read -p "listening port:" port1
    read -p "domain:" domain
    
    read -p "Select outbounds method:
    1. 2022-blake3-aes-256-gcm
    2. aes-256-gcm
    (press plz): " method_choice

    if [[ "$method_choice" == "1" ]]; then
      method="2022-blake3-aes-256-gcm"
    elif [[ "$method_choice" == "2" ]]; then
      method="aes-256-gcm"
    else
      method="2022-blake3-aes-256-gcm"
    fi
    
    read -p "remote ip:" ip
    read -p "remote port:" port2
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl stop "sb${port1}"; else echo "Service file for port $port1 does not exist."; fi
    folder="/usr/local/etc/sb$port1"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":'$port1',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"grpc"}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"'"$ip"'","server_port":'$port2',"method":"'"$method"'","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl restart "sb${port1}" && sudo systemctl status "sb${port1}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  6)
    echo "shadowsocks+shadowsocks"
    read -p "Select inbounds method:
    1. 2022-blake3-aes-256-gcm
    2. aes-256-gcm
    (press plz): " method_choice1

    if [[ "$method_choice1" == "1" ]]; then
      method1="2022-blake3-aes-256-gcm"
    elif [[ "$method_choice1" == "2" ]]; then
      method1="aes-256-gcm"
    else
      method1="2022-blake3-aes-256-gcm"
    fi

    read -p "listening port:" port1

    read -p "Select outbounds method:
    1. 2022-blake3-aes-256-gcm
    2. aes-256-gcm
    (press plz): " method_choice2

    if [[ "$method_choice2" == "1" ]]; then
      method2="2022-blake3-aes-256-gcm"
    elif [[ "$method_choice2" == "2" ]]; then
      method2="aes-256-gcm"
    else
      method2="2022-blake3-aes-256-gcm"
    fi
    
    read -p "remote ip:" ip
    read -p "remote port:" port2
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl stop "sb${port1}"; else echo "Service file for port $port1 does not exist."; fi
    folder="/usr/local/etc/sb$port1"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":'$port1',"sniff":true,"sniff_override_destination":true,"method":"'"$method1"'","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"'"$ip"'","server_port":'$port2',"method":"'"$method2"'","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}' > "$folder/config.json"
    service_file="/etc/systemd/system/sb${port1}.service"; if [ -f "$service_file" ]; then echo "Service file for port $port1 exists."; sudo systemctl restart "sb${port1}" && sudo systemctl status "sb${port1}"; else /usr/local/bin/sing-box run -c "$folder/config.json"; fi
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac

