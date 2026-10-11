# Scripts

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
