#!/usr/bin/env bash
# Isolated fixtures only: no host APT configuration or network is touched.
set -Eeuo pipefail
export LC_ALL=C
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
(( EUID == 0 )) || { printf 'Run as root in an isolated Linux environment.\n' >&2; exit 1; }
mkdir -p "$WORK/bin"
cat > "$WORK/bin/apt-get" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$FIXTURE/apt.log"
[[ "$*" == *'APT::Update::Error-Mode=any'* && "${!#}" == update ]] || exit 91
case "${APT_RESULT:-success}" in
    fail) exit 100 ;;
    signal) kill -TERM "$PPID"; exit 143 ;;
esac
MOCK
chmod +x "$WORK/bin/apt-get"

fail() { printf 'FAIL: %s\n' "$*" >&2; cat "$FIXTURE/output" >&2; exit 1; }
new_fixture() {
    local version=${2:-13} codename=trixie
    [[ "$version" != 12 ]] || codename=bookworm
    FIXTURE="$WORK/$1"
    mkdir -p "$FIXTURE/etc/apt/sources.list.d" "$FIXTURE/var/backups" "$FIXTURE/run/lock"
    printf 'ID=debian\nVERSION_ID="%s"\nVERSION_CODENAME=%s\nPRETTY_NAME="Debian GNU/Linux %s"\n' \
        "$version" "$codename" "$version" > "$FIXTURE/os-release"
    printf 'keyring fixture\n' > "$FIXTURE/keyring"
    printf 'deb https://deb.debian.org/debian %s main\ndeb-src https://deb.debian.org/debian %s main\n' \
        "$codename" "$codename" > "$FIXTURE/etc/apt/sources.list"
    cat > "$FIXTURE/etc/apt/sources.list.d/debian.sources" <<EOF
# Original Debian archives
Types: deb
URIs: http://deb.debian.org/debian
Suites: $codename $codename-updates $codename-backports
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: https://security.debian.org/debian-security
Suites: $codename-security
Components: main
EOF
    printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian %s stable\n' \
        "$codename" > "$FIXTURE/etc/apt/sources.list.d/docker.list"
    cat > "$FIXTURE/etc/apt/sources.list.d/vendor.sources" <<EOF
# Vendor stanza must survive byte for byte
Types: deb
URIs: https://vendor.example/repository
Suites: $codename
Components: main
EOF
    cp -a -- "$FIXTURE/etc/apt" "$FIXTURE/original"
    # Redirect only literal host paths in a test copy, not production behavior.
    sed -e "s|/etc/os-release|$FIXTURE/os-release|g" \
        -e "s|/etc/apt|$FIXTURE/etc/apt|g" \
        -e "s|/var/backups/debian-sources|$FIXTURE/var/backups/debian-sources|g" \
        -e "s|/usr/share/keyrings/debian-archive-keyring.gpg|$FIXTURE/keyring|g" \
        -e "s|/run/lock/debian-sources.lock|$FIXTURE/run/lock/debian-sources.lock|g" \
        "$REPO/debian-sources.sh" > "$FIXTURE/script.sh"
    : > "$FIXTURE/apt.log"
}
run() {
    local expected=$1 actual=0
    shift
    env PATH="$WORK/bin:$PATH" FIXTURE="$FIXTURE" APT_RESULT="${APT_RESULT:-success}" \
        bash "$FIXTURE/script.sh" "$@" > "$FIXTURE/output" 2>&1 || actual=$?
    [[ "$actual" == "$expected" ]] || fail "exit: expected $expected, got $actual ($*)"
}
unchanged() { diff -r "$FIXTURE/original" "$FIXTURE/etc/apt" || fail 'source files changed'; }
pass() { printf 'PASS %s\n' "$*"; }
backup_path() {
    local -a backups=("$FIXTURE/var/backups/debian-sources/"*)
    printf '%s\n' "${backups[0]}"
}

