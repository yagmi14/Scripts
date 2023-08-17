#!/bin/bash

echo "请选择:"
echo "01) 🇭🇰 Cera-HKG"
echo "02) 🇭🇰 IPRaft-HKG1"
echo "21) 🇺🇦 GlobalVM-IEV"
echo "22) 🇮🇸 1984-REF"
echo "23) 🇮🇱 Stark-IL"

read -p "输入选择:" choice

case $choice in
  01)
    echo "🇭🇰 Cera-HKG"
    ssh root@156.251.180.64 -p 40000
    ;;
  02)
    echo "🇭🇰 IPRaft-HKG1"
    ssh root@209.146.125.19 -p 53022
    ;;
  21)
    echo "🇺🇦 GlobalVM-IEV"
    ssh root@2a13:b487:4f00::50
    ;;
  22)
    echo "🇮🇸 1984-REF"
    ssh root@is.1984.wx2021.buzz -p 20031
    ;;
  23)
    echo "🇮🇱 Stark-IL"
    ssh root@il.sisl.wx2021.buzz -p 10016
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
