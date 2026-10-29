# Scripts

## SSH 安全加固

`ssh-hardening.sh` 为 Debian/Ubuntu 添加公钥、将 SSH 端口统一为 **40022**、
关闭密码及交互式认证，并配置使用 systemd 日志的 Fail2ban。
执行前确认脚本内的公钥属于你，并确认服务商防火墙允许 TCP 40022：

```bash
curl -fL --retry 2 https://raw.githubusercontent.com/yagmi14/Scripts/main/ssh-hardening.sh -o ssh-hardening.sh && sudo bash ssh-hardening.sh
```

SSH 认证选项以先读到的配置为准。脚本使用
`/etc/ssh/sshd_config.d/00-000-local-hardening.conf`，早于镜像常见的
`00-cloudshlii-login.conf` 和 `50-cloud-init.conf`，避免它们的密码登录设置
覆盖加固策略。旧版 `00-local-hardening.conf` 会保留，其中的旧端口按普通
配置处理。主配置在 Include 前的设置或排序更早的自定义文件仍可能冲突；
脚本会在重载前通过 `sshd -t` / `sshd -T` 检测并恢复配置。

修改前备份位于 `/root/ssh-hardening-backup-*`。完成后保留当前会话，
另开终端用公钥连接 `ssh -p 40022 root@服务器IP`，确认可登录后再关闭旧会话。
Fail2ban 阶段失败只恢复其配置，SSH 加固可能已经生效，应检查输出中的端口。

回归测试需要 Linux、root 和已有 OpenSSH 服务端；使用真实 `sshd` 解析临时配置，
模拟软件安装、防火墙和服务控制，不修改系统 SSH 设置：

```bash
sudo bash tests/ssh_hardening_test.sh
```

## Debian 一键换源

`debian-sources.sh` 自动检测 Debian 12（bookworm）或 Debian 13（trixie），
可切换官方源、中国大陆中科大 USTC 镜像、Debian AWS CDN 源。
三种方案都包含主仓库、updates 和 security，启用
`main contrib non-free non-free-firmware`，使用系统 Debian 官方密钥校验签名。

以 root 下载并打开选择菜单（普通用户请在 `bash` 前加 `sudo`）：

```bash
curl -fL --retry 2 https://raw.githubusercontent.com/yagmi14/Scripts/main/debian-sources.sh -o debian-sources.sh && bash debian-sources.sh
```

直接指定源，或先查看修改预览：

```bash
sudo bash debian-sources.sh official   # 官方
sudo bash debian-sources.sh china      # 中国大陆：中科大
sudo bash debian-sources.sh aws        # AWS CDN
bash debian-sources.sh china --dry-run # 预览，无需 root
```

脚本兼容 `/etc/apt/sources.list`、`sources.list.d/*.list` 和 Deb822 `*.sources`，
将 Debian 源统一写入 `/etc/apt/sources.list.d/debian.sources`。
按仓库地址识别 Debian 源：HTTP(S) 地址路径为 `/debian` 或 `/debian-security`，
或 Debian 官方的根地址；其他布局保留，首次使用可先预览。
Docker 等第三方源和显式禁用的 Deb822 段落保留；
原来启用的 `deb-src` 和当前版本的 `-backports` 会继续启用。
其他自定义 Debian suite 会替换为当前版本的标准 suite；脚本不安装或升级软件包。
AWS 选项使用 `cdn-aws.deb.debian.org` 的 Debian 仓库与安全仓库。

修改前，受影响源文件和恢复清单会备份至
`/var/backups/debian-sources/时间-随机后缀/`。
脚本执行严格的 `apt-get update`，任意源（含保留的第三方源）更新失败时恢复修改前的源文件；
已下载的 APT 索引不回滚。成功后会输出恢复命令：

```bash
sudo bash debian-sources.sh --restore /var/backups/debian-sources/实际备份目录
```

手动恢复前也会备份当前状态；恢复后的索引更新失败时回到恢复前配置。
脚本拒绝修改符号链接或硬链接的源文件，并通过进程锁防止自身并发运行。
它不会覆盖云平台自动生成源配置的规则；若镜像受 cloud-init 等工具管理，
需在相应工具中同步配置以保证后续重启仍然生效。

在隔离 Linux 环境运行回归测试（临时文件系统、模拟 APT，无网络或系统源改动）：

```bash
sudo bash tests/debian_sources_test.sh
```

## XanMod 内核安装

`xanmod_install.sh` 支持使用官方 XanMod APT 仓库的 amd64 Debian/Ubuntu，
自动按虚拟机实际暴露的 CPU flags 选择 x64v1/v2/v3 内核。
默认优先 MAIN，不可用时尝试 LTS；x64v1 默认使用 LTS。
LXC/OpenVZ/Docker 等共享宿主机内核的容器会被拒绝。

```bash
# 只检查仓库签名、CPU 等级和候选包，不安装或重启
sudo XANMOD_CHECK_ONLY=1 bash xanmod_install.sh

# 安装（默认不自动重启）
sudo bash xanmod_install.sh

# 指定内核分支：auto / main / lts / edge / rt
sudo XANMOD_FLAVOR=lts bash xanmod_install.sh
```

只检查模式需要系统已有 `ca-certificates`、`wget` 和 `gnupg`。
该模式使用临时 APT 配置、密钥、索引和缓存，不运行系统 APT 更新钩子，
不修改系统软件源或安装依赖。检查通过表示仓库签名有效且存在匹配的内核包；
实际安装依赖和重启后的启动结果需要另外验证。

安装模式会备份旧 XanMod 软件源及密钥到 `/root/xanmod-install-backup-*`。
依赖已存在时，先验证仓库和候选包，再修改系统软件源；缺失依赖时，
先备份并清理旧 XanMod 源，然后安装所需工具。
安装完成后检查启动配置，再自行重启；只有显式设置 `AUTO_REBOOT=1` 才自动重启。

Ubuntu 26.04（resolute）使用 APT 3.x。脚本会完整读取 `apt-cache policy` 输出，
避免提前结束管道触发 SIGPIPE，在 CPU 等级提示后静默退出。
QEMU/KVM 的 CPU 可能仅暴露 x64v2 指令集，应按客户机检测结果选包。

在 Linux 测试环境运行隔离回归测试（网络、APT 安装和启动命令均使用模拟工具）：

```bash
sudo bash tests/xanmod_install_test.sh
```
