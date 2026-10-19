#!/usr/bin/env bash
# Debian 12/13 APT mirror switcher. No packages are installed or upgraded.
set -Eeuo pipefail
export LC_ALL=C
umask 077

APT_DIR=/etc/apt
BACKUP_ROOT=/var/backups/debian-sources
KEYRING=/usr/share/keyrings/debian-archive-keyring.gpg
LOCK=/run/lock/debian-sources.lock
WORK=''
BACKUP=''
ROLLBACK=0
MODE=switch
PREVIEW=0
MIRROR=''
RESTORE=''
declare -a CHANGED=()

log() { printf '[debian-sources] %s\n' "$*"; }
die() { log "错误：$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
用法：sudo bash debian-sources.sh [official|china|aws] [--dry-run]
      sudo bash debian-sources.sh --restore 备份目录

不带参数：检测 Debian 版本后显示选择菜单。
  official   Debian 官方 CDN
  china      中国大陆：中科大 USTC 镜像
  aws        Debian AWS CDN（含安全仓库）
  --dry-run  只预览将修改的文件和新软件源，无需 root
  --restore  恢复本脚本生成的指定备份，并更新软件包索引

支持 Debian 12 (bookworm) / 13 (trixie)，保留第三方源。
切换前备份；apt-get update 失败或收到退出信号时自动恢复源文件。
EOF
}

while (( $# )); do
    case "$1" in
        official|china|aws)
            [[ -z "$MIRROR" ]] || die '只能选择一个镜像'
            MIRROR=$1 ;;
        --dry-run) PREVIEW=1 ;;
        --restore)
            (( $# >= 2 )) || die '--restore 缺少备份目录'
            [[ -z "$RESTORE" ]] || die '重复的 --restore'
            MODE=restore; RESTORE=$2; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "未知参数：$1（使用 --help 查看用法）" ;;
    esac
    shift
done
[[ "$MODE" != restore || ( -z "$MIRROR" && "$PREVIEW" == 0 ) ]] ||
    die '--restore 不能与镜像参数或 --dry-run 同时使用'

[[ -r /etc/os-release ]] || die '找不到 /etc/os-release'
# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
    debian:12) CODENAME=bookworm ;;
    debian:13) CODENAME=trixie ;;
    *) die "仅支持 Debian 12/13，当前系统：${PRETTY_NAME:-unknown}" ;;
esac
[[ -z "${VERSION_CODENAME:-}" || "$VERSION_CODENAME" == "$CODENAME" ]] ||
    die '系统版本号与代号不一致，请先检查 /etc/os-release'
log "检测到 ${PRETTY_NAME:-Debian $VERSION_ID}，代号：$CODENAME"

if [[ "$MODE" == switch && -z "$MIRROR" ]]; then
    [[ -t 0 ]] || die '非交互运行请指定 official、china 或 aws'
    printf '\n  1) 官方源\n  2) 中国大陆源（中科大 USTC）\n  3) AWS CDN 源\n'
    read -r -p '请选择 [1-3]：' choice
    case "$choice" in
        1) MIRROR=official ;; 2) MIRROR=china ;; 3) MIRROR=aws ;;
        *) die '无效选择，未修改系统' ;;
    esac
fi
if (( ! PREVIEW )); then
    (( EUID == 0 )) || die '请使用 root 或 sudo 运行'
fi
for tool in awk cmp cp diff flock install mktemp mv realpath stat apt-get; do
    command -v "$tool" >/dev/null 2>&1 || die "缺少工具：$tool"
done
[[ -r "$KEYRING" ]] || die "缺少 Debian 官方签名密钥：$KEYRING"

# Never replace a linked source file or write through a linked directory.
check_file() {
    local file=$1
    [[ ! -L "$file" ]] || die "拒绝修改符号链接：$file"
    if [[ -e "$file" ]]; then
        [[ -f "$file" && $(stat -c %h -- "$file") == 1 ]] ||
            die "源文件必须是普通文件且没有硬链接：$file"
    fi
}
check_apt_dirs() {
    [[ -d "$APT_DIR" && $(realpath -e -- "$APT_DIR") == "$APT_DIR" ]] ||
        die "APT 目录不存在或含符号链接：$APT_DIR"
    [[ ! -e "$APT_DIR/sources.list.d" || -d "$APT_DIR/sources.list.d" ]] ||
        die 'sources.list.d 不是目录'
    [[ ! -L "$APT_DIR/sources.list.d" ]] || die 'sources.list.d 不能是符号链接'
}
check_apt_dirs
WORK=$(mktemp -d)

