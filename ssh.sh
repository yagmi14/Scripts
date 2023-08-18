#!/bin/bash

echo "请选择:"
echo "01) 🇭🇰 Cera-HKG"
echo "02) 🇭🇰 IPRaft-HKG1"
echo "03) 🇭🇰 IPRaft-HKG2"
echo "04) 🇭🇰 IPRaft-HKG3"
echo "05) 🇭🇰 IPRaft-HKG4"
echo "21) 🇺🇸 IPRaft-SJC"
echo "31) 🇺🇦 GlobalVM-IEV"
echo "32) 🇮🇸 1984-REF"
echo "33) 🇮🇱 Stark-IL"

read -p "输入选择:" choice

case $choice in
  01)
    echo "🇭🇰 Cera-HKG"
    ssh root@156.251.180.64 -p 40000
    ;;
  02)
    echo "🇭🇰 IPRaft-HKG1"
    ssh root@209.146.125.124 -p 40000
    ;;
  03)
    echo "🇭🇰 IPRaft-HKG2"
    ssh root@209.146.125.206 -p 40000
    ;;
  04)
    echo "🇭🇰 IPRaft-HKG3"
    ssh root@209.146.125.19 -p 53022
    ;;
  05)
    echo "🇭🇰 IPRaft-HKG4"
    ssh root@209.146.125.105 -p 40000
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
    echo "🇮🇸 1984-REF"
    ssh root@is.1984.wx2021.buzz -p 20031
    ;;
  33)
    echo "🇮🇱 Stark-IL"
    ssh root@il.sisl.wx2021.buzz -p 10016
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
