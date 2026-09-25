#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Universal XanMod Installer
#
# 用法：
#   sudo bash xanmod_install.sh
#
# 可选：
#   sudo XANMOD_FLAVOR=main bash xanmod_install.sh
#   sudo XANMOD_FLAVOR=lts  bash xanmod_install.sh
#   sudo XANMOD_FLAVOR=edge bash xanmod_install.sh
#   sudo XANMOD_FLAVOR=rt   bash xanmod_install.sh
#
# 默认：
#   XANMOD_FLAVOR=auto
#   优先 MAIN，不可用时自动尝试 LTS
#
# 自动重启：
#   sudo AUTO_REBOOT=1 bash xanmod_install.sh
# ============================================================

XANMOD_FLAVOR="${XANMOD_FLAVOR:-auto}"
AUTO_REBOOT="${AUTO_REBOOT:-0}"
# XanMod's CDN may challenge wget's default User-Agent while allowing APT requests.
XANMOD_HTTP_USER_AGENT="Debian APT-HTTP/1.3"

log() {
    printf '\n[xanmod] %s\n' "$*"
}

warn() {
    printf '\n[xanmod] WARNING: %s\n' "$*" >&2
}

fail() {
    printf '\n[xanmod] ERROR: %s\n' "$*" >&2
    exit 1
}

# ------------------------------------------------------------
# 基本检查
# ------------------------------------------------------------

[[ ${EUID:-$(id -u)} -eq 0 ]] || \
    fail "请使用 root 权限运行，例如：sudo bash $0"

command -v apt-get >/dev/null 2>&1 || \
    fail "未发现 apt-get，本脚本仅适用于 Debian/Ubuntu 系统"

command -v dpkg >/dev/null 2>&1 || \
    fail "未发现 dpkg"

[[ -r /etc/os-release ]] || \
    fail "找不到 /etc/os-release"

ARCH="$(dpkg --print-architecture 2>/dev/null || true)"

[[ "$ARCH" == "amd64" ]] || \
    fail "XanMod 官方 APT 仓库仅适用于 amd64，当前架构：${ARCH:-unknown}"

# ------------------------------------------------------------
# 检测容器
# LXC/OpenVZ/Docker 无法自行更换宿主机内核
# KVM/VMware/Hyper-V VPS 不受影响
# ------------------------------------------------------------

if command -v systemd-detect-virt >/dev/null 2>&1; then
    CONTAINER_TYPE="$(systemd-detect-virt --container 2>/dev/null || true)"

    if [[ -n "$CONTAINER_TYPE" && "$CONTAINER_TYPE" != "none" ]]; then
        fail "检测到系统容器：${CONTAINER_TYPE}。此类容器不能启动自定义 XanMod 内核"
    fi
fi

case "$XANMOD_FLAVOR" in
    auto|main|lts|edge|rt)
        ;;
    *)
        fail "XANMOD_FLAVOR=$XANMOD_FLAVOR 无效，可用：auto/main/lts/edge/rt"
        ;;
esac

export DEBIAN_FRONTEND=noninteractive

SOURCE_LIST=/etc/apt/sources.list
SOURCE_DIR=/etc/apt/sources.list.d
KEYRING_DIR=/etc/apt/keyrings

KEYRING="${KEYRING_DIR}/xanmod-archive-keyring.gpg"
LIST_FILE="${SOURCE_DIR}/xanmod-release.list"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/root/xanmod-install-backup-${STAMP}"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

install -d -m 0755 "$SOURCE_DIR" "$KEYRING_DIR"
install -d -m 0700 "$BACKUP_DIR"

backup_file() {
    local file="$1"
    local rel
    local dest

    [[ -f "$file" ]] || return 0

    rel="${file#/etc/apt/}"
    dest="${BACKUP_DIR}/${rel}"

    install -d -m 0700 "$(dirname "$dest")"

    cp -a -- "$file" "$dest"
}

