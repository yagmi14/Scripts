#!/bin/bash

set -e -o pipefail

ARCH_RAW=$(uname -m)
case "${ARCH_RAW}" in
    'x86_64')    ARCH='amd64';;
    'x86' | 'i686' | 'i386')     ARCH='386';;
    'aarch64' | 'arm64') ARCH='arm64';;
    'armv7l')   ARCH='armv7';;
    's390x')    ARCH='s390x';;
    *)          echo "Unsupported architecture: ${ARCH_RAW}"; exit 1;;
esac

VERSION=$(curl -s https://api.github.com/repos/zhboner/realm/releases/latest \
    | grep tag_name \
    | cut -d ":" -f2 \
    | sed 's/\"//g;s/\,//g;s/\ //g;s/v//')

curl -Lo realm.tar.gz "https://github.com/zhboner/realm/releases/download/v${VERSION}/realm-${ARCH_RAW}-unknown-linux-gnu.tar.gz"

sudo tar -xvf realm.tar.gz && sudo chown root:root /root/realm && sudo chmod +x realm
sudo mv realm /usr/local/bin/realm && sudo rm realm.tar.gz

