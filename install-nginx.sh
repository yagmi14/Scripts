#!/usr/bin/env bash

set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

NGINX_KEYRING="/usr/share/keyrings/nginx-archive-keyring.gpg"
NGINX_REPO_FILE="/etc/apt/sources.list.d/nginx.list"
NGINX_PIN_FILE="/etc/apt/preferences.d/99nginx"
SSL_REJECT_FILE="/etc/nginx/conf.d/00-ssl-default-reject.conf"
WEBSOCKET_MAP_FILE="/etc/nginx/conf.d/00-map-websocket.conf"
LE_WEBROOT_SNIPPET="/etc/nginx/snippets/letsencrypt-webroot.conf"
LE_WEBROOT="/usr/share/nginx/html"

log() {
    printf '\033[1;32m[INFO]\033[0m %s\n' "$*"
}

warn() {
    printf '\033[1;33m[WARN]\033[0m %s\n' "$*"
}

error() {
    printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2
}

trap 'error "脚本执行失败，出错行号：${LINENO}"' ERR

if [[ "${EUID}" -ne 0 ]]; then
    error "请使用 root 用户运行此脚本。"
    error "例如：sudo bash $0"
    exit 1
fi

if [[ ! -f /etc/os-release ]]; then
    error "无法识别当前操作系统。"
    exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${ID:-}" != "debian" ]]; then
    error "此脚本仅适用于 Debian。当前系统：${PRETTY_NAME:-未知}"
    exit 1
fi

log "当前系统：${PRETTY_NAME}"

log "安装基础依赖……"
apt-get update
apt-get install -y \
    curl \
    gnupg2 \
    ca-certificates \
    lsb-release \
    debian-archive-keyring

CODENAME="$(lsb_release -cs)"

if [[ -z "${CODENAME}" ]]; then
    error "无法获取 Debian 发行版代号。"
    exit 1
fi

log "检测到 Debian 代号：${CODENAME}"

log "下载并安装 nginx.org 签名密钥……"
curl -fsSL https://nginx.org/keys/nginx_signing.key \
    | gpg --dearmor --yes \
    > "${NGINX_KEYRING}"

chmod 0644 "${NGINX_KEYRING}"

log "显示 Nginx 签名密钥信息……"
gpg \
    --dry-run \
    --quiet \
    --no-keyring \
    --import \
    --import-options import-show \
    "${NGINX_KEYRING}"

log "配置 nginx.org Mainline 软件源……"
cat > "${NGINX_REPO_FILE}" <<EOF
deb [signed-by=${NGINX_KEYRING}] http://nginx.org/packages/mainline/debian ${CODENAME} nginx
EOF

log "设置 nginx.org 软件包优先级……"
cat > "${NGINX_PIN_FILE}" <<'EOF'
Package: *
Pin: origin nginx.org
Pin: release o=nginx
Pin-Priority: 900
EOF

log "更新软件源并安装 Nginx Mainline……"
apt-get update
apt-get install -y nginx

log "启用并启动 Nginx……"
systemctl enable --now nginx

log "安装 Certbot 和 Nginx 插件……"
apt-get install -y certbot python3-certbot-nginx

log "创建 Nginx 配置目录……"
mkdir -p /etc/nginx/conf.d
mkdir -p /etc/nginx/snippets
mkdir -p "${LE_WEBROOT}/.well-known/acme-challenge"

log "配置默认 HTTPS 拒绝握手……"
cat > "${SSL_REJECT_FILE}" <<'EOF'
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_reject_handshake on;
}
EOF

log "配置 WebSocket Connection Upgrade 映射……"
cat > "${WEBSOCKET_MAP_FILE}" <<'EOF'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
EOF

log "创建 Let's Encrypt Webroot 验证片段……"
cat > "${LE_WEBROOT_SNIPPET}" <<'EOF'
location ^~ /.well-known/acme-challenge/ {
    root /usr/share/nginx/html;
    default_type "text/plain";
    try_files $uri =404;
}
EOF

chown -R root:root /etc/nginx
chmod 0755 /etc/nginx/snippets
chmod 0644 \
    "${SSL_REJECT_FILE}" \
    "${WEBSOCKET_MAP_FILE}" \
    "${LE_WEBROOT_SNIPPET}"

log "检查 Nginx 配置……"
nginx -t

log "重新加载 Nginx……"
systemctl reload nginx

log "检查 Nginx 服务状态……"
if systemctl is-active --quiet nginx; then
    printf '\n'
    log "Nginx 安装及基础配置完成。"
    nginx -v
    certbot --version
    printf '\n'
    systemctl --no-pager --full status nginx | head -n 15
else
    error "Nginx 服务未正常运行。"
    journalctl -u nginx --no-pager -n 50
    exit 1
fi
