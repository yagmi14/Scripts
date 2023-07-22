#!/bin/bash

read -p "请输入IP地址或域名: " ip_address

RealiTLScanner -addr $ip_address -showFail -o
