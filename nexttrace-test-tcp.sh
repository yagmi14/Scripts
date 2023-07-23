#!/bin/bash

echo "请选择:"
echo "0) 默认(执行所有命令)"
echo "1) China Telecom"
echo "2) China Unicom"
echo "3) China Mobile" 
echo "4) Optimized Network"

read -p "输入(0-4):" choice

case $choice in
  0)
    echo "默认,执行所有命令"
    nexttrace -Tp 65499 27.185.201.1
    nexttrace -Tp 65499 124.74.52.254 
    nexttrace -Tp 65499 61.144.6.18
    nexttrace -Tp 65499 61.240.159.62
    nexttrace -Tp 65499 220.196.190.38
    nexttrace -Tp 65499 163.177.38.106
    nexttrace -Tp 65499 111.62.68.52
    nexttrace -Tp 65499 120.204.34.2
    nexttrace -Tp 65499 120.198.26.254
    nexttrace -Tp 65499 58.32.4.1
    nexttrace -Tp 65499 210.13.67.2
    nexttrace -Tp 65499 223.70.155.6
    nexttrace -Tp 65499 211.156.140.17 
    nexttrace -Tp 65499 166.111.4.5
    ;;
  1)
    echo "China Telecom"
    nexttrace -Tp 65499 27.185.201.1
    nexttrace -Tp 65499 124.74.52.254
    nexttrace -Tp 65499 61.144.6.18
    ;;
  2)
    echo "China Unicom"  
    nexttrace -Tp 65499 61.240.159.62
    nexttrace -Tp 65499 220.196.190.38
    nexttrace -Tp 65499 163.177.38.106
    ;;
  3)
    echo "China Mobile"
    nexttrace -Tp 65499 111.62.68.52
    nexttrace -Tp 65499 120.204.34.2
    nexttrace -Tp 65499 120.198.26.254
    ;;
  4)
    echo "Optimized Network"
    nexttrace -Tp 65499 58.32.4.1
    nexttrace -Tp 65499 210.13.67.2
    nexttrace -Tp 65499 223.70.155.6
    nexttrace -Tp 65499 211.156.140.17
    nexttrace -Tp 65499 166.111.4.5
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
