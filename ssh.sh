#!/bin/bash

options=(
  "01) 🇭🇰 Cera-HKG"
  "02) 🇭🇰 HKBN-HKG"
  "03) 🇭🇰 IPRaft-HKG1"
  "04) 🇭🇰 IPRaft-HKG2"
  "05) 🇭🇰 IPRaft-HKG3"
  "06) 🇭🇰 IPRaft-HKG4"
  "07) 🇭🇰 Miku-HKG"
  "21) 🇺🇸 IPRaft-SJC"
  "31) 🇺🇦 GlobalVM-IEV"
  "32) 🇮🇸 1984-REF"
  "33) 🇮🇱 Stark-IL"
)

formatted_options=$(printf "%s\n" "${options[@]}" | column -c 120)  # 调整了列宽

echo "请选择:"
echo "$formatted_options
