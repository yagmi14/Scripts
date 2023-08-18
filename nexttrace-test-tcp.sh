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
    nexttrace -T -p 65499 27.185.201.1 && \
    nexttrace -T -p 65499 124.74.52.254 && \ 
    nexttrace -T -p 65499 61.144.6.18 && \
    nexttrace -T -p 65499 61.240.159.62 && \
    nexttrace -T -p 65499 220.196.190.38 && \
    nexttrace -T -p 65499 163.177.38.106 && \
    nexttrace -T -p 65499 111.62.68.52 && \
    nexttrace -T -p 65499 120.204.34.2 && \
    nexttrace -T -p 65499 120.198.26.254 && \
    nexttrace -T -p 40001 58.32.4.1 && \
    nexttrace -T -p 40001 210.13.67.2 && \
    nexttrace -T -p 40001 223.70.155.6 && \
    nexttrace -T 211.156.140.17 && \
    nexttrace -T 166.111.4.39 && \
    nexttrace -T 159.226.254.1
    ;;
  1)
    echo "China Telecom"
    nexttrace -T -p 65499 219.141.150.166 && \
    nexttrace -T -p 65499 27.185.201.1 && \
    nexttrace -T -p 65499 61.178.65.90 && \
    nexttrace -T -p 65499 124.74.52.254 && \
    nexttrace -T -p 65499 61.150.151.122 && \
    nexttrace -T -p 65499 61.144.6.18
    ;;
  2)
    echo "China Unicom"  
    nexttrace -T -p 65499 61.135.214.54 && \
    nexttrace -T -p 65499 61.240.159.62 && \
    nexttrace -T -p 65499 60.13.41.246 && \
    nexttrace -T -p 40001 cu.lightnovel.cn && \
    nexttrace -T -p 65499 220.196.190.38 && \
    nexttrace -T -p 65499 58.20.176.94 && \
    nexttrace -T -p 65499 163.177.38.106
    ;;
  3)
    echo "China Mobile"
    nexttrace -T 111.13.111.99 && \
    nexttrace -T -p 65499 111.62.68.52 && \
    nexttrace -T 211.139.80.33 && \
    nexttrace -T -p 65499 120.204.34.2 && \
    nexttrace -T 111.8.9.73 && \
    nexttrace -T -p 65499 120.198.26.254
    ;;
  4)
    echo "Optimized Network"
    nexttrace -T -p 40001 58.32.4.1 && \
    nexttrace -T -p 40001 210.13.67.2 && \
    nexttrace -T -p 40001 223.70.155.6 && \
    nexttrace -T 211.156.140.17 && \
    nexttrace -T 166.111.4.39 && \
    nexttrace -T 159.226.254.1
    ;;
  *)
    echo "无效输入,请重试!"
    ;;
esac
