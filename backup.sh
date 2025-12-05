#!/bin/bash

mkdir -p ~/logs

# 日志文件路径（只记录错误）
LOG_FILE="/root/logs/backup.log"

# 通用参数（已移除 sync，改为在具体执行时指定）
# 注意：--transfers 1 和 --tpslimit 0.5 适合网络受限环境，如果只是 copy 可以适当放宽，这里暂时保持统一
COMMON_OPTIONS1="--progress --timeout 0 --transfers 1 --tpslimit 0.5"
COMMON_OPTIONS2="--progress --timeout 0 --transfers 1 --tpslimit 0.5 --ignore-existing"

# 定义目标前缀变量
DEST_PREFIX="jianguoyun:/Backup"

# 写入日志的函数
log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_error "===== 开始执行 rclone 任务 ====="

# ================= 配置区域 =================

# 1. 定义要 SYNC (同步/镜像) 的目录
# 警告：sync 会删除网盘上有但本地没有的文件
declare -A DIRS_SYNC=(
    ["/root/.config/rclone/"]="$DEST_PREFIX/rclone/"
)

# 2. 定义要 COPY (复制/增量) 的目录
# 说明：copy 只上传新文件，不会删除网盘上已存在的文件
declare -A DIRS_COPY=(
    # 示例格式： ["/本地源路径/"]="$DEST_PREFIX/网盘目标路径/"
    # ["/root/data/photos/"]="$DEST_PREFIX/photos/"
)

# ================= 执行区域 =================

# 处理 SYNC 任务
for SOURCE in "${!DIRS_SYNC[@]}"; do
    DEST="${DIRS_SYNC[$SOURCE]}"
    log_error "[SYNC] 开始同步：$SOURCE -> $DEST"
    # 这里使用 sync 命令
    if ! rclone sync $COMMON_OPTIONS1 "$SOURCE" "$DEST" 2>> "$LOG_FILE"; then
        log_error "[SYNC] 失败：$SOURCE"
    fi
done

# 处理 COPY 任务
for SOURCE in "${!DIRS_COPY[@]}"; do
    DEST="${DIRS_COPY[$SOURCE]}"
    log_error "[COPY] 开始复制：$SOURCE -> $DEST"
    # 这里使用 copy 命令
    if ! rclone copy $COMMON_OPTIONS2 "$SOURCE" "$DEST" 2>> "$LOG_FILE"; then
        log_error "[COPY] 失败：$SOURCE"
    fi
done

log_error "===== rclone 任务完成 ====="