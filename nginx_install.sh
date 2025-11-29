#!/bin/bash
set -e

echo "更新系统并安装必要工具..."
apt update && apt install -y curl gnupg2 ca-certificates lsb-release debian-archive-keyring

echo "下载并添加 Nginx 官方签名密钥..."
curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor \
| sudo tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null

echo "验证密钥导入..."
gpg --dry-run --quiet --import --import-options import-show /usr/share/keyrings/nginx-archive-keyring.gpg

echo "添加 Nginx 官方源..."
echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
http://nginx.org/packages/mainline/debian $(lsb_release -cs) nginx" \
| sudo tee /etc/apt/sources.list.d/nginx.list

echo "设置 Nginx 源优先级..."
echo -e "Package: *\nPin: origin nginx.org\nPin: release o=nginx\nPin-Priority: 900\n" \
| sudo tee /etc/apt/preferences.d/99nginx

echo "更新软件源并安装 Nginx..."
sudo apt update && sudo apt install -y nginx

echo "查看 Nginx 版本..."
sudo nginx -v

echo "启动并设置 Nginx 开机自启..."
sudo systemctl enable --now nginx

echo "查看 Nginx 状态..."
sudo systemctl status nginx
