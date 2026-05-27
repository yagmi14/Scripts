#!/usr/bin/env bash
set -e

echo "==> 更新软件源并安装必要工具..."
sudo apt update
sudo apt install -y gnupg wget ca-certificates

echo "==> 导入 XanMod PGP 密钥..."
wget -qO - https://dl.xanmod.org/archive.key | \
sudo gpg --dearmor -o /usr/share/keyrings/xanmod-archive-keyring.gpg

echo "==> 添加 XanMod 官方仓库..."
echo 'deb [signed-by=/usr/share/keyrings/xanmod-archive-keyring.gpg] http://deb.xanmod.org trixie main' | \
sudo tee /etc/apt/sources.list.d/xanmod-release.list > /dev/null

echo "==> 更新软件源..."
sudo apt update

echo "==> 安装 XanMod x64v3 内核..."
sudo apt install -y linux-xanmod-x64v3

echo
echo "安装完成。请重启系统以启用 XanMod 内核："
echo "sudo reboot"
echo
echo "重启后可使用以下命令确认当前内核："
echo "uname -r"
