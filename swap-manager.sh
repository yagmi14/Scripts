#!/usr/bin/env bash
set -e

SWAP_FILE="/swapfile"
DEFAULT_SWAP_SIZE="1G"
SWAPPINESS="10"

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "请使用 root 权限运行，例如：sudo bash $0"
        exit 1
    fi
}

show_status() {
    echo
    echo "当前内存状态："
    free -h

    echo
    echo "当前 swap 状态："
    swapon --show || true

    echo
}

validate_size() {
    local size="$1"
    if [[ "$size" =~ ^[0-9]+[GgMm]$ ]]; then
        return 0
    else
        return 1
    fi
}

size_to_mb() {
    local size="$1"
    local number unit

    number="${size::-1}"
    unit="${size: -1}"

    case "$unit" in
        G|g)
            echo $((number * 1024))
            ;;
        M|m)
            echo "$number"
            ;;
        *)
            echo 0
            ;;
    esac
}

remove_fstab_entry() {
    if grep -qE "^[[:space:]]*$SWAP_FILE[[:space:]]+" /etc/fstab; then
        sed -i.bak "\|^[[:space:]]*$SWAP_FILE[[:space:]]|d" /etc/fstab
        echo "已从 /etc/fstab 删除 swap 开机挂载项，原文件备份为 /etc/fstab.bak"
    fi
}

create_swap() {
    local swap_size="$1"

    if [ -z "$swap_size" ]; then
        swap_size="$DEFAULT_SWAP_SIZE"
    fi

    if ! validate_size "$swap_size"; then
        echo "大小格式错误，请输入类似 1G、2G、512M"
        return 1
    fi

    echo
    echo "准备创建 swap：$SWAP_FILE"
    echo "swap 大小：$swap_size"
    echo "物理内存优先策略：vm.swappiness=$SWAPPINESS"

    if swapon --show | grep -q "$SWAP_FILE"; then
        echo
        read -r -p "$SWAP_FILE 已启用，是否删除并重新创建？[y/N]: " confirm
        case "$confirm" in
            y|Y)
                delete_swap
                ;;
            *)
                echo "已取消创建。"
                return 0
                ;;
        esac
    elif [ -f "$SWAP_FILE" ]; then
        echo
        read -r -p "$SWAP_FILE 已存在但未启用，是否删除并重新创建？[y/N]: " confirm
        case "$confirm" in
            y|Y)
                rm -f "$SWAP_FILE"
                remove_fstab_entry
                ;;
            *)
                echo "已取消创建。"
                return 0
                ;;
        esac
    fi

    echo
    echo "正在创建 swap 文件..."

    if command -v fallocate >/dev/null 2>&1; then
        if ! fallocate -l "$swap_size" "$SWAP_FILE"; then
            echo "fallocate 创建失败，改用 dd 创建..."
            dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$(size_to_mb "$swap_size")" status=progress
        fi
    else
        dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$(size_to_mb "$swap_size")" status=progress
    fi

    echo "设置 swap 文件权限..."
    chmod 600 "$SWAP_FILE"

    echo "格式化为 swap..."
    mkswap "$SWAP_FILE"

    echo "启用 swap..."
    swapon "$SWAP_FILE"

    echo "写入 /etc/fstab，设置开机自动启用..."
    remove_fstab_entry
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab

    echo "设置系统优先使用物理内存..."
    cat > /etc/sysctl.d/99-swap.conf <<EOF
vm.swappiness=$SWAPPINESS
EOF

    sysctl -p /etc/sysctl.d/99-swap.conf >/dev/null

    echo
    echo "swap 创建完成。"
    show_status
}

delete_swap() {
    echo
    echo "准备删除 swap：$SWAP_FILE"

    if swapon --show | grep -q "$SWAP_FILE"; then
        echo "正在关闭 swap..."
        swapoff "$SWAP_FILE"
    fi

    remove_fstab_entry

    if [ -f "$SWAP_FILE" ]; then
        echo "正在删除 swap 文件..."
        rm -f "$SWAP_FILE"
    else
        echo "$SWAP_FILE 不存在。"
    fi

    if [ -f /etc/sysctl.d/99-swap.conf ]; then
        read -r -p "是否删除 swappiness 配置 /etc/sysctl.d/99-swap.conf？[y/N]: " confirm
        case "$confirm" in
            y|Y)
                rm -f /etc/sysctl.d/99-swap.conf
                echo "已删除 swappiness 配置。"
                ;;
            *)
                echo "保留 swappiness 配置。"
                ;;
        esac
    fi

    echo
    echo "swap 删除完成。"
    show_status
}

main_menu() {
    while true; do
        echo "=============================="
        echo " Debian 系统 swap 管理脚本"
        echo "=============================="
        echo "1. 创建 swap，默认 1G"
        echo "2. 创建自定义大小 swap"
        echo "3. 删除 swap"
        echo "4. 查看当前内存和 swap"
        echo "5. 退出"
        echo

        read -r -p "请选择操作 [1-5]: " choice

        case "$choice" in
            1)
                create_swap "$DEFAULT_SWAP_SIZE"
                ;;
            2)
                read -r -p "请输入 swap 大小，例如 1G、2G、512M，直接回车默认 1G: " custom_size
                custom_size="${custom_size:-$DEFAULT_SWAP_SIZE}"
                create_swap "$custom_size"
                ;;
            3)
                read -r -p "确认删除 swap？[y/N]: " confirm
                case "$confirm" in
                    y|Y)
                        delete_swap
                        ;;
                    *)
                        echo "已取消删除。"
                        ;;
                esac
                ;;
            4)
                show_status
                ;;
            5)
                echo "退出。"
                exit 0
                ;;
            *)
                echo "无效选择，请重新输入。"
                ;;
        esac

        echo
    done
}

check_root
main_menu