# ------------------------------------------------------------
# 清理旧 XanMod 软件源
# ------------------------------------------------------------

log "清理旧 XanMod APT 配置"
log "备份目录：$BACKUP_DIR"

# 处理传统 .list
while IFS= read -r -d '' file; do

    if grep -qiE \
        '(deb\.xanmod\.org|dl\.xanmod\.org)' \
        "$file" 2>/dev/null; then

        backup_file "$file"

        sed -i -E \
            '/^[[:space:]]*deb(-src)?[[:space:]].*(deb\.xanmod\.org|dl\.xanmod\.org)/s|^|# disabled-by-xanmod-installer: |' \
            "$file"
    fi

done < <(
    {
        [[ -f "$SOURCE_LIST" ]] && printf '%s\0' "$SOURCE_LIST"

        find "$SOURCE_DIR" \
            -maxdepth 1 \
            -type f \
            -name '*.list' \
            -print0 2>/dev/null
    }
)

# 处理 Debian 新版 Deb822 .sources
while IFS= read -r -d '' file; do

    if grep -qiE \
        '(deb\.xanmod\.org|dl\.xanmod\.org)' \
        "$file" 2>/dev/null; then

        backup_file "$file"

        tmp_sources="$(mktemp)"

        awk '
            BEGIN {
                RS=""
                ORS="\n\n"
            }

            tolower($0) !~ /(deb\.xanmod\.org|dl\.xanmod\.org)/ {
                print
            }
        ' "$file" > "$tmp_sources"

        if [[ -s "$tmp_sources" ]]; then
            install -m 0644 "$tmp_sources" "$file"
        else
            rm -f -- "$file"
        fi

        rm -f -- "$tmp_sources"
    fi

done < <(
    find "$SOURCE_DIR" \
        -maxdepth 1 \
        -type f \
        -name '*.sources' \
        -print0 2>/dev/null
)

# 清除 sources.list.d 中错误的 XanMod 备份文件
while IFS= read -r -d '' file; do

    base="$(basename "$file")"

    case "$base" in
        *.list|*.sources)
            continue
            ;;
    esac

    if [[ "$base" == *xanmod* ]] ||
       grep -qiE \
        '(deb\.xanmod\.org|dl\.xanmod\.org)' \
        "$file" 2>/dev/null; then

        backup_file "$file"
        rm -f -- "$file"
    fi

done < <(
    find "$SOURCE_DIR" \
        -maxdepth 1 \
        -type f \
        -print0 2>/dev/null
)

rm -f -- "$LIST_FILE"

# 清理旧索引
find /var/lib/apt/lists \
    -maxdepth 1 \
    -type f \
    \( -iname '*xanmod*' -o -iname '*deb.xanmod.org*' \) \
    -delete 2>/dev/null || true

find /var/lib/apt/lists/partial \
    -maxdepth 1 \
    -type f \
    \( -iname '*xanmod*' -o -iname '*deb.xanmod.org*' \) \
    -delete 2>/dev/null || true

# ------------------------------------------------------------
# 安装依赖
# ------------------------------------------------------------

log "更新系统 APT 索引"

apt-get update \
    --allow-releaseinfo-change

log "安装依赖"

apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    wget \
    gnupg

# ------------------------------------------------------------
# 检测发行版 codename
# ------------------------------------------------------------

# shellcheck disable=SC1091
. /etc/os-release

declare -a CODENAME_CANDIDATES=()

add_codename() {
    local c="${1:-}"
    local existing

    [[ -n "$c" ]] || return 0

    for existing in "${CODENAME_CANDIDATES[@]:-}"; do
        [[ "$existing" == "$c" ]] && return 0
    done

    CODENAME_CANDIDATES+=("$c")
}

add_codename "${VERSION_CODENAME:-}"
add_codename "${UBUNTU_CODENAME:-}"

if command -v lsb_release >/dev/null 2>&1; then
    add_codename "$(lsb_release -sc 2>/dev/null || true)"
