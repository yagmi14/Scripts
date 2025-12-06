#!/bin/bash

# 创建日志文件夹 (建议统一使用 HOME 变量，适应不同用户)
mkdir -p "$HOME/logs"

# 日志文件路径
LOG_FILE="$HOME/logs/rclone_config_sync.log"

# 定义特定目录变量
LOCAL_DIR="$HOME/.config/rclone"
REMOTE_DIR="jianguoyun:/Backup/rclone"

# 通用参数 (保留了你之前的设置：低并发，适合网络受限环境)
# 注意：sync 操作不建议加 --ignore-existing，因为 sync 的本意就是保持两端完全一致
COMMON_OPTIONS="--progress --timeout 0 --transfers 1 --tpslimit 0.5"

# 写入日志的函数
log_message() {
    local msg="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "$LOG_FILE"
    echo "$msg" # 同时输出到屏幕让用户看到
}

# ================= 交互区域 =================

echo "=========================================="
echo "   Rclone 配置文件同步工具"
echo "   当前本地路径: $LOCAL_DIR"
echo "   当前远端路径: $REMOTE_DIR"
echo "=========================================="
echo "请选择操作模式："
echo "1) 备份：本地 -> 远端 (Local Sync to Remote)"
echo "2) 恢复：远端 -> 本地 (Remote Sync to Local)"
echo "=========================================="

read -p "请输入数字 [1 或 2]: " choice

log_message "===== 开始执行任务，用户选择模式: $choice ====="

case "$choice" in
    1)
        # 模式1：备份 (Local -> Remote)
        SOURCE="$LOCAL_DIR"
        DEST="$REMOTE_DIR"
        ACTION_NAME="备份 (上传)"
        ;;
    2)
        # 模式2：恢复 (Remote -> Local)
        # 警告用户
        echo -e "\033[31m警告：你选择了从远端同步到本地。\033[0m"
        echo -e "\033[31m这将会删除本地有、但远端没有的配置文件！\033[0m"
        read -p "确认继续吗？(y/n): " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "操作已取消。"
            exit 0
        fi
        
        SOURCE="$REMOTE_DIR"
        DEST="$LOCAL_DIR"
        ACTION_NAME="恢复 (下载)"
        ;;
    *)
        echo "无效的输入，脚本退出。"
        exit 1
        ;;
esac

# ================= 执行区域 =================

log_message "[$ACTION_NAME] 开始同步：$SOURCE -> $DEST"

# 执行 Sync 命令
if rclone sync $COMMON_OPTIONS "$SOURCE" "$DEST" 2>> "$LOG_FILE"; then
    log_message "[$ACTION_NAME] 成功完成！"
else
    log_message "[$ACTION_NAME] 失败！请查看日志 $LOG_FILE"
fi

log_message "===== 任务结束 ====="
