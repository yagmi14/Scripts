#!/bin/bash

# 获取用户输入的文件名
echo "请输入文件名："
read filename

# 创建一个新文件
touch "$filename"

# 打开文件并将用户输入的内容写入其中
echo "请输入文本内容："
while read line; do
  echo "$line" > "$filename"
done

# 给予文件权限
chmod +x "$filename"

