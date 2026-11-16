#!/usr/bin/env bash
set -Eeuo pipefail

# Docker Engine installer for Debian and Ubuntu.
# Official apt repository method. Supports overrides:
#   DOCKER_APT_OS=ubuntu|debian DOCKER_APT_CODENAME=noble|bookworm|trixie bash docker_install_compat.sh

if [ "${EUID}" -ne 0 ]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "ERROR: Please run as root, or install sudo first." >&2
    exit 1
  fi
  SUDO="sudo"
else
  SUDO=""
fi

run() {
  echo "+ $*"
  ${SUDO} "$@"
}

if [ ! -r /etc/os-release ]; then
  echo "ERROR: /etc/os-release not found; cannot detect distribution." >&2
  exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release

os_id="${ID:-}"
os_like=" ${ID_LIKE:-} "
docker_os=""
codename=""

case "${os_id}" in
  ubuntu)
    docker_os="ubuntu"
    codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
    ;;
  debian)
    docker_os="debian"
    codename="${VERSION_CODENAME:-}"
    ;;
  *)
    if [[ "${os_like}" == *" ubuntu "* ]]; then
      docker_os="ubuntu"
      codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
    elif [[ "${os_like}" == *" debian "* ]]; then
      docker_os="debian"
      codename="${DEBIAN_CODENAME:-${VERSION_CODENAME:-}}"
    else
      echo "ERROR: Unsupported distribution: ID=${os_id}, ID_LIKE=${ID_LIKE:-}" >&2
      echo "Supported targets are Ubuntu and Debian." >&2
      exit 1
    fi
    ;;
esac

# Allow explicit override for derivatives or unusual /etc/os-release values.
docker_os="${DOCKER_APT_OS:-${docker_os}}"
codename="${DOCKER_APT_CODENAME:-${codename}}"

if [ -z "${docker_os}" ] || [ -z "${codename}" ]; then
  echo "ERROR: Could not determine Docker apt repository OS/codename." >&2
  echo "Try: DOCKER_APT_OS=ubuntu DOCKER_APT_CODENAME=noble bash $0" >&2
  exit 1
fi

case "${docker_os}" in
  ubuntu|debian) ;;
  *)
    echo "ERROR: DOCKER_APT_OS must be ubuntu or debian, got: ${docker_os}" >&2
    exit 1
    ;;
esac

echo "Detected system: ${PRETTY_NAME:-${os_id}}"
echo "Using Docker apt repository: https://download.docker.com/linux/${docker_os} ${codename}"

# Remove stale Docker apt source files first; otherwise apt update can keep failing on an old wrong repo.
run rm -f \
  /etc/apt/sources.list.d/docker.list \
  /etc/apt/sources.list.d/docker.sources \
  /etc/apt/sources.list.d/download_docker_com_linux_debian.list \
  /etc/apt/sources.list.d/download_docker_com_linux_debian.sources \
  /etc/apt/sources.list.d/download_docker_com_linux_ubuntu.list \
  /etc/apt/sources.list.d/download_docker_com_linux_ubuntu.sources

run apt-get update
run apt-get install -y ca-certificates curl python3

# Check that the repository suite exists before writing the source file.
if ! curl -fsSL "https://download.docker.com/linux/${docker_os}/dists/${codename}/Release" -o /dev/null; then
  echo "ERROR: Docker repository does not have a Release file for ${docker_os}/${codename}." >&2
  echo "For Ubuntu 24.04 use: DOCKER_APT_OS=ubuntu DOCKER_APT_CODENAME=noble" >&2
  echo "For Debian 12 use:   DOCKER_APT_OS=debian DOCKER_APT_CODENAME=bookworm" >&2
  echo "For Debian 13 use:   DOCKER_APT_OS=debian DOCKER_APT_CODENAME=trixie" >&2
  exit 1
fi

run install -m 0755 -d /etc/apt/keyrings
run curl -fsSL "https://download.docker.com/linux/${docker_os}/gpg" -o /etc/apt/keyrings/docker.asc
run chmod a+r /etc/apt/keyrings/docker.asc

architecture="$(dpkg --print-architecture)"
${SUDO} tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF2
Types: deb
URIs: https://download.docker.com/linux/${docker_os}
Suites: ${codename}
Components: stable
Architectures: ${architecture}
Signed-By: /etc/apt/keyrings/docker.asc
EOF2

# Remove conflicting distro packages only if they are installed.
conflicts=(docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc)
installed_conflicts=()
for pkg in "${conflicts[@]}"; do
  if dpkg-query -W -f='${db:Status-Abbrev}' "${pkg}" 2>/dev/null | grep -q '^ii'; then
    installed_conflicts+=("${pkg}")
  fi
done
if [ "${#installed_conflicts[@]}" -gt 0 ]; then
  run apt-get remove -y "${installed_conflicts[@]}"
fi

run apt-get update
run apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Merge the daemon defaults without replacing unrelated settings (mirrors, DNS, etc.).
# Package installation can start Docker before this configuration is written.
run python3 - /etc/docker/daemon.json <<'PYTHON'
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

config_path = Path(sys.argv[1])
if config_path.is_symlink():
    raise SystemExit(f"ERROR: Refusing to replace a symlink: {config_path}")
existing = config_path.exists()
original = json.loads(config_path.read_text()) if existing else {}
if not isinstance(original, dict):
    raise SystemExit("ERROR: Docker daemon.json must contain a JSON object.")
options = original.get("log-opts", {})
if not isinstance(options, dict):
    raise SystemExit("ERROR: Docker log-opts must contain a JSON object.")

# Options for a different logging driver may not be valid for json-file.
options = options.copy() if original.get("log-driver", "json-file") == "json-file" else {}
options.update({"max-size": "50m", "max-file": "5"})
config = {**original, "log-driver": "json-file", "log-opts": options}
if existing and config == original:
    subprocess.run(["dockerd", "--validate", "--config-file", str(config_path)], check=True)
    print("Docker log rotation defaults are already configured.")
else:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    fd, candidate = tempfile.mkstemp(prefix=".daemon.json.", dir=config_path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(config, stream, indent=2)
            stream.write("\n")
        if existing:
            shutil.copymode(config_path, candidate)
        else:
            os.chmod(candidate, 0o644)
        subprocess.run(["dockerd", "--validate", "--config-file", candidate], check=True)
        if existing:
            backup_fd, backup = tempfile.mkstemp(prefix="daemon.json.backup.", dir=config_path.parent)
            os.close(backup_fd)
            shutil.copy2(config_path, backup)
            print(f"Existing Docker configuration backed up to: {backup}")
        os.replace(candidate, config_path)
    finally:
        if os.path.exists(candidate):
            os.unlink(candidate)
    print("Configured Docker json-file logging: 50m x 5 files (about 250 MiB per container).")
PYTHON

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files >/dev/null 2>&1; then
  run systemctl enable docker
  run systemctl restart docker
elif command -v service >/dev/null 2>&1; then
  run service docker restart
else
  echo "WARNING: Neither systemctl nor service is available. Start Docker manually if needed." >&2
fi

if command -v docker >/dev/null 2>&1; then
  docker --version
  docker compose version
  echo "Log rotation defaults apply to new containers; recreate existing containers to use them."
  echo "Per-container or Compose logging settings override these defaults."
  echo "Docker installed. To test the daemon, run: sudo docker run hello-world"
else
  echo "ERROR: docker command was not found after installation." >&2
  exit 1
fi
