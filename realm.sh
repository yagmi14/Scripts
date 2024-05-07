#!/bin/bash

# 检查realm是否已安装
if [ -f "/usr/local/bin/realm" ]; then
    echo "检测到realm已安装。"
    realm_status="已安装"
    realm_status_color="\033[0;32m" # 绿色
else
    echo "realm未安装。"
    realm_status="未安装"
    realm_status_color="\033[0;31m" # 红色
fi

# 检查realm服务状态
check_realm_service_status() {
    if systemctl is-active --quiet realm; then
        echo -e "\033[0;32m启用\033[0m" # 绿色
    else
        echo -e "\033[0;31m未启用\033[0m" # 红色
    fi
}

# 显示菜单的函数
show_menu() {
    clear
    echo "欢迎使用realm一键转发脚本"
    echo "================="
    echo "1. 部署环境"
    echo "2. 添加转发"
    echo "3. 删除转发"
    echo "4. 启动服务"
    echo "5. 停止服务"
    echo "6. 重启服务"
    echo "7. 一键卸载"
    echo "================="
    echo -e "realm 状态：${realm_status_color}${realm_status}\033[0m"
    echo -n "realm 转发状态："
    check_realm_service_status
}

# 部署环境的函数
deploy_realm() {
    bash <(curl -Lso- https://raw.githubusercontent.com/yagmi14/Scripts/main/realm-install.sh) && \
    mkdir -p /usr/local/etc/realm
    # 创建服务文件
    echo "[Unit]
Description=realm
After=network-online.target
Wants=network-online.target systemd-networkd-wait-online.service

[Service]
Type=simple
User=root
Restart=on-failure
RestartSec=5s
DynamicUser=true
ExecStart=/usr/local/bin/realm -c /usr/local/etc/realm/config.toml
[Install]
WantedBy=multi-user.target" > /etc/systemd/system/realm.service
    systemctl daemon-reload
    # 更新realm状态变量
    realm_status="已安装"
    realm_status_color="\033[0;32m" # 绿色
    echo "部署完成。"
}

# 卸载realm
uninstall_realm() {
    systemctl stop realm
    systemctl disable realm
    rm -f /etc/systemd/system/realm.service
    systemctl daemon-reload
    rm -rf /usr/local/bin/realm
    rm -rf /usr/local/etc/realm
    echo "realm已被卸载。"
    # 更新realm状态变量
    realm_status="未安装"
    realm_status_color="\033[0;31m" # 红色
}

# 删除转发规则的函数

delete_forward() {
    echo "当前转发规则："
    local IFS=$'\n' # 设置IFS仅以换行符作为分隔符
    local endpoints_lines=($(grep -n '[[endpoints]]' /usr/local/etc/realm/config.toml)) # 搜索所有包含[[endpoints]]的行
    if [ ${#endpoints_lines[@]} -eq 0 ]; then
        echo "没有发现任何转发规则。"
        return
    fi
    local index=1
    for line in "${endpoints_lines[@]}"; do
        local endpoint_line_number=$(echo $line | cut -d ':' -f 1)
        local remote_line=$(sed -n "${endpoint_line_number},/^\[\[endpoints\]\]/p" /usr/local/etc/realm/config.toml | grep 'remote =' | cut -d '"' -f 2)
        echo "${index}. $remote_line" # 提取并显示端口信息
        let index+=1
    done

    echo "请输入要删除的转发规则序号，直接按回车返回主菜单。"
    read -p "选择: " choice
    if [ -z "$choice" ]; then
        echo "返回主菜单。"
        return
    fi

    if ! [[ $choice =~ ^[0-9]+$ ]]; then
        echo "无效输入，请输入数字。"
        return
    fi

    if [ $choice -lt 1 ] || [ $choice -gt ${#endpoints_lines[@]} ]; then
        echo "选择超出范围，请输入有效序号。"
        return
    fi

    local chosen_line=${endpoints_lines[$((choice-1))]}
    local start_line=$(echo $chosen_line | cut -d ':' -f 1)
    local end_line
    if [ $choice -eq ${#endpoints_lines[@]} ]; then
        end_line=$(wc -l /usr/local/etc/realm/config.toml | awk '{print $1}')
    else
        end_line=$(echo ${endpoints_lines[$choice]} | cut -d ':' -f 1)
        end_line=$((end_line-1))
    fi

    # 使用sed删除选中的转发规则区块
    sed -i "${start_line},${end_line}d" /usr/local/etc/realm/config.toml

    echo "转发规则已删除。" && \
    systemctl restart realm && \
    echo "realm服务已重启。"
}





# 添加转发规则
add_forward() {
    while true; do
        read -p "请输入监听端口: " port1
        read -p "请输入IP: " ip
        read -p "请输入端口: " port2
        # 追加到config.toml文件
        echo "[[endpoints]]
listen = \"0.0.0.0:$port1\"
remote = \"$ip:$port2\"" >> /usr/local/etc/realm/config.toml
        
        read -p "是否继续添加(Y/N)? " answer
        if [[ $answer != "Y" && $answer != "y" ]]; then
            break
        fi
    done && \
    systemctl restart realm && \
    echo "realm服务已重启。"
}

# 启动服务
start_service() {
    systemctl daemon-reload
    systemctl restart realm
    systemctl enable realm
    echo "realm服务已启动并设置为开机自启。"
}

# 停止服务
stop_service() {
    systemctl stop realm
    echo "realm服务已停止。"
}

# 重启服务
restart_service() {
    systemctl restart realm
    echo "realm服务已重启。"
}

# 主循环
while true; do
    show_menu
    read -p "请选择一个选项: " choice
    case $choice in
        1)
            deploy_realm
            ;;
        2)
            add_forward
            ;;
        3)
            delete_forward
            ;;
        4)
            start_service
            ;;
        5)
            stop_service
            ;;
        6)
            restart_service
            ;;
        7)
            uninstall_realm
            ;;
        *)
            echo "无效选项: $choice"
            ;;
    esac
    read -p "按任意键继续..." key
done
