#!/bin/bash

# 获取用户输入的文件名
echo "请输入文件名："
read filename

# 创建一个新文件
touch "$filename"

# 打开文件并将用户输入的内容写入其中
echo "请输入文本内容："
while read line; do
  echo "$line" >> "$filename"
done

# 给予文件权限
chmod +x "$filename"

# 提示用户完成
echo "文件已创建并写入。"

# 提示用户保存并退出脚本
echo "请按回车键保存并退出脚本。"
read

# 退出脚本
exit 0
