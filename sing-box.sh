#!/bin/bash

read -p "请输入域名: " ip_address

echo "请选择:"
echo "1) vless-xtls-grpc-reality"
echo "2) vless-xtls-vision-reality"

read -p "输入(1-2):" choice

case $choice in
  1)
    echo "vless-xtls-grpc-reality"
    cat > /usr/local/etc/sing-box/config.json <<EOF
    {
      "log": {
        "level": "info",
        "timestamp": true
      },
      "route": {
        "rules": [
          {
            "geosite": "cn",
            "geoip": "cn",
            "outbound": "direct"
          },
          {
            "geosite": "category-ads-all",
            "outbound": "block"
          }
        ]
      },
      "inbounds": [
        {
          "type": "vless",
          "tag": "vless-in",
          "listen": "::",
          "listen_port": 443,
          "sniff": true,
          "sniff_override_destination": true,
          "users": [
            {
              "uuid": "f8b5cc81-d25c-4d22-92b6-d10a055f7e98" // 或执行 ./sing-box generate uuid 生成
            }
          ],
          "tls": {
            "enabled": true,
            "server_name": "$ip_address", // 客户端可用的 serverName 列表，暂不支持 * 通配符
            "reality": {
              "enabled": true,
              "handshake": {
                "server": "$ip_address", // 目标网站最低标准：国外网站，支持 TLSv1.3、X25519 与 H2，域名非跳转用（主域名可能被用于跳转到 www）
                "server_port": 443
              },
              "private_key": "oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY", // 执行 ./sing-box generate reality-keypair 生成，填 "PrivateKey" 的值
              // "publicKey": "h2R5BJbjYH0Le3R8ilNqrRKjKQ0WRVjjDKCnRgTEVFk"
              "short_id": [ // 客户端可用的 shortId 列表，可用于区分不同的客户端
                "4c10a4acb2917613" // 0 到 f，长度为 2 的倍数，长度上限为 16，可留空，或执行 ./sing-box generate rand --hex 8 生成
              ]
            }
          },
          "transport": {
            "type": "grpc"
          }
        }
      ],
      "outbounds": [
        {
          "type": "direct",
          "tag": "direct"
        },
        {
          "type": "block",
          "tag": "block"
        }
      ]
    }
    EOF
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  2)
    echo "vless-xtls-vision-reality"  
    cat > /usr/local/etc/sing-box/config.json <<EOF
    {
      "log": {
        "level": "info",
        "timestamp": true
      },
      "route": {
        "rules": [
          {
            "geosite": "cn",
            "geoip": "cn",
            "outbound": "direct"
          },
          {
            "geosite": "category-ads-all",
            "outbound": "block"
          }
        ]
      },
      "inbounds": [
        {
          "type": "vless",
          "tag": "vless-in",
          "listen": "::",
          "listen_port": 443,
          "sniff": true,
          "sniff_override_destination": true,
          "users": [
            {
              "uuid": "f8b5cc81-d25c-4d22-92b6-d10a055f7e98", // 或执行 ./sing-box generate uuid 生成
              "flow": "xtls-rprx-vision"
            }
          ],
          "tls": {
            "enabled": true,
            "server_name": "$ip_address", // 客户端可用的 serverName 列表，暂不支持 * 通配符
            "reality": {
              "enabled": true,
              "handshake": {
                "server": "$ip_address", // 目标网站最低标准：国外网站，支持 TLSv1.3、X25519 与 H2，域名非跳转用（主域名可能被用于跳转到 www）
                "server_port": 443
              },
              "private_key": "oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY", // 执行 ./sing-box generate reality-keypair 生成，填 "PrivateKey" 的值
              // "publicKey": "h2R5BJbjYH0Le3R8ilNqrRKjKQ0WRVjjDKCnRgTEVFk"
              "short_id": [ // 客户端可用的 shortId 列表，可用于区分不同的客户端
                "4c10a4acb2917613" // 0 到 f，长度为 2 的倍数，长度上限为 16，可留空，或执行 ./sing-box generate rand --hex 8 生成
              ]
            }
          }
        }
      ],
      "outbounds": [
        {
          "type": "direct",
          "tag": "direct"
        },
        {
          "type": "block",
          "tag": "block"
        }
      ]
    }
    EOF
    /usr/local/bin/sing-box run -c /usr/local/etc/sing-box/config.json
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac

