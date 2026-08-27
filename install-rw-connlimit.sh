#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
 echo "Please run as root: sudo bash $0" >&2
 exit 1
fi

export DEBIAN_FRONTEND=noninteractive

LIMIT_DEFAULT=800
SYNC_INTERVAL_DEFAULT=15
PROCESS_NAME_DEFAULT=rw-core

log() {
 printf '[rw-connlimit] %s\n' "$*"
}

log "Installing required packages..."
if ! apt-get update; then
 echo "APT update failed. Fix invalid repositories, then rerun this installer." >&2
 exit 1
fi
apt-get install -y nftables iproute2 procps util-linux

install -d -m 0755 /etc/rw-connlimit /var/lib/rw-connlimit /run/lock

if [[ ! -f /etc/rw-connlimit/config ]]; then
 cat > /etc/rw-connlimit/config <<EOF
# Maximum concurrent TCP connections for each source IP on each rw-core port.
LIMIT=${LIMIT_DEFAULT}

# Process name displayed by ss -p for Remnawave Core.
PROCESS_NAME=${PROCESS_NAME_DEFAULT}

# systemd timer interval in seconds. Change the timer separately after install.
SYNC_INTERVAL=${SYNC_INTERVAL_DEFAULT}
EOF
fi

if [[ ! -f /etc/rw-connlimit/include-ports ]]; then
 cat > /etc/rw-connlimit/include-ports <<'EOF'
# Force-add TCP ports, one per line or separated by spaces/commas.
# Example:
# 443
EOF
fi

if [[ ! -f /etc/rw-connlimit/exclude-ports ]]; then
 cat > /etc/rw-connlimit/exclude-ports <<'EOF'
# Force-exclude TCP ports.
# Remnawave Node API port in this deployment:
2222
EOF
fi

cat > /usr/local/sbin/rw-connlimit-sync <<'SYNC_SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG=/etc/rw-connlimit/config
INCLUDE_FILE=/etc/rw-connlimit/include-ports
EXCLUDE_FILE=/etc/rw-connlimit/exclude-ports
STATE_DIR=/var/lib/rw-connlimit
STATE_FILE=$STATE_DIR/state
TABLE_FAMILY=inet
TABLE_NAME=rw_connlimit

usage() {
 cat <<'EOF'
Usage: rw-connlimit-sync [--force|--print|--clear]
  --force  Rebuild the nftables table even if configuration is unchanged.
  --print  Print detected/effective ports without changing nftables.
  --clear  Delete the rw_connlimit nftables table and saved state.
EOF
}

MODE=${1:-sync}
case "$MODE" in
 sync|--force|--print|--clear) ;;
 *) usage >&2; exit 2 ;;
esac

if [[ ! -r "$CONFIG" ]]; then
 echo "Missing config: $CONFIG" >&2
 exit 1
fi

# shellcheck disable=SC1090
. "$CONFIG"

LIMIT=${LIMIT:-500}
PROCESS_NAME=${PROCESS_NAME:-rw-core}

if [[ ! "$LIMIT" =~ ^[1-9][0-9]*$ ]] || (( LIMIT > 1000000 )); then
 echo "Invalid LIMIT: $LIMIT" >&2
 exit 1
fi

