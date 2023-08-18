#!/bin/bash

options=(
  "01) 🇭🇰 Cera-HKG"
  "02) 🇭🇰 HKBN-HKG"
  "03) 🇭🇰 IPRaft-HKG1"
  "04) 🇭🇰 IPRaft-HKG2"
  "05) 🇭🇰 IPRaft-HKG3"
  "06) 🇭🇰 IPRaft-HKG4"
  "07) 🇭🇰 Miku-HKG"
  "21) 🇺🇸 IPRaft-SJC"
  "31) 🇺🇦 GlobalVM-IEV"
  "32) 🇮🇸 1984-REF"
  "33) 🇮🇱 Stark-IL"
)

formatted_options=$(printf "%s\n" "${options[@]}" | column -c 80)

echo "请选择:"
echo "$formatted_options"

read -p "输入选择:" choice

case $choice in
  01)
    echo "🇭🇰 Cera-HKG"
    ssh root@156.251.180.64 -p 40000
    ;;
  02)
    echo "🇭🇰 HKBN-HKG"
    ssh root@hkbn.miaoddns.top -p 40000
    ;;
  03)
    echo "🇭🇰 IPRaft-HKG1"
    ssh root@209.146.125.124 -p 40000
    ;;
  04)
    echo "🇭🇰 IPRaft-HKG2"
    ssh root@209.146.125.206 -p 40000
    ;;
  05)
    echo "🇭🇰 IPRaft-HKG3"
    ssh root@209.146.125.19 -p 53022
    ;;
  06)
    echo "🇭🇰 IPRaft-HKG4"
    ssh root@209.146.125.105 -p 40000
    ;;
  07)
    echo "🇭🇰 Miku-HKG"
    ssh root@38.150.15.114 -p 40000
    ;;
  21)
    echo "🇺🇸 IPRaft-SJC"
    ssh root@38.207.149.43 -p 40000
    ;;
  31)
    echo "🇺🇦 GlobalVM-IEV"
    ssh root@2a13:b487:4f00::50
    ;;
  32)
    echo "🇮🇸 1984-REF"
    ssh root@is.1984.wx2021.buzz -p 20031
    ;;
  33)
    echo "🇮🇱 Stark-IL"
    ssh root@il.sisl.wx2021.buzz -p 10016
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
