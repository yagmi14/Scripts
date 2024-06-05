#!/bin/bash

# 检查iptables是否已安装
if ! command -v iptables &> /dev/null
then
    echo "iptables未安装。正在安装iptables..."
    sudo apt-get update && sudo apt-get install iptables -y
fi

# 检查iptables-persistent是否已安装
if ! dpkg -l | grep iptables-persistent &> /dev/null
then
    echo "iptables-persistent未安装。正在安装iptables-persistent..."
    sudo apt-get update && sudo apt install iptables-persistent -y
fi

# 启用IP转发
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null

# 查看、添加和删除规则的选项
echo "请选择以下选项："
echo "1. 查看当前NAT规则"
echo "2. 添加新的NAT规则"
echo "3. 删除特定NAT规则"
echo "4. 退出"
read -p "请输入你的选择（1-4）: " choice

case $choice in
    1)
        echo "当前NAT规则如下："
        sudo iptables -t nat -L PREROUTING
        ;;
    2)
        read -p "请输入要重定向的端口范围: " port_range
        if [ -z "$port_range" ]
        then
            port_range="49000:50000"
        fi
        read -p "请输入要重定向到的端口: " port
        if [ -z "$port" ]
        then
            port=40007
        fi
        echo "你输入的端口范围是：$port_range"
        echo "你输入的端口号是：$port"
        echo "添加NAT规则，将$port_range端口转发到$port..."
        sudo iptables -t nat -A PREROUTING -p udp -m udp --dport $port_range -m comment --comment "NAT $port_range to $port (Sing-box Family Bucket)" -j DNAT --to-destination :$port
        sudo iptables-save > /etc/iptables/rules.v4
        sudo iptables-save > /etc/iptables/rules.v6
        echo "规则已添加。"
        ;;
    3)
        read -p "请输入要删除的规则的端口号: " del_port
        echo "正在删除所有转发到端口$del_port的NAT规则..."
        # 查找与del_port相关的规则行号
        rule_line_numbers=$(sudo iptables -t nat -L PREROUTING --line-numbers | grep "to::$del_port" | awk '{print $1}' | tac)
        # 如果找到规则，则逐行删除
        if [ -n "$rule_line_numbers" ]; then
            for line in $rule_line_numbers; do
                sudo iptables -t nat -D PREROUTING $line
            done
            sudo iptables-save > /etc/iptables/rules.v4
            sudo iptables-save > /etc/iptables/rules.v6
            echo "规则已删除。"
        else
            echo "没有找到转发到端口$del_port的规则。"
        fi
        ;;
    4)
        echo "退出脚本。"
        exit 0
        ;;
    *)
        echo "无效的选项。"
        ;;
esac
