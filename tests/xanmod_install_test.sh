#!/usr/bin/env bash
# Run the installer against a temporary filesystem with mocked package/network tools.
set -euo pipefail

REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLER=${XANMOD_TEST_INSTALLER:-"$REPO_DIR/xanmod_install.sh"}
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/bin"

cat > "$WORK/bin/mock" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
tool=${0##*/}
printf '%s %s\n' "$tool" "$*" >> "$MOCK_LOG"
case "$tool" in
    dpkg) printf '%s\n' "${MOCK_ARCH:-amd64}" ;;
    systemd-detect-virt) printf 'none\n'; exit 1 ;;
    wget)
        output=''
        for arg in "$@"; do
            case "$arg" in --output-document=*) output=${arg#*=} ;; esac
        done
        if [[ "$*" == *'/Release'* ]]; then
            if [[ "${MOCK_HTTP_ERROR:-}" != '' ]]; then
                printf '  HTTP/1.1 %s failure\n' "$MOCK_HTTP_ERROR" >&2
                exit 8
            fi
            printf 'Codename: %s\n' "${MOCK_RELEASE_CODENAME:-trixie}" > "$output"
        else
            printf 'mock public key\n' > "$output"
        fi
        ;;
    gpg)
        [[ "$GNUPGHOME" == */gnupg && -d "$GNUPGHOME" ]] || exit 90
        [[ "${MOCK_KEY_ERROR:-0}" == '0' ]] || exit 2
        while (( $# )); do
            if [[ "$1" == '--output' ]]; then printf 'mock binary key\n' > "$2"; break; fi
            shift
        done
        ;;
    apt-get)
        if [[ "$*" == *'Dir::Etc::sourcelist='* ]]; then
            [[ -f "$APT_CONFIG" ]] || exit 91
            grep -Fq "$(dirname "$APT_CONFIG")/apt.conf.d" "$APT_CONFIG" || exit 92
            [[ -d "$(dirname "$APT_CONFIG")/apt.conf.d" ]] || exit 92
            [[ "$*" == *'APT::Update::Error-Mode=any'* ]] || exit 93
            [[ "${MOCK_SIGNATURE_ERROR:-0}" == '0' ]] || exit 100
        elif [[ "$*" != *'update'* && "$*" != *'install -y'* ]]; then
            exit 94
        fi
        ;;
    apt-cache)
        # Installed packages must not supply a candidate absent from the repository.
        [[ "$*" == *'Dir::State::status='* && -f "$APT_CONFIG" ]] || exit 95
        pkg=${!#}
        if [[ "$pkg" == "$MOCK_PACKAGE" ]]; then
            printf '%s:\n  Candidate: 7.2.9-1\n' "$pkg"
        else
            printf '%s:\n  Candidate: (none)\n' "$pkg"
        fi
        if [[ "${MOCK_POLICY_STREAM:-0}" == '1' ]]; then
            # A producer must finish even when the candidate appeared near the start.
            sleep 0.1
            head -c 8388608 /dev/zero | tr '\0' ' '
            printf '\n'
        fi
        ;;
    update-grub|reboot) ;;
    lsb_release) printf 'trixie\n' ;;
    *) exit 96 ;;
esac
MOCK
chmod +x "$WORK/bin/mock"
for tool in dpkg systemd-detect-virt wget gpg apt-get apt-cache update-grub reboot lsb_release; do
    ln -s mock "$WORK/bin/$tool"
done

