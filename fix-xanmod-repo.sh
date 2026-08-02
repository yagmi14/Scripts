#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
 echo "Please run as root: sudo bash $0" >&2
 exit 1
fi

log() {
 printf '[fix-xanmod] %s\n' "$*"
}

fail() {
 printf '[fix-xanmod] ERROR: %s\n' "$*" >&2
 exit 1
}

export DEBIAN_FRONTEND=noninteractive

SOURCE_LIST=/etc/apt/sources.list
SOURCE_DIR=/etc/apt/sources.list.d
KEYRING_DIR=/etc/apt/keyrings
KEYRING=${KEYRING_DIR}/xanmod-archive-keyring.gpg
LIST_FILE=${SOURCE_DIR}/xanmod-release.list
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP=/root/xanmod-apt-backup-${TIMESTAMP}.tar.gz

[[ -r /etc/os-release ]] || fail "/etc/os-release not found"
# shellcheck disable=SC1091
. /etc/os-release

CODENAME=${VERSION_CODENAME:-}

if [[ -z "$CODENAME" ]] && command -v lsb_release >/dev/null 2>&1; then
 CODENAME=$(lsb_release -sc 2>/dev/null || true)
fi

[[ -n "$CODENAME" ]] || fail "Unable to detect distribution codename"

ARCH=$(dpkg --print-architecture 2>/dev/null || true)
[[ "$ARCH" == "amd64" ]] || fail "XanMod official APT repository is for amd64; detected: ${ARCH:-unknown}"

install -d -m 0755 "$SOURCE_DIR" "$KEYRING_DIR"

log "Detected system: ${PRETTY_NAME:-unknown}; codename=${CODENAME}; arch=${ARCH}"
log "Backing up current APT configuration to ${BACKUP}"

tar -czf "$BACKUP" \
 --ignore-failed-read \
 "$SOURCE_LIST" \
 "$SOURCE_DIR" \
 "$KEYRING_DIR" \
 2>/dev/null || true

log "Disabling old or malformed XanMod repository entries"

# Disable XanMod entries in traditional one-line .list files and sources.list.
while IFS= read -r -d '' file; do
 if grep -qiE '(deb\.xanmod\.org|dl\.xanmod\.org)' "$file"; then
  cp -a "$file" "${file}.before-xanmod-fix-${TIMESTAMP}"

  sed -i -E \
   '/^[[:space:]]*deb(-src)?[[:space:]].*(deb\.xanmod\.org|dl\.xanmod\.org)/s|^|# disabled-by-fix-xanmod: |' \
   "$file"
 fi
done < <(
 {
  [[ -f "$SOURCE_LIST" ]] && printf '%s\0' "$SOURCE_LIST"
  find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.list' -print0 2>/dev/null
 }
)

# Remove complete XanMod stanzas from deb822 .sources files.
while IFS= read -r -d '' file; do
 if grep -qiE '(deb\.xanmod\.org|dl\.xanmod\.org)' "$file"; then
  cp -a "$file" "${file}.before-xanmod-fix-${TIMESTAMP}"
  tmp_file=$(mktemp)

  awk '
   BEGIN {
    RS=""
    ORS="\n\n"
   }

   tolower($0) !~ /(deb\.xanmod\.org|dl\.xanmod\.org)/ {
    print
   }
  ' "$file" >"$tmp_file"

  install -m 0644 "$tmp_file" "$file"
  rm -f "$tmp_file"
 fi
done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.sources' -print0 2>/dev/null)

# The canonical file will be recreated later. Remove it now so a previously
# commented/broken entry cannot coexist with the new one.
rm -f "$LIST_FILE"

log "Removing stale XanMod APT indexes"
find /var/lib/apt/lists -maxdepth 1 -type f \
 \( -iname '*xanmod*' -o -iname '*deb.xanmod.org*' \) \
 -delete 2>/dev/null || true
find /var/lib/apt/lists/partial -maxdepth 1 -type f \
 \( -iname '*xanmod*' -o -iname '*deb.xanmod.org*' \) \
 -delete 2>/dev/null || true

log "Refreshing APT without the broken XanMod entry"
if ! apt-get update \
      --allow-releaseinfo-change \
      -o Acquire::PDiffs=false; then
 fail "APT update still fails. Another repository may also be broken. Backup: ${BACKUP}"
fi

log "Installing key-management dependencies"
apt-get install -y --no-install-recommends \
 ca-certificates \
 wget \
 gnupg

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

export GNUPGHOME=${TMPDIR}/gnupg
install -d -m 0700 "$GNUPGHOME"

log "Downloading the current XanMod archive key"
wget -qO "${TMPDIR}/archive.key" \
 https://dl.xanmod.org/archive.key

[[ -s "${TMPDIR}/archive.key" ]] || fail "Downloaded XanMod key is empty"

gpg --batch --yes \
 --dearmor \
 --output "${TMPDIR}/xanmod-archive-keyring.gpg" \
 "${TMPDIR}/archive.key"

install -m 0644 \
 "${TMPDIR}/xanmod-archive-keyring.gpg" \
 "$KEYRING"

log "Checking whether XanMod publishes suite '${CODENAME}'"
if ! wget -qO "${TMPDIR}/Release" \
      "http://deb.xanmod.org/dists/${CODENAME}/Release"; then
 fail "XanMod does not publish a Release file for '${CODENAME}'. Old entries were disabled; backup: ${BACKUP}"
fi

if ! grep -Eq "^(Codename|Suite):[[:space:]]*${CODENAME}([[:space:]]|$)" \
      "${TMPDIR}/Release"; then
 log "Warning: Release metadata did not explicitly report codename/suite '${CODENAME}', but the path exists"
fi

log "Writing the official codename-based XanMod source"
cat >"$LIST_FILE" <<EOF
deb [arch=amd64 signed-by=${KEYRING}] http://deb.xanmod.org ${CODENAME} main
EOF
chmod 0644 "$LIST_FILE"

log "Refreshing APT with the repaired XanMod source"
if ! apt-get update \
      --allow-releaseinfo-change \
      -o Acquire::PDiffs=false; then
 fail "XanMod source was rewritten, but APT update failed. Review the output above. Backup: ${BACKUP}"
fi

log "Verifying repository visibility"
if apt-cache policy 2>/dev/null | grep -q 'deb.xanmod.org'; then
 log "XanMod repository is visible to APT"
else
 fail "APT update succeeded, but deb.xanmod.org is not visible in apt-cache policy"
fi

echo
echo "Repair completed."
echo "Source: ${LIST_FILE}"
echo "Suite:  ${CODENAME}"
echo "Key:    ${KEYRING}"
echo "Backup: ${BACKUP}"
echo
echo "Current source entry:"
cat "$LIST_FILE"
echo
echo "Installed XanMod kernel (if any):"
uname -r
