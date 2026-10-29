#!/usr/bin/env bash
# Real sshd parsing; all service, firewall and package changes are mocked.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root on a Linux test host.' >&2; exit 1; }
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLER=${SSH_HARDENING_TEST_INSTALLER:-"$REPO_DIR/ssh-hardening.sh"}
REAL_SSHD=${SSH_HARDENING_TEST_SSHD:-$(command -v sshd || printf '/usr/sbin/sshd')}
REAL_KEYGEN=${SSH_HARDENING_TEST_KEYGEN:-$(command -v ssh-keygen)}
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/bin"
export REAL_SSHD REAL_KEYGEN
"$REAL_KEYGEN" -q -t ed25519 -N '' -f "$WORK/hostkey"

cat > "$WORK/bin/mock" <<'MOCK'
#!/usr/bin/env bash
set -Eeuo pipefail
tool=${0##*/}
printf '%s %s\n' "$tool" "$*" >> "$FIXTURE/commands"
case "$tool" in
    getent) printf 'root:x:0:0:root:%s/root:/bin/bash\n' "$FIXTURE" ;;
    sshd) exec "$REAL_SSHD" -f "$FIXTURE/etc/ssh/sshd_config" "$@" ;;
    ssh-keygen) exec "$REAL_KEYGEN" "$@" ;;
    apt-get|ufw|firewall-cmd) echo 'Unexpected package/firewall mutation' >&2; exit 90 ;;
    systemctl)
        case "$1" in
            is-active) [[ "${*: -1}" == ssh.service ]] ;;
            is-enabled) exit 1 ;;
            reload|restart)
                if [[ "${*: -1}" == ssh && "${MOCK_RELOAD_FAILURE:-0}" == 1 ]]; then exit 1; fi
                ;;
            *) : ;;
        esac
        ;;
    ss) printf 'LISTEN 0 128 0.0.0.0:40022 0.0.0.0:*\n' ;;
    fail2ban-server) [[ "${MOCK_F2B_FAILURE:-0}" == 0 ]] ;;
    fail2ban-client) printf 'Server ready\n' ;;
    sleep) : ;;
    *) exit 91 ;;
esac
MOCK
chmod +x "$WORK/bin/mock"
for tool in getent sshd ssh-keygen apt-get ufw firewall-cmd systemctl ss fail2ban-server fail2ban-client sleep; do
    ln -s mock "$WORK/bin/$tool"
done