fi

[[ ${#CODENAME_CANDIDATES[@]} -gt 0 ]] || \
    fail "无法识别发行版 codename"

CODENAME=""

for candidate in "${CODENAME_CANDIDATES[@]}"; do

    log "检查 XanMod 仓库是否支持：$candidate"

    if wget -nv -S \
        --user-agent="$XANMOD_HTTP_USER_AGENT" \
        --output-document="$TMPDIR/Release" \
        "https://deb.xanmod.org/dists/${candidate}/Release" \
        2>"$TMPDIR/release-wget.log"; then

        grep -Fxq "Codename: $candidate" "$TMPDIR/Release" || \
            fail "XanMod 仓库返回的 Release 元数据与 ${candidate} 不匹配"

        CODENAME="$candidate"
        break
    fi

    REPO_HTTP_STATUS="$(
        awk '/^[[:space:]]*HTTP\/[0-9.]+[[:space:]]+[0-9]+/ { code=$2 } END { print code }' \
            "$TMPDIR/release-wget.log"
    )"

    if [[ "$REPO_HTTP_STATUS" != "404" ]]; then
        fail "无法访问 XanMod 仓库（${candidate}，HTTP ${REPO_HTTP_STATUS:-unknown}）；请检查网络或仓库访问限制"
    fi
done

[[ -n "$CODENAME" ]] || \
    fail "XanMod 当前不支持检测到的发行版：${CODENAME_CANDIDATES[*]}"

log "使用 XanMod suite：$CODENAME"

# ------------------------------------------------------------
# 安装 XanMod 官方密钥
# ------------------------------------------------------------

log "下载 XanMod 官方 archive key"

wget -nv \
    --user-agent="$XANMOD_HTTP_USER_AGENT" \
    --output-document="$TMPDIR/archive.key" \
    https://dl.xanmod.org/archive.key || \
    fail "无法下载 XanMod 官方 archive key；请检查网络或仓库访问限制"

[[ -s "$TMPDIR/archive.key" ]] || \
    fail "下载的 XanMod archive key 为空"

gpg \
    --batch \
    --yes \
    --dearmor \
    --output "$TMPDIR/xanmod-archive-keyring.gpg" \
    "$TMPDIR/archive.key"

install \
    -m 0644 \
    "$TMPDIR/xanmod-archive-keyring.gpg" \
    "$KEYRING"

# ------------------------------------------------------------
# 添加 XanMod 仓库
# ------------------------------------------------------------

log "写入 XanMod 官方仓库"

printf \
    'deb [arch=amd64 signed-by=%s] https://deb.xanmod.org %s main\n' \
    "$KEYRING" \
    "$CODENAME" \
    > "$LIST_FILE"

chmod 0644 "$LIST_FILE"

apt-get update \
    --allow-releaseinfo-change

# ------------------------------------------------------------
# 自动检测 x86-64 psABI
#
# v1 = 老 x86-64
# v2 = Nehalem/Sandy Bridge 等
# v3 = Haswell / Zen / 更新 CPU
#
# v4 不单独选择：
# XanMod 官方当前说明 AVX-512 v4 对内核没有实际收益
# ------------------------------------------------------------

CPU_FLAGS="$(
    awk -F: \
        '/^flags[[:space:]]*:/ {
            print $2
            exit
        }' \
        /proc/cpuinfo 2>/dev/null || true
)"

[[ -n "$CPU_FLAGS" ]] || \
    fail "无法读取 /proc/cpuinfo CPU flags"

has_all_flags() {
    local f

    for f in "$@"; do
        grep -qw "$f" <<<"$CPU_FLAGS" || return 1
    done
}

CPU_LEVEL=1

# x86-64-v2
if has_all_flags \
    cx16 \
    lahf_lm \
    popcnt \
    sse4_1 \
    sse4_2 \
    ssse3; then

    CPU_LEVEL=2
fi

# x86-64-v3
if [[ "$CPU_LEVEL" -eq 2 ]] &&
   has_all_flags \
    avx \
    avx2 \
    bmi1 \
    bmi2 \
    f16c \
    fma \
    abm \
    movbe \
    xsave; then

    CPU_LEVEL=3
fi

log "CPU 支持等级：x64v${CPU_LEVEL}"

# ------------------------------------------------------------
# 选择 XanMod 包
# ------------------------------------------------------------

declare -a PACKAGES=()

case "$XANMOD_FLAVOR" in

    auto)

        # 默认优先 MAIN
        if [[ "$CPU_LEVEL" -ge 2 ]]; then
            PACKAGES+=(
                "linux-xanmod-x64v${CPU_LEVEL}"
            )
        fi

        # MAIN 不可用时 fallback LTS
        PACKAGES+=(
            "linux-xanmod-lts-x64v${CPU_LEVEL}"
        )
        ;;

    main)

        PACKAGES+=(
            "linux-xanmod-x64v${CPU_LEVEL}"
        )
        ;;

    lts)

        PACKAGES+=(
            "linux-xanmod-lts-x64v${CPU_LEVEL}"
        )
        ;;

    edge)

        PACKAGES+=(
            "linux-xanmod-edge-x64v${CPU_LEVEL}"
        )
        ;;

    rt)

        PACKAGES+=(
            "linux-xanmod-rt-x64v${CPU_LEVEL}"
        )
        ;;
esac

SELECTED_PACKAGE=""

for pkg in "${PACKAGES[@]}"; do

    candidate_version="$(
        apt-cache policy "$pkg" 2>/dev/null |
        awk '/Candidate:/ {
            print $2
            exit
        }'
    )"

    if [[ -n "$candidate_version" &&
          "$candidate_version" != "(none)" ]]; then

        SELECTED_PACKAGE="$pkg"
        break
    fi
done

[[ -n "$SELECTED_PACKAGE" ]] || \
    fail "找不到合适的 XanMod 内核。尝试过：${PACKAGES[*]}"

# ------------------------------------------------------------
# 安装
# ------------------------------------------------------------

log "准备安装：$SELECTED_PACKAGE"

apt-get install -y \
    "$SELECTED_PACKAGE"

# ------------------------------------------------------------
# GRUB
# ------------------------------------------------------------

if command -v update-grub >/dev/null 2>&1; then

    log "更新 GRUB"

    update-grub
fi

# ------------------------------------------------------------
# Secure Boot 提醒
# ------------------------------------------------------------

if command -v mokutil >/dev/null 2>&1; then

    if mokutil --sb-state 2>/dev/null |
       grep -qi 'SecureBoot enabled'; then

        warn "检测到 Secure Boot 已开启，请确认服务器允许启动 XanMod 内核"
    fi
fi

# ------------------------------------------------------------
# 完成
# ------------------------------------------------------------

log "XanMod 安装完成"

echo
echo "系统：         ${PRETTY_NAME:-unknown}"
echo "发行版：       ${CODENAME}"
echo "架构：         ${ARCH}"
echo "CPU 等级：     x64v${CPU_LEVEL}"
echo "安装包：       ${SELECTED_PACKAGE}"
echo "当前内核：     $(uname -r)"
echo "APT 备份：     ${BACKUP_DIR}"

echo
echo "已安装的 XanMod kernel："

find /boot \
    -maxdepth 1 \
    -type f \
    -name 'vmlinuz-*xanmod*' \
    -printf '  %f\n' 2>/dev/null || true

echo
echo "注意：当前运行内核不会立即改变。"
echo "重启后检查："
echo
echo "    uname -r"
echo

if [[ "$AUTO_REBOOT" == "1" ]]; then

    log "AUTO_REBOOT=1，准备重启"

    reboot

else

    echo "确认无误后执行："
    echo
    echo "    sudo reboot"
    echo
fi
