#!/bin/bash

# 提示用户输入服务名称
read -p "请输入要操作的服务名称: " service_name

# 提示用户选择操作
echo "请选择要执行的操作:"
echo "1. 启动服务"
echo "2. 重启服务"
echo "3. 关闭服务"
echo "4. 查看服务状态"
echo "5. 重新加载配置文件"
echo "6. 禁用并删除服务文件"
echo "7. systemctl cat"
echo "8. View logs in real time"
read -p "输入操作编号: " choice

# 根据用户选择执行相应的操作
case $choice in
  1)
    sudo systemctl start $service_name
    sudo systemctl status $service_name
    echo "$service_name 服务已启动"
    ;;
  2)
    sudo systemctl restart $service_name
    sudo systemctl status $service_name
    echo "$service_name 服务已重启"
    ;;  
  3)
    sudo systemctl stop $service_name
    echo "$service_name 服务已关闭"
    ;;  
  4)
    sudo systemctl status $service_name
    ;;
  5)
    sudo systemctl daemon-reload
    echo "配置文件已重新加载"
    ;;
  6)
    sudo systemctl stop $service_name
    sudo systemctl disable $service_name
    service_file="/etc/systemd/system/${service_name}.service"
    if [ -f "$service_file" ]; then
      sudo rm -f "$service_file"
      echo "$service_name 服务已禁用并删除 service 文件"
      sudo systemctl daemon-reload
    else
      echo "未找到 $service_name 的 service 文件"
    fi
    ;;
  7)
    sudo systemctl cat $service_name
    ;;
  8)
    sudo journalctl -u $service_name -o cat -f
    ;;
  *)
    echo "无效的操作编号"
    ;;
esac