run_case() {
    local name=$1 expected_exit=$2 package=$3 check_only=$4 cpu_flags=$5
    shift 5
    [[ -z "${XANMOD_TEST_CASE:-}" || "$name" == "$XANMOD_TEST_CASE" ]] || return 0
    local fixture="$WORK/$name" exit_code=0 before after
    mkdir -p "$fixture/etc/apt/sources.list.d" "$fixture/etc/apt/keyrings" \
        "$fixture/var/lib/apt/lists/partial" "$fixture/root" "$fixture/boot"
    printf 'ID=debian\nPRETTY_NAME="Test Debian"\nVERSION_CODENAME=trixie\n' > "$fixture/os-release"
    printf 'flags : %s\n' "$cpu_flags" > "$fixture/cpuinfo"
    printf 'test certificate\n' > "$fixture/certificates"
    printf 'deb https://deb.xanmod.org trixie main\n' > "$fixture/etc/apt/sources.list.d/old-xanmod.list"
    printf 'original public key\n' > "$fixture/etc/apt/keyrings/xanmod-archive-keyring.gpg"
    printf 'unrelated index\n' > "$fixture/var/lib/apt/lists/debian_index"
    : > "$fixture/mock.log"

    # Only redirect host filesystem paths in the test copy; production code is unchanged.
    sed -e "s|/etc/os-release|$fixture/os-release|g" \
        -e "s|/proc/cpuinfo|$fixture/cpuinfo|g" \
        -e "s|/etc/ssl/certs/ca-certificates.crt|$fixture/certificates|g" \
        -e "s|/etc/apt|$fixture/etc/apt|g" \
        -e "s|/var/lib/apt/lists|$fixture/var/lib/apt/lists|g" \
        -e "s|/root/xanmod-install-backup-|$fixture/root/xanmod-install-backup-|g" \
        -e "s|find /boot|find $fixture/boot|g" \
        "$INSTALLER" > "$fixture/install.sh"

    before=$(find "$fixture/etc" "$fixture/var" "$fixture/root" -type f -exec sha256sum {} + | sort)
    env PATH="$WORK/bin:$PATH" MOCK_LOG="$fixture/mock.log" MOCK_PACKAGE="$package" \
        XANMOD_FLAVOR=auto AUTO_REBOOT=0 XANMOD_CHECK_ONLY="$check_only" "$@" \
        bash "$fixture/install.sh" > "$fixture/output" 2>&1 || exit_code=$?
    if [[ "$exit_code" != "$expected_exit" ]]; then
        cat "$fixture/output" >&2
        printf 'FAIL %s: expected exit %s, got %s\n' "$name" "$expected_exit" "$exit_code" >&2
        exit 1
    fi
    if [[ "$check_only" == '1' || "$expected_exit" != '0' ]]; then
        after=$(find "$fixture/etc" "$fixture/var" "$fixture/root" -type f -exec sha256sum {} + | sort)
        [[ "$before" == "$after" ]] || { printf 'FAIL %s: host files changed\n' "$name" >&2; exit 1; }
        if grep -Eq '^(apt-get install|update-grub|reboot)' "$fixture/mock.log"; then
            printf 'FAIL %s: unexpected install/boot operation\n' "$name" >&2
            exit 1
        fi
    fi
    if [[ "$expected_exit" == '0' ]]; then
        grep -Fq "$package" "$fixture/output"
        if [[ "$check_only" == '0' ]]; then
            grep -Fxq "apt-get install -y $package" "$fixture/mock.log"
            [[ -f "$fixture/etc/apt/sources.list.d/xanmod-release.list" ]]
            grep -Fq 'disabled-by-xanmod-installer' "$fixture/etc/apt/sources.list.d/old-xanmod.list"
            grep -R -Fxq 'original public key' "$fixture/root"
            [[ -f "$fixture/var/lib/apt/lists/debian_index" ]]
        fi
    fi
    printf 'PASS %s\n' "$name"
}

[[ $EUID -eq 0 ]] || { printf 'Run tests as root in an isolated Linux test environment.\n' >&2; exit 1; }
V2='cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3'
V3="$V2 avx avx2 bmi1 bmi2 f16c fma abm movbe xsave"
run_case check-v3 0 linux-xanmod-x64v3 1 "$V3"
run_case check-v2 0 linux-xanmod-x64v2 1 "$V2"
run_case streamed-policy 0 linux-xanmod-x64v2 1 "$V2" MOCK_POLICY_STREAM=1
run_case check-v1-lts 0 linux-xanmod-lts-x64v1 1 'sse2'
run_case check-lts-fallback 0 linux-xanmod-lts-x64v3 1 "$V3"
run_case unsupported-architecture 1 '' 1 "$V3" MOCK_ARCH=arm64
run_case missing-package 1 '' 1 "$V3"
run_case missing-suite 1 '' 1 "$V3" MOCK_HTTP_ERROR=404
run_case network-denied 1 '' 1 "$V3" MOCK_HTTP_ERROR=403
run_case wrong-codename 1 '' 1 "$V3" MOCK_RELEASE_CODENAME=bookworm
run_case invalid-key 2 '' 1 "$V3" MOCK_KEY_ERROR=1
run_case signature-error 100 '' 1 "$V3" MOCK_SIGNATURE_ERROR=1
run_case install-success 0 linux-xanmod-x64v3 0 "$V3"
run_case install-preflight-failed 100 '' 0 "$V3" MOCK_SIGNATURE_ERROR=1