for version in 12 13; do
    codename=trixie
    [[ "$version" != 12 ]] || codename=bookworm
    for mirror in official china aws; do
        new_fixture "$version-$mirror" "$version"
        run 0 "$mirror"
        managed="$FIXTURE/etc/apt/sources.list.d/debian.sources"
        grep -Fxq "Suites: $codename $codename-updates $codename-backports" "$managed" || fail suites
        grep -Fxq "Suites: $codename-security" "$managed" || fail security
        grep -Fxq 'Types: deb deb-src' "$managed" || fail deb-src
        grep -Fxq 'Components: main contrib non-free non-free-firmware' "$managed" || fail components
        case "$mirror" in
            official) host=deb.debian.org ;;
            china) host=mirrors.ustc.edu.cn ;;
            aws) host=cdn-aws.deb.debian.org ;;
        esac
        grep -Fxq "URIs: https://$host/debian" "$managed" || fail mirror
        cmp "$FIXTURE/original/sources.list.d/docker.list" "$FIXTURE/etc/apt/sources.list.d/docker.list" || fail docker
        cmp "$FIXTURE/original/sources.list.d/vendor.sources" "$FIXTURE/etc/apt/sources.list.d/vendor.sources" || fail vendor
        grep -q '^# disabled by debian-sources: deb ' "$FIXTURE/etc/apt/sources.list" || fail legacy
        [[ $(wc -l < "$FIXTURE/apt.log") == 1 ]] || fail apt-count
        backup=$(backup_path)
        [[ $(stat -c %a "$backup") == 700 ]] || fail backup-permissions
        cmp "$FIXTURE/original/sources.list" "$backup/files/sources.list" || fail backup-legacy
        cmp "$FIXTURE/original/sources.list.d/debian.sources" "$backup/files/sources.list.d/debian.sources" || fail backup-deb822
        [[ ! -e "$backup/files/sources.list.d/docker.list" ]] || fail unrelated-backup
        # Running the same choice twice must not accumulate old generated stanzas.
        cp "$managed" "$FIXTURE/managed-first"
        run 0 "$mirror"
        cmp "$managed" "$FIXTURE/managed-first" || fail idempotence
        run 0 --restore "$backup"
        unchanged
        pass "Debian $version / $mirror / repeat / restore"
    done
done

new_fixture preview
run 0 china --dry-run
unchanged
[[ ! -s "$FIXTURE/apt.log" && ! -e "$FIXTURE/var/backups/debian-sources" ]] || fail preview-wrote-state
pass preview

for result in fail signal; do
    new_fixture "rollback-$result"
    export APT_RESULT=$result
    expected=100
    [[ "$result" != signal ]] || expected=143
    run "$expected" aws
    unchanged
    grep -q '原软件源已恢复' "$FIXTURE/output" || fail rollback-message
    unset APT_RESULT
    pass "rollback-$result"
done

new_fixture rollback-new-managed
rm "$FIXTURE/etc/apt/sources.list.d/debian.sources" "$FIXTURE/original/sources.list.d/debian.sources"
export APT_RESULT=fail
run 100 official
unchanged
unset APT_RESULT
pass rollback-removes-new-file

new_fixture restore-failure
run 0 official
backup=$(backup_path)
cp -a "$FIXTURE/etc/apt" "$FIXTURE/before-restore"
export APT_RESULT=fail
run 100 --restore "$backup"
diff -r "$FIXTURE/before-restore" "$FIXTURE/etc/apt" || fail restore-rollback
unset APT_RESULT
pass restore-failure-rolls-back

new_fixture mixed-uris
cat > "$FIXTURE/etc/apt/sources.list.d/mixed.sources" <<'EOF'
# Mixed stanza
Types: deb
URIs: https://deb.debian.org/debian
 https://vendor.example/repo
Suites: trixie
Components: main

# Disabled source must stay disabled
Types: deb
URIs: https://deb.debian.org/debian
Suites: trixie
Components: main
Enabled: no
EOF
run 0 aws
grep -Fxq 'URIs: https://vendor.example/repo' "$FIXTURE/etc/apt/sources.list.d/mixed.sources" || fail mixed-uri
grep -Fxq 'Enabled: no' "$FIXTURE/etc/apt/sources.list.d/mixed.sources" || fail disabled-stanza
pass mixed-and-disabled-stanzas

new_fixture preserve-managed-vendor
printf 'Types: deb\nURIs: https://vendor.example/repo\nSuites: trixie\nComponents: main' \
    > "$FIXTURE/etc/apt/sources.list.d/debian.sources"