if [[ ! "$PROCESS_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
 echo "Invalid PROCESS_NAME: $PROCESS_NAME" >&2
 exit 1
fi

NFT=$(command -v nft)
SS=$(command -v ss)

install -d -m 0755 "$STATE_DIR" /run/lock
exec 9>/run/lock/rw-connlimit.lock
flock -x 9

parse_port_file() {
 local file=$1
 [[ -r "$file" ]] || return 0
 awk '
  {
   sub(/#.*/, "")
   gsub(/,/, " ")
   for (i = 1; i <= NF; i++) {
    if ($i ~ /^[0-9]+$/ && $i >= 1 && $i <= 65535)
     print $i
   }
  }
 ' "$file"
}

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

AUTO=$TMPDIR/auto
INCLUDED=$TMPDIR/included
EXCLUDED=$TMPDIR/excluded
ALL=$TMPDIR/all
DESIRED=$TMPDIR/desired
RULESET=$TMPDIR/rules.nft
NEW_STATE=$TMPDIR/state

: > "$AUTO"

# Detect non-loopback TCP listeners owned by the exact rw-core process name.
"$SS" -H -lntp 2>/dev/null |
awk -v proc="$PROCESS_NAME" '
 index($0, "\"" proc "\"") {
  local_addr=$4

  if (local_addr ~ /^127\./ ||
      local_addr ~ /^\[::1\]:/ ||
      local_addr ~ /^::1:/)
   next

  port=local_addr
  sub(/^.*:/, "", port)

  if (port ~ /^[0-9]+$/ && port >= 1 && port <= 65535)
   print port
 }
' | sort -nu > "$AUTO"

parse_port_file "$INCLUDE_FILE" | sort -nu > "$INCLUDED"
parse_port_file "$EXCLUDE_FILE" | sort -nu > "$EXCLUDED"

{
 cat "$AUTO"
 cat "$INCLUDED"
} | sort -nu > "$ALL"

awk '
 NR == FNR {
  excluded[$1]=1
  next
 }
 !excluded[$1]
' "$EXCLUDED" "$ALL" > "$DESIRED"

if [[ "$MODE" == "--print" ]]; then
 cat "$DESIRED"
 exit 0
fi

if [[ "$MODE" == "--clear" ]]; then
 if "$NFT" list table "$TABLE_FAMILY" "$TABLE_NAME" >/dev/null 2>&1; then
  "$NFT" delete table "$TABLE_FAMILY" "$TABLE_NAME"
 fi
 rm -f "$STATE_FILE"
 logger -t rw-connlimit "table cleared"
 exit 0
fi

# During a core restart there may briefly be no listener. Preserve current rules.
if [[ ! -s "$DESIRED" ]]; then
 logger -t rw-connlimit "no public TCP listeners found for process $PROCESS_NAME; existing rules preserved"
 exit 0
fi

{
 printf 'LIMIT=%s\n' "$LIMIT"
 printf 'PROCESS_NAME=%s\n' "$PROCESS_NAME"
 cat "$DESIRED"
} > "$NEW_STATE"

TABLE_EXISTS=0
if "$NFT" list table "$TABLE_FAMILY" "$TABLE_NAME" >/dev/null 2>&1; then
 TABLE_EXISTS=1
fi

if [[ "$MODE" != "--force" && $TABLE_EXISTS -eq 1 && -r "$STATE_FILE" ]] && cmp -s "$NEW_STATE" "$STATE_FILE"; then
 exit 0
fi

: > "$RULESET"
if (( TABLE_EXISTS == 1 )); then
 printf 'delete table %s %s\n' "$TABLE_FAMILY" "$TABLE_NAME" >> "$RULESET"
fi

cat >> "$RULESET" <<EOF
table ${TABLE_FAMILY} ${TABLE_NAME} {
EOF

while read -r port; do
 [[ -n "$port" ]] || continue
 cat >> "$RULESET" <<EOF
 set v4_${port} {
  type ipv4_addr
  flags dynamic
  size 65535
 }

 set v6_${port} {
  type ipv6_addr
  flags dynamic
  size 65535
 }
EOF
done < "$DESIRED"

cat >> "$RULESET" <<'EOF'

 chain input {
  type filter hook input priority -20
  policy accept
EOF

while read -r port; do
 [[ -n "$port" ]] || continue
 printf '  meta nfproto ipv4 tcp dport %s ct state new add @v4_%s { ip saddr ct count over %s } counter reject with tcp reset\n' "$port" "$port" "$LIMIT" >> "$RULESET"
 printf '  meta nfproto ipv6 tcp dport %s ct state new add @v6_%s { ip6 saddr ct count over %s } counter reject with tcp reset\n' "$port" "$port" "$LIMIT" >> "$RULESET"
done < "$DESIRED"

cat >> "$RULESET" <<'EOF'
 }
}
EOF

# Syntax/kernel feature check first, then apply the same transaction atomically.
"$NFT" -c -f "$RULESET"
"$NFT" -f "$RULESET"
install -m 0644 "$NEW_STATE" "$STATE_FILE"

logger -t rw-connlimit "limit=$LIMIT ports=$(paste -sd, "$DESIRED")"
SYNC_SCRIPT

chmod 0755 /usr/local/sbin/rw-connlimit-sync

cat > /etc/systemd/system/rw-connlimit.service <<'EOF'
[Unit]
Description=Per-IP per-port TCP connection limit for Remnawave rw-core
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/rw-connlimit-sync
ExecReload=/usr/local/sbin/rw-connlimit-sync --force
ExecStop=/usr/local/sbin/rw-connlimit-sync --clear
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/rw-connlimit-sync.service <<'EOF'
[Unit]
Description=Synchronize Remnawave rw-core TCP ports into nftables
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/rw-connlimit-sync
EOF

SYNC_INTERVAL=$(sed -n 's/^SYNC_INTERVAL=//p' /etc/rw-connlimit/config | tail -n 1)
SYNC_INTERVAL=${SYNC_INTERVAL:-15}
if [[ ! "$SYNC_INTERVAL" =~ ^[1-9][0-9]*$ ]]; then
 SYNC_INTERVAL=$SYNC_INTERVAL_DEFAULT
fi

cat > /etc/systemd/system/rw-connlimit-sync.timer <<EOF
[Unit]
Description=Periodically synchronize Remnawave rw-core TCP ports

[Timer]
OnBootSec=15s
OnUnitActiveSec=${SYNC_INTERVAL}s
AccuracySec=1s
Unit=rw-connlimit-sync.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable rw-connlimit.service rw-connlimit-sync.timer

# Build immediately if rw-core is already listening. Empty detection is non-fatal.
/usr/local/sbin/rw-connlimit-sync --force
systemctl restart rw-connlimit.service
systemctl enable --now rw-connlimit-sync.timer
systemctl start rw-connlimit-sync.service

log "Installation completed."
echo
echo "Effective rw-core TCP ports:"
/usr/local/sbin/rw-connlimit-sync --print || true

echo
echo "Current nftables table:"
if nft list table inet rw_connlimit >/dev/null 2>&1; then
 nft list table inet rw_connlimit
else
 echo "No table yet. rw-core may not be listening; the timer will retry every ${SYNC_INTERVAL}s."
fi

echo
echo "Useful commands:"
echo "  /usr/local/sbin/rw-connlimit-sync --print"
echo "  nft -a list table inet rw_connlimit"
echo "  systemctl status rw-connlimit.service rw-connlimit-sync.timer --no-pager"
echo "  journalctl -u rw-connlimit-sync.service -n 50 --no-pager"
