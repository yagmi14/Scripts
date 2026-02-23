#!/bin/bash
set -euo pipefail

CONF_DIR="/usr/local/etc/sb3/conf"
LOG_JSON="$CONF_DIR/00_log.json"

# 必须 root；非 root 时尽量用 sudo 自动提权（Alpine 可能没有 sudo）
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  echo "请用 root 运行（例如：sudo bash $0）"
  exit 1
fi

detect_os() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    [[ "${ID:-}" == "alpine" ]] && { echo alpine; return; }
    [[ " ${ID_LIKE:-} " == *" debian "* ]] && { echo debian; return; }
    case "${ID:-}" in debian|ubuntu|kali|raspbian|linuxmint|pop) echo debian; return;; esac
  fi
  [[ -f /etc/alpine-release ]] && { echo alpine; return; }
  [[ -f /etc/debian_version ]] && { echo debian; return; }
  echo unknown
}

OS="$(detect_os)"
[[ "$OS" == "unknown" ]] && { echo "不支持/未识别的系统"; exit 1; }

# 统一用你指定的安装命令（Debian / Alpine 都走这条）
bash <(curl -fsSL https://sing-box.app/deb-install.sh)

mkdir -p "$CONF_DIR"
echo '{"log":{"disabled":false,"level":"info","timestamp":true}}' > "$LOG_JSON"

SB_BIN="$(command -v sing-box || true)"
[[ -z "$SB_BIN" ]] && SB_BIN="/usr/bin/sing-box"
[[ ! -x "$SB_BIN" ]] && { echo "未找到 sing-box 可执行文件：$SB_BIN"; exit 1; }

if [[ "$OS" == "debian" ]]; then
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
  systemctl enable --now sb3

elif [[ "$OS" == "alpine" ]]; then
  cat > /etc/init.d/sb3 <<EOF
#!/sbin/openrc-run
description="sing-box service (sb3)"

command="$SB_BIN"
command_args="run -C $CONF_DIR/"

supervisor=supervise-daemon
respawn_delay=10

depend() {
  need net
  after firewall
}
EOF

  chmod +x /etc/init.d/sb3
  rc-update add sb3 default
  rc-service sb3 start
fi
