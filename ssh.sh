#!/bin/bash

echo "请选择:"
echo "1) 🇭🇰 IPRaft-HKG1"
echo "2) 🇺🇦 GlobalVM-IEV"
echo "3) 🇮🇸 1984-REF"
echo "4) 🇮🇱 Stark-IL"

read -p "输入选择:" choice

case $choice in
  1)
    echo "🇭🇰 IPRaft-HKG1"
    ssh root@209.146.125.19 -p 53022
    ;;
  2)
    echo "🇺🇦 GlobalVM-IEV"
    ssh root@2a13:b487:4f00::50
    ;;
  3)
    echo "🇮🇸 1984-REF"
    ssh root@is.1984.wx2021.buzz -p 20031
    ;;
  4)
    echo "🇮🇱 Stark-IL"
    ssh root@il.sisl.wx2021.buzz -p 10016
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