run 0 official
grep -Fq 'URIs: https://vendor.example/repo' "$FIXTURE/etc/apt/sources.list.d/debian.sources" || fail managed-vendor
awk 'BEGIN { RS="" } /vendor.example/ { if ($0 ~ /Managed by/) exit 1 }' \
    "$FIXTURE/etc/apt/sources.list.d/debian.sources" || fail missing-stanza-separator
cp "$FIXTURE/etc/apt/sources.list.d/debian.sources" "$FIXTURE/first"
run 0 official
cmp "$FIXTURE/first" "$FIXTURE/etc/apt/sources.list.d/debian.sources" || fail managed-vendor-repeat
pass preserve-managed-vendor-without-final-newline

new_fixture empty-source-config
rm -f "$FIXTURE/etc/apt/sources.list" "$FIXTURE/etc/apt/sources.list.d/"*
run 0 china
grep -Fxq 'Types: deb' "$FIXTURE/etc/apt/sources.list.d/debian.sources" || fail empty-config
grep -Fxq 'Suites: trixie trixie-updates' "$FIXTURE/etc/apt/sources.list.d/debian.sources" || fail default-suites
run 0 --restore "$(backup_path)"
[[ ! -e "$FIXTURE/etc/apt/sources.list.d/debian.sources" ]] || fail restore-empty
pass empty-source-config

for kind in symlink hardlink directory; do
    new_fixture "unsafe-$kind"
    cp "$FIXTURE/etc/apt/sources.list" "$FIXTURE/external"
    rm "$FIXTURE/etc/apt/sources.list"
    case "$kind" in
        symlink) ln -s "$FIXTURE/external" "$FIXTURE/etc/apt/sources.list" ;;
        hardlink) ln "$FIXTURE/external" "$FIXTURE/etc/apt/sources.list" ;;
        directory) mkdir "$FIXTURE/etc/apt/sources.list" ;;
    esac
    run 1 official
    cmp "$FIXTURE/external" "$FIXTURE/original/sources.list" || fail external-file-modified
    [[ ! -s "$FIXTURE/apt.log" ]] || fail unsafe-apt
    pass "reject-$kind"
done

new_fixture linked-source-directory
mv "$FIXTURE/etc/apt/sources.list.d" "$FIXTURE/external-dir"
ln -s "$FIXTURE/external-dir" "$FIXTURE/etc/apt/sources.list.d"
run 1 aws
[[ ! -s "$FIXTURE/apt.log" ]] || fail unsafe-directory-apt
pass reject-linked-source-directory

for os in 'ubuntu:24.04:noble' 'debian:11:bullseye' 'debian:14:forky' 'debian:13:bookworm'; do
    new_fixture "unsupported-${os//:/-}"
    IFS=: read -r id version codename <<< "$os"
    printf 'ID=%s\nVERSION_ID=%s\nVERSION_CODENAME=%s\n' "$id" "$version" "$codename" > "$FIXTURE/os-release"
    run 1 official
    unchanged
    [[ ! -s "$FIXTURE/apt.log" ]] || fail unsupported-apt
    pass "reject-$os"
done

new_fixture invalid-arguments
run 1 invalid
run 1 official aws
run 1 --restore
run 1 --restore /tmp --dry-run
run 1 --restore /tmp
run 1 </dev/null
unchanged
pass invalid-arguments

new_fixture malicious-manifest
mkdir -p "$FIXTURE/var/backups/debian-sources/bad"
printf 'absent ../outside\n' > "$FIXTURE/var/backups/debian-sources/bad/manifest"
run 1 --restore "$FIXTURE/var/backups/debian-sources/bad"
unchanged
pass reject-malicious-manifest

new_fixture lock
flock "$FIXTURE/run/lock/debian-sources.lock" bash -c 'touch "$1"; sleep 5' _ "$FIXTURE/locked" &
locker=$!
while [[ ! -e "$FIXTURE/locked" ]]; do sleep 0.05; done
run 1 aws
unchanged
wait "$locker"
pass concurrent-process-rejected

printf 'All Debian source switcher tests passed.\n'