# Restore only manifest-listed files. New/unrelated files are never removed.
restore_files() {
    local directory=$1 state relative target temp
    while read -r state relative; do
        target="$APT_DIR/$relative"
        check_file "$target"
        if [[ "$state" == present ]]; then
            temp=$(mktemp "$APT_DIR/.debian-sources.XXXXXX")
            if ! cp -p -- "$directory/files/$relative" "$temp" || ! mv -f -- "$temp" "$target"; then
                rm -f -- "$temp"
                return 1
            fi
            cmp -s -- "$directory/files/$relative" "$target" || return 1
        else
            rm -f -- "$target" || return 1
        fi
    done < "$directory/manifest"
}
cleanup() {
    local rc=$?
    trap - EXIT HUP INT TERM
    if (( ROLLBACK )); then
        log "操作未完成，正在恢复：$BACKUP" >&2
        if ( restore_files "$BACKUP" ); then
            log '原软件源已恢复；可修复网络后重新运行 apt-get update。' >&2
        else
            log "自动恢复未完成，请保留并手动检查备份：$BACKUP" >&2
        fi
        if (( rc == 0 )); then rc=1; fi
    fi
    [[ -z "$WORK" ]] || rm -rf -- "$WORK"
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if (( ! PREVIEW )); then
    [[ ! -L "$LOCK" ]] || die "锁文件不能是符号链接：$LOCK"
    exec 9>"$LOCK"
    flock -n 9 || die '另一个换源进程正在运行'
    [[ ! -L "$BACKUP_ROOT" ]] || die '备份目录不能是符号链接'
    install -d -m 0700 -- "$BACKUP_ROOT"
    [[ $(realpath -e -- "$BACKUP_ROOT") == "$BACKUP_ROOT" &&
       $(stat -c %u -- "$BACKUP_ROOT") == 0 ]] || die '备份目录路径或所有者不安全'
fi

save_backup() {
    local relative
    BACKUP=$(mktemp -d "$BACKUP_ROOT/$(date +%Y%m%d-%H%M%S)-XXXXXX")
    : > "$BACKUP/manifest"
    for relative in "${CHANGED[@]}"; do
        check_file "$APT_DIR/$relative"
        if [[ -e "$APT_DIR/$relative" ]]; then
            install -d -m 0700 -- "$BACKUP/files/$(dirname -- "$relative")"
            cp -p -- "$APT_DIR/$relative" "$BACKUP/files/$relative"
            cmp -s -- "$APT_DIR/$relative" "$BACKUP/files/$relative" || die '备份校验失败'
            printf 'present %s\n' "$relative" >> "$BACKUP/manifest"
        else
            printf 'absent %s\n' "$relative" >> "$BACKUP/manifest"
        fi
    done
    log "备份目录：$BACKUP"
}

update_indexes() {
    # APT otherwise returns success for some failed downloads and keeps old indexes.
    apt-get -o APT::Update::Error-Mode=any -o Acquire::Retries=1 \
        -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update
}

if [[ "$MODE" == restore ]]; then
    [[ -d "$RESTORE" && ! -L "$RESTORE" ]] || die '备份目录不存在或是链接'
    RESTORE=$(realpath -e -- "$RESTORE")
    [[ $(dirname -- "$RESTORE") == "$BACKUP_ROOT" ]] || die "只能恢复 $BACKUP_ROOT 下的备份"
    [[ -f "$RESTORE/manifest" && ! -L "$RESTORE/manifest" && -s "$RESTORE/manifest" ]] ||
        die '无效备份清单'
    while read -r state relative extra; do
        [[ "$state" == present || "$state" == absent ]] || die '无效备份状态'
        [[ -z "$extra" && ( "$relative" == sources.list ||
            "$relative" =~ ^sources\.list\.d/[a-zA-Z0-9_-][a-zA-Z0-9_.-]*\.(list|sources)$ ) ]] ||
            die '无效备份文件路径'
        check_file "$APT_DIR/$relative"
        if [[ "$state" == present ]]; then
            [[ -f "$RESTORE/files/$relative" && ! -L "$RESTORE/files/$relative" &&
               $(realpath -e -- "$RESTORE/files/$relative") == "$RESTORE/files/$relative" ]] ||
                die '备份文件缺失或包含链接'
        fi
        CHANGED+=("$relative")
    done < "$RESTORE/manifest"
    install -d -m 0755 -- "$APT_DIR/sources.list.d"
    save_backup
    ROLLBACK=1
    restore_files "$RESTORE"
    update_indexes
    ROLLBACK=0
    log "已恢复：$RESTORE（恢复前状态备份于 $BACKUP）"
    exit 0
fi

case "$MIRROR" in
    official) BASE=https://deb.debian.org/debian; SECURITY=https://security.debian.org/debian-security ;;
    china) BASE=https://mirrors.ustc.edu.cn/debian; SECURITY=https://mirrors.ustc.edu.cn/debian-security ;;
    aws) BASE=https://cdn-aws.deb.debian.org/debian; SECURITY=https://cdn-aws.deb.debian.org/debian-security ;;
