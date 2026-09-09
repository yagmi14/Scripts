#!/usr/bin/env bash

set -e

# ============================================================
# Zsh + Oh My Zsh 一键安装
# 自动判断出口 IP：
#   CN      -> 使用 ghfast.top
#   非 CN   -> 使用 GitHub 官方源
#   检测失败 -> 默认 GitHub 官方源
# ============================================================

echo
echo "============================================"
echo " Zsh + Oh My Zsh 自动安装脚本"
echo "============================================"
echo

# ------------------------------------------------------------
# 1. 必须使用 root
# ------------------------------------------------------------

if [ "$(id -u)" -ne 0 ]; then
    echo "请使用 root 用户执行此脚本："
    echo
    echo "sudo bash $0"
    exit 1
fi

# 当前安装用户
TARGET_USER="$(whoami)"
TARGET_HOME="$HOME"

echo "安装用户: $TARGET_USER"
echo "HOME: $TARGET_HOME"
echo

# ------------------------------------------------------------
# 2. 安装基础依赖
# ------------------------------------------------------------

echo "[1/5] 安装基础软件..."

export DEBIAN_FRONTEND=noninteractive

apt-get update

apt-get install -y \
    zsh \
    wget \
    git \
    curl \
    lsof \
    screen \
    net-tools \
    cron \
    chrony \
    rdate \
    dnsutils \
    unzip \
    iproute2 \
    ifupdown \
    nano \
    sudo

echo
echo "基础软件安装完成。"
echo

# ------------------------------------------------------------
# 3. 检测出口国家
# ------------------------------------------------------------

echo "[2/5] 检测服务器出口 IP 所在地区..."

COUNTRY=""

# 方法 1：Cloudflare
COUNTRY="$(
    curl -4 -fsSL \
        --connect-timeout 5 \
        --max-time 8 \
        https://www.cloudflare.com/cdn-cgi/trace 2>/dev/null \
    | awk -F= '$1=="loc" {print toupper($2); exit}'
)" || true

# 方法 2：ipinfo.io
if [ -z "$COUNTRY" ]; then
    COUNTRY="$(
        curl -4 -fsSL \
            --connect-timeout 5 \
            --max-time 8 \
            https://ipinfo.io/country 2>/dev/null \
        | tr -d '\r\n' \
        | tr '[:lower:]' '[:upper:]'
    )" || true
fi

# 方法 3：ifconfig.co
if [ -z "$COUNTRY" ]; then
    COUNTRY="$(
        curl -4 -fsSL \
            --connect-timeout 5 \
            --max-time 8 \
            https://ifconfig.co/country-iso 2>/dev/null \
        | tr -d '\r\n' \
        | tr '[:lower:]' '[:upper:]'
    )" || true
fi

echo

if [ "$COUNTRY" = "CN" ]; then
    USE_CN=true
    echo "检测结果：CN"
    echo "当前出口位于中国大陆。"
    echo "将使用 CN 加速源。"
else
    USE_CN=false

    if [ -n "$COUNTRY" ]; then
        echo "检测结果：$COUNTRY"
    else
        echo "无法确定出口国家。"
    fi

    echo "将使用默认国际源。"
fi

echo

# ------------------------------------------------------------
# 4. 设置下载地址
# ------------------------------------------------------------

if [ "$USE_CN" = true ]; then

    OMZ_INSTALL_URL="https://ghfast.top/https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"

    SYNTAX_URL="https://ghfast.top/https://github.com/zsh-users/zsh-syntax-highlighting.git"

    AUTOSUGGESTIONS_URL="https://ghfast.top/https://github.com/zsh-users/zsh-autosuggestions.git"

else

    OMZ_INSTALL_URL="https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"

    SYNTAX_URL="https://github.com/zsh-users/zsh-syntax-highlighting.git"

    AUTOSUGGESTIONS_URL="https://github.com/zsh-users/zsh-autosuggestions.git"

fi

# ------------------------------------------------------------
# 5. 安装 Oh My Zsh
# ------------------------------------------------------------

echo "[3/5] 安装 Oh My Zsh..."

if [ -d "$TARGET_HOME/.oh-my-zsh" ]; then

    echo "检测到 Oh My Zsh 已安装："
    echo "$TARGET_HOME/.oh-my-zsh"
    echo
    echo "跳过 Oh My Zsh 安装。"

