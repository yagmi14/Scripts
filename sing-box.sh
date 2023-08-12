#!/bin/bash

echo "请选择:"
echo "1) vless-xtls-grpc-reality"
echo "2) vless-xtls-vision-reality"
echo "3) shadowsocks"

read -p "输入(1-3):" choice

case $choice in
  1)
    read -p "请输入域名：" domain
    echo "vless-xtls-grpc-reality"
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":443,"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc"}}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > /usr/local/etc/sing-box/config.json; \
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  2)
    read -p "请输入域名：" domain
    echo "vless-xtls-vision-reality"
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":443,"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"'"$domain"'","reality":{"enabled":true,"handshake":{"server":"'"$domain"'","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}], "outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > /usr/local/etc/sing-box/config.json; \
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  3)
    echo "shadowsocks"
    folder="/usr/local/etc/sb40001"; if [ ! -d "$folder" ]; then mkdir -p "$folder"; echo "文件夹 $folder 创建成功！"; else echo "文件夹 $folder 已经存在，无需创建。"; fi
    echo '{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":40001,"sniff":true,"sniff_override_destination":true,"method":"aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}' > /usr/local/etc/sb40001/config.json
    /usr/local/bin/sing-box run -c /usr/local/etc/sb40001/config.json
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac

