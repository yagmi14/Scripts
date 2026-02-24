#!/bin/sh
set -eu

CONF_DIR="/usr/local/etc/sb3/conf"
LOG_JSON="$CONF_DIR/00_log.json"
OUTBOUNDS_DIRECT_JSON="$CONF_DIR/outbounds_direct.json"

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 运行（Alpine 通常没有 sudo）：sudo sh $0"
    exit 1
  fi
}

detect_os() {
  OS_FAMILY="unknown"

  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}" in
      alpine) OS_FAMILY="alpine" ;;
      debian|ubuntu|linuxmint|pop|kali|raspbian) OS_FAMILY="debian" ;;
      *)
        case " ${ID_LIKE:-} " in
          *" debian "*) OS_FAMILY="debian" ;;
        esac
      ;;
    esac
  fi

  # 兜底：有些精简系统没 os-release
  if [ "$OS_FAMILY" = "unknown" ]; then
    [ -f /etc/alpine-release ] && OS_FAMILY="alpine"
    [ -f /etc/debian_version ] && OS_FAMILY="debian"
  fi

  echo "$OS_FAMILY"
}

install_sing_box_debian() {
  # 按你原脚本的安装方式（用 pipe 避免 bash 的 <() 语法在 /bin/sh 下不可用）
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://sing-box.app/deb-install.sh | bash
  else
    echo "缺少 curl，无法执行 deb-install.sh"
    exit 1
  fi
}

install_sing_box_alpine() {
  if ! command -v apk >/dev/null 2>&1; then
    echo "未找到 apk，当前看起来不像 Alpine"
    exit 1
  fi

  # sing-box 在 Alpine 通常来自 edge/community；这里按需补源（避免重复写入）
  EDGE_COMMUNITY_URL="https://dl-cdn.alpinelinux.org/alpine/edge/community"
  if ! grep -q "edge/community" /etc/apk/repositories 2>/dev/null; then
    echo "$EDGE_COMMUNITY_URL" >> /etc/apk/repositories
  fi

  apk update
  apk add --no-cache sing-box
}

ensure_conf() {
  mkdir -p "$CONF_DIR"
  printf '%s\n' '{"log":{"disabled":false,"level":"info","timestamp":true}}' > "$LOG_JSON"
}

write_outbounds_direct() {
  mkdir -p "$CONF_DIR"
  printf '%s\n' '{"outbounds": [{"type": "direct", "tag": "direct-out"}]}' > "$OUTBOUNDS_DIRECT_JSON"
}

restart_sb3() {
  if command -v systemctl >/dev/null 2>&1; then
    systemctl restart sb3 >/dev/null 2>&1 || systemctl start sb3
  elif command -v rc-service >/dev/null 2>&1; then
    rc-service sb3 restart >/dev/null 2>&1 || rc-service sb3 start
  else
    echo "无法重启 sb3：未找到 systemctl 或 rc-service"
  fi
}

write_systemd_service() {
  SB_BIN="$(command -v sing-box || true)"
  if [ -z "$SB_BIN" ]; then
    echo "未找到 sing-box 可执行文件（Debian 安装后应在 PATH 中）"
    exit 1
  fi

  if ! command -v systemctl >/dev/null 2>&1; then
    echo "当前系统缺少 systemctl / systemd，无法生成 systemd service"
    exit 1
  fi

  cat > /etc/systemd/system/sb3.service <<EOF
[Unit]
Description=sing-box service (sb3)
Documentation=https://sing-box.sagernet.org
After=network.target nss-lookup.target

[Service]
User=root
Type=simple
NoNewPrivileges=yes
TimeoutStartSec=0
ExecStart=$SB_BIN run -C $CONF_DIR/
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable sb3
}

write_openrc_service() {
  SB_BIN="$(command -v sing-box || true)"
  if [ -z "$SB_BIN" ]; then
    echo "未找到 sing-box 可执行文件（Alpine apk 安装后应在 PATH 中）"
    exit 1
  fi

  if [ ! -x /sbin/openrc-run ]; then
    echo "未找到 /sbin/openrc-run，当前系统可能不是 OpenRC（或环境不完整）"
    exit 1
  fi

  cat > /etc/init.d/sb3 <<EOF
#!/sbin/openrc-run
description="sing-box service (sb3)"

command="$SB_BIN"
command_args="run -C $CONF_DIR/"

# 使用 OpenRC 内置 supervise-daemon 做守护 + 异常退出自动重启
supervisor=supervise-daemon
respawn_delay=10

depend() {
  need net
  after firewall
}
EOF

  chmod +x /etc/init.d/sb3
  rc-update add sb3 default
}

main() {
  require_root

  OS="$(detect_os)"
  case "$OS" in
    debian)
      install_sing_box_debian
      ensure_conf
      write_outbounds_direct
      write_systemd_service
      restart_sb3
      echo "Debian 系：已写入 systemd 服务 /etc/systemd/system/sb3.service，并设置开机自启（enable），并已重启/启动 sb3。"
      ;;
    alpine)
      install_sing_box_alpine
      ensure_conf
      write_outbounds_direct
      write_openrc_service
      restart_sb3
      echo "Alpine：已写入 OpenRC 服务 /etc/init.d/sb3，并设置开机自启（rc-update add default），并已重启/启动 sb3。"
      ;;
    *)
      echo "不支持的系统：未识别为 Debian 系或 Alpine"
      exit 1
      ;;
  esac
}

main "$@"