else

    echo "下载地址："
    echo "$OMZ_INSTALL_URL"
    echo

    TMP_INSTALL="$(mktemp)"

    curl -fsSL \
        --connect-timeout 10 \
        --max-time 60 \
        "$OMZ_INSTALL_URL" \
        -o "$TMP_INSTALL"

    # 使用 unattended，避免官方脚本询问：
    #
    # Do you want to change your default shell to zsh? [Y/n]
    #
    RUNZSH=no \
    CHSH=no \
    KEEP_ZSHRC=no \
        sh "$TMP_INSTALL" --unattended

    rm -f "$TMP_INSTALL"

    echo
    echo "Oh My Zsh 安装完成。"

fi

echo

# ------------------------------------------------------------
# 6. 设置默认 shell
# ------------------------------------------------------------

echo "[4/5] 设置默认 Shell..."

ZSH_BIN="$(command -v zsh)"

CURRENT_SHELL="$(getent passwd "$TARGET_USER" | cut -d: -f7)"

if [ "$CURRENT_SHELL" = "$ZSH_BIN" ]; then

    echo "默认 Shell 已经是：$ZSH_BIN"

else

    echo "当前 Shell：$CURRENT_SHELL"
    echo "修改为：$ZSH_BIN"

    chsh -s "$ZSH_BIN" "$TARGET_USER"

    echo "默认 Shell 修改完成。"

fi

echo

# ------------------------------------------------------------
# 7. 安装插件
# ------------------------------------------------------------

echo "[5/5] 安装 Zsh 插件..."

ZSH_CUSTOM="${ZSH_CUSTOM:-$TARGET_HOME/.oh-my-zsh/custom}"

PLUGIN_DIR="$ZSH_CUSTOM/plugins"

mkdir -p "$PLUGIN_DIR"

# -----------------------------
# zsh-autosuggestions
# -----------------------------

AUTO_DIR="$PLUGIN_DIR/zsh-autosuggestions"

if [ -d "$AUTO_DIR/.git" ]; then

    echo
    echo "zsh-autosuggestions 已存在，跳过安装。"

else

    echo
    echo "安装 zsh-autosuggestions..."

    rm -rf "$AUTO_DIR"

    git clone \
        --depth=1 \
        "$AUTOSUGGESTIONS_URL" \
        "$AUTO_DIR"

fi

# -----------------------------
# zsh-syntax-highlighting
# -----------------------------

SYNTAX_DIR="$PLUGIN_DIR/zsh-syntax-highlighting"

if [ -d "$SYNTAX_DIR/.git" ]; then

    echo
    echo "zsh-syntax-highlighting 已存在，跳过安装。"

else

    echo
    echo "安装 zsh-syntax-highlighting..."

    rm -rf "$SYNTAX_DIR"

    git clone \
        --depth=1 \
        "$SYNTAX_URL" \
        "$SYNTAX_DIR"

fi

# ------------------------------------------------------------
# 8. 修改 .zshrc
# ------------------------------------------------------------

ZSHRC="$TARGET_HOME/.zshrc"

touch "$ZSHRC"

AUTO_SOURCE='source ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh'

SYNTAX_SOURCE='source ~/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh'

if ! grep -qF "$AUTO_SOURCE" "$ZSHRC"; then
    echo "$AUTO_SOURCE" >> "$ZSHRC"
fi

if ! grep -qF "$SYNTAX_SOURCE" "$ZSHRC"; then
    echo "$SYNTAX_SOURCE" >> "$ZSHRC"
fi

# ------------------------------------------------------------
# 完成
# ------------------------------------------------------------

echo
echo "============================================"
echo " 安装完成"
echo "============================================"
echo
echo "出口国家：${COUNTRY:-未知}"

if [ "$USE_CN" = true ]; then
    echo "下载线路：CN 加速源"
else
    echo "下载线路：GitHub 国际源"
fi

echo
echo "Zsh："
zsh --version

echo
echo "默认 Shell："
getent passwd "$TARGET_USER" | cut -d: -f7

echo
echo "已安装插件："
echo "  - zsh-autosuggestions"
echo "  - zsh-syntax-highlighting"

echo
echo "请重新登录 SSH，使默认 Zsh Shell 完全生效。"
echo
echo "或者当前终端立即执行："
echo
echo "exec zsh"
echo