run_case() {
    local name=$1 expected_exit=$2 mode=$3 exit_code=0 before main_before f2b_before
    shift 3
    local fixture="$WORK/$name"
    mkdir -p "$fixture/etc/ssh/sshd_config.d" "$fixture/root/.ssh" \
        "$fixture/etc/fail2ban/jail.d"
    printf 'Include %s/etc/ssh/sshd_config.d/*.conf\nPort 22\nPasswordAuthentication no\nHostKey %s/hostkey\n' \
        "$fixture" "$WORK" > "$fixture/etc/ssh/sshd_config"
    printf 'PermitRootLogin yes\nPasswordAuthentication yes\n' \
        > "$fixture/etc/ssh/sshd_config.d/00-cloudshlii-login.conf"
    printf 'PasswordAuthentication yes\n' > "$fixture/etc/ssh/sshd_config.d/50-cloud-init.conf"
    printf '# unrelated key retained\n' > "$fixture/root/.ssh/authorized_keys"
    printf '# original fail2ban settings\n' > "$fixture/etc/fail2ban/jail.d/sshd.local"
    if [[ "$mode" == legacy ]]; then
        printf 'Port 2222\nPasswordAuthentication no\nPermitRootLogin prohibit-password\n' \
            > "$fixture/etc/ssh/sshd_config.d/00-local-hardening.conf"
    elif [[ "$mode" == conflict ]]; then
        # Main-file settings before Include still take precedence; fail safely.
        sed -i '1i PasswordAuthentication yes' "$fixture/etc/ssh/sshd_config"
    elif [[ "$mode" == existing ]]; then
        printf '# pre-existing managed file\nPort 2222\n' \
            > "$fixture/etc/ssh/sshd_config.d/00-000-local-hardening.conf"
    elif [[ "$mode" == invalid ]]; then
        printf 'InvalidHardeningTestOption yes\n' >> "$fixture/etc/ssh/sshd_config"
    fi
    before=$(find "$fixture/etc/ssh" -type f -exec sha256sum {} + | sort)
    main_before=$(cat "$fixture/etc/ssh/sshd_config")
    f2b_before=$(cat "$fixture/etc/fail2ban/jail.d/sshd.local")
    # Redirect every absolute mutation path in the test copy. sshd stays real,
    # but a wrapper supplies its isolated configuration file.
    sed -e "s|/etc/ssh|$fixture/etc/ssh|g" \
        -e "s|/etc/fail2ban|$fixture/etc/fail2ban|g" \
        -e "s|/etc/systemd/system|$fixture/etc/systemd/system|g" \
        -e "s|/root/ssh-hardening-backup-|$fixture/root/ssh-hardening-backup-|g" \
        "$INSTALLER" > "$fixture/install.sh"
    env PATH="$WORK/bin:$PATH" FIXTURE="$fixture" "$@" \
        bash "$fixture/install.sh" > "$fixture/output" 2>&1 || exit_code=$?
    if [[ "$exit_code" != "$expected_exit" ]]; then
        cat "$fixture/output" >&2
        printf 'FAIL %s: expected %s, got %s\n' "$name" "$expected_exit" "$exit_code" >&2
        exit 1
    fi
    if [[ "$expected_exit" == 0 ]]; then
        local effective
        effective=$("$REAL_SSHD" -T -f "$fixture/etc/ssh/sshd_config")
        grep -Fxq 'port 40022' <<< "$effective"
        grep -Fxq 'passwordauthentication no' <<< "$effective"
        grep -Fxq 'pubkeyauthentication yes' <<< "$effective"
        grep -Eq '^permitrootlogin (without-password|prohibit-password)$' <<< "$effective"
        grep -Fxq 'kbdinteractiveauthentication no' <<< "$effective"
        grep -Fxq 'permitemptypasswords no' <<< "$effective"
        [[ $(awk '$1 == "port" {print $2}' <<< "$effective" | sort -u) == 40022 ]]
        grep -Fxq 'PermitRootLogin yes' "$fixture/etc/ssh/sshd_config.d/00-cloudshlii-login.conf"
        grep -Fxq 'backend = systemd' "$fixture/etc/fail2ban/jail.d/sshd.local"
        grep -Fxq '# unrelated key retained' "$fixture/root/.ssh/authorized_keys"
        # Repeat under the same backup timestamp and verify no duplicate keys.
        env PATH="$WORK/bin:$PATH" FIXTURE="$fixture" "$@" \
            bash "$fixture/install.sh" >> "$fixture/output" 2>&1
        [[ $(grep -c '^ssh-ed25519 ' "$fixture/root/.ssh/authorized_keys") == 2 ]]
    elif [[ "$mode" != f2b ]]; then
        [[ "$before" == "$(find "$fixture/etc/ssh" -type f -exec sha256sum {} + | sort)" ]]
        [[ "$main_before" == "$(cat "$fixture/etc/ssh/sshd_config")" ]]
        [[ "$f2b_before" == "$(cat "$fixture/etc/fail2ban/jail.d/sshd.local")" ]]
        if [[ "$mode" == conflict || "$mode" == invalid ]]; then
            ! grep -Eq '^systemctl (reload|restart) ssh' "$fixture/commands"
        fi
    else
        [[ "$f2b_before" == "$(cat "$fixture/etc/fail2ban/jail.d/sshd.local")" ]]
    fi
    printf 'PASS %s\n' "$name"
}

run_case cloud-image 0 fresh
run_case legacy-config 0 legacy
run_case existing-managed-config 0 existing
run_case main-file-conflict 1 conflict
run_case invalid-config 1 invalid
run_case service-failure-rollback 1 fresh MOCK_RELOAD_FAILURE=1
run_case existing-file-rollback 1 existing MOCK_RELOAD_FAILURE=1
run_case fail2ban-failure-rollback 1 f2b MOCK_F2B_FAILURE=1
