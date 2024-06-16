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

VERSION=$(curl -s https://api.github.com/repos/librespeed/speedtest-cli/releases/latest \
    | grep tag_name \
    | cut -d ":" -f2 \
    | sed 's/\"//g;s/\,//g;s/\ //g;s/v//')

sudo curl -Lo librespeed-cli.tar.gz "https://github.com/librespeed/speedtest-cli/releases/download/v${VERSION}/librespeed-cli_${VERSION}_linux_${ARCH}.tar.gz"
sudo tar zxvf librespeed-cli.tar.gz --transform="s/librespeed-cli_\${VERSION}_linux_\${ARCH}/librespeed-cli"
cd librespeed-cli && sudo chown root:root librespeed-cli && sudo chmod +x librespeed-cli && mv librespeed-cli /usr/local/bin/
cd && rm -rf librespeed-cli librespeed-cli.tar.gz
grep -qE '^alias[ ]*lsp=' ~/.zshrc || echo "alias lsp ='librespeed-cli'" >> ~/.zshrc
grep -qE '^alias[ ]*lspu=' ~/.zshrc || echo "alias lspu='librespeed-cli --no-download'" >> ~/.zshrc
grep -qE '^alias[ ]*lspus=' ~/.zshrc || echo "alias lspus='librespeed-cli --no-download --concurrent 1'" >> ~/.zshrc
grep -qE '^alias[ ]*lsps=' ~/.zshrc || echo "alias lsps='librespeed-cli --concurrent 1'" >> ~/.zshrc
source ~/.zshrc
