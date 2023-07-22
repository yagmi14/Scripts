#!/bin/bash

read -p "请输入IP地址或域名: " ip_address

openssl s_client -connect $ip_address:443 -status