esac

# Debian archive roots identify distro sources; Docker's /linux/debian stays intact.
# Unknown/custom layouts are retained, so the dry-run is useful before first use.
cat > "$WORK/filter.awk" <<'AWK'
function is_debian(uri, path) {
    path = tolower(uri)
    sub(/\/*$/, "", path)
    return path ~ /^https?:\/\/[^/]+\/debian(-security)?$/ ||
           path ~ /^https?:\/\/(security|deb|ftp([.][a-z0-9-]+)?)\.debian\.org$/
}
function note(types, suites) {
    changed = 1
    gsub(/[[:space:]]+/, " ", suites)
    if (types ~ /(^|[[:space:]])deb-src([[:space:]]|$)/) print "deb-src" >> meta
    if (index(" " suites " ", " " codename "-backports ")) print "backports" >> meta
}
BEGIN { if (format == "sources") { RS = ""; ORS = "\n\n" } }
format == "list" {
    if ($1 == "deb" || $1 == "deb-src") {
        for (i = 2; i <= NF; i++) {
            if ($i ~ /^https?:\/\//) {
                if (is_debian($i)) {
                    note($1, $(i+1))
                    print "# disabled by debian-sources: " $0
                    next
                }
                break
            }
        }
    }
    print; next
}
format == "sources" {
    delete fields; delete keys
    count = split($0, lines, "\n"); key = ""
    for (i = 1; i <= count; i++) {
        if (lines[i] ~ /^[[:space:]]*#/) continue
        if (lines[i] ~ /^[^[:space:]:]+:/) {
            key = tolower(lines[i]); sub(/:.*/, "", key)
            value = lines[i]; sub(/^[^:]+:[[:space:]]*/, "", value)
            fields[key] = value
        } else if (lines[i] ~ /^[[:space:]]/ && key != "") {
            fields[key] = fields[key] " " lines[i]
        }
        keys[i] = key
    }
    enabled = tolower(fields["enabled"]); gsub(/[[:space:]]/, "", enabled)
    if (enabled == "no") { print; next }
    n = split(fields["uris"], uris, /[[:space:]]+/); kept = ""; removed = 0
    for (i = 1; i <= n; i++) {
        if (is_debian(uris[i])) removed = 1
        else if (uris[i] != "") kept = kept (kept == "" ? "" : " ") uris[i]
    }
    if (!removed) { print; next }
    note(fields["types"], fields["suites"])
    if (kept == "") {
        # Original stanzas are in the backup; removing them avoids accumulating
        # disabled copies every time the managed file is switched again.
        next
    } else {
        result = ""; emitted = 0
        for (i = 1; i <= count; i++) {
            if (keys[i] == "uris") {
                if (emitted) continue
                line = "URIs: " kept; emitted = 1
            } else line = lines[i]
            result = result (result == "" ? "" : "\n") line
        }
        print result
    }
}
END { if (!changed) exit 3 }
AWK

mkdir -p "$WORK/staged/sources.list.d"
: > "$WORK/features"
shopt -s nullglob
FILES=("$APT_DIR/sources.list" "$APT_DIR/sources.list.d/"*.list "$APT_DIR/sources.list.d/"*.sources)
for file in "${FILES[@]}"; do
    [[ -e "$file" || -L "$file" ]] || continue
    relative=${file#"$APT_DIR/"}
    # APT ignores sourceparts filenames outside this character set.
    [[ "$relative" == sources.list || ${file##*/} =~ ^[a-zA-Z0-9_.-]+\.(list|sources)$ ]] || continue
    check_file "$file"
    format=list
    [[ "$file" != *.sources ]] || format=sources
    rc=0
    awk -v format="$format" -v meta="$WORK/features" -v codename="$CODENAME" \
        -f "$WORK/filter.awk" "$file" > "$WORK/staged/$relative" || rc=$?
    case "$rc" in
        0) CHANGED+=("$relative") ;;
        3) rm -f -- "$WORK/staged/$relative" ;;
        *) die "解析软件源失败：$file" ;;
    esac
done

MANAGED=sources.list.d/debian.sources
check_file "$APT_DIR/$MANAGED"
if [[ ! -e "$WORK/staged/$MANAGED" ]]; then
    if [[ -e "$APT_DIR/$MANAGED" ]]; then
        cp -- "$APT_DIR/$MANAGED" "$WORK/staged/$MANAGED"
    else
        : > "$WORK/staged/$MANAGED"
    fi
    CHANGED+=("$MANAGED")
fi
TYPES=deb
if grep -qx deb-src "$WORK/features"; then TYPES='deb deb-src'; fi
SUITES="$CODENAME $CODENAME-updates"
if grep -qx backports "$WORK/features"; then SUITES+=" $CODENAME-backports"; fi
# Keep a blank stanza separator even if a pre-existing file lacked its final LF.
awk 'BEGIN { RS = ""; ORS = "\n\n" } { print }' "$WORK/staged/$MANAGED" > "$WORK/prefix"
mv -- "$WORK/prefix" "$WORK/staged/$MANAGED"
cat >> "$WORK/staged/$MANAGED" <<EOF
# Managed by debian-sources.sh: $MIRROR
Types: $TYPES
URIs: $BASE
Suites: $SUITES
Components: main contrib non-free non-free-firmware
Signed-By: $KEYRING

Types: $TYPES
URIs: $SECURITY
Suites: $CODENAME-security
Components: main contrib non-free non-free-firmware
Signed-By: $KEYRING
EOF

log "选择镜像：$MIRROR"
if (( PREVIEW )); then
    for relative in "${CHANGED[@]}"; do
        original="$APT_DIR/$relative"
        [[ -f "$original" ]] || original=/dev/null
        rc=0
        diff -u --label "$APT_DIR/$relative (原配置)" --label "$APT_DIR/$relative (新配置)" \
            "$original" "$WORK/staged/$relative" || rc=$?
        (( rc <= 1 )) || die '生成预览失败'
    done
    log '预览完成，未修改系统配置。'
    exit 0
fi

save_backup
install -d -m 0755 -- "$APT_DIR/sources.list.d"
ROLLBACK=1
for relative in "${CHANGED[@]}"; do
    check_file "$APT_DIR/$relative"
    temp=$(mktemp "$APT_DIR/.debian-sources.XXXXXX")
    install -m 0644 -- "$WORK/staged/$relative" "$temp"
    mv -f -- "$temp" "$APT_DIR/$relative"
    cmp -s -- "$WORK/staged/$relative" "$APT_DIR/$relative" || die '写入后校验失败'
done
update_indexes
ROLLBACK=0
log "已切换到 $MIRROR，软件包索引更新成功。"
log "恢复命令：sudo bash debian-sources.sh --restore '$BACKUP'"
