#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

options = [
    "0) 🇨🇳 CN",
    "1) 🇨🇳 CT",
    "2) 🇨🇳 CU",
    "3) 🇨🇳 CMCC",
    "4) 🇨🇳 Others",
    "5) 🇭🇰 HK",
    "6) 🇯🇵 JP",
    "7) 🇸🇬 SG",
    "8) 🇪🇺 EU",
]

num_columns = 3
num_options = len(options)
num_rows = (num_options + num_columns - 1) // num_columns

formatted_options = ""
for i in range(num_rows):
    for j in range(i, num_options, num_rows):
        formatted_options += f"{options[j]}\t"
    formatted_options += "\n"

print("请选择:")
print(formatted_options)

try:
    choice = int(input("输入选择: "))
    if 0 <= choice < num_options:
        print(f"您选择了: {options[choice]}")
        if choice == 0:
            # CT
            subprocess.call(["nexttrace", "-T", "-p", "65499", "27.185.201.1"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "124.74.52.254"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.144.6.18"])
            # CU
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.240.159.62"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "210.51.57.10"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "163.177.38.106"])
            # CMCC
            subprocess.call(["nexttrace", "-T", "111.62.68.4"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "120.204.34.2"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "120.198.26.254"])
            # Others
            subprocess.call(["nexttrace", "-T", "58.32.4.1"])
            subprocess.call(["nexttrace", "-T", "210.13.67.106"])
            subprocess.call(["nexttrace", "-T", "223.70.155.77"])
            subprocess.call(["nexttrace", "-T", "211.156.140.17"])
            subprocess.call(["nexttrace", "-T", "166.111.4.39"])
            subprocess.call(["nexttrace", "-T", "159.226.254.1"])
        elif choice == 1:
            # CT
            subprocess.call(["nexttrace", "-T", "-p", "65499", "219.141.150.166"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "27.185.201.1"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.178.65.90"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "124.74.52.254"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.150.151.122"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.144.6.18"])
        elif choice == 2:
            # CU
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.135.214.54"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "61.240.159.62"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "60.13.41.246"])
            subprocess.call(["nexttrace", "-T", "-p", "40001", "cu.lightnovel.cn"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "210.51.57.10"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "58.20.176.94"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "163.177.38.106"])
        elif choice == 3:
            # CMCC
            subprocess.call(["nexttrace", "-T", "111.13.111.99"])
            subprocess.call(["nexttrace", "-T", "111.62.68.4"])
            subprocess.call(["nexttrace", "-T", "211.139.80.33"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "120.204.34.2"])
            subprocess.call(["nexttrace", "-T", "111.8.9.73"])
            subprocess.call(["nexttrace", "-T", "-p", "65499", "120.198.26.254"])
        elif choice == 4:
            # Others
            subprocess.call(["nexttrace", "-T", "58.32.4.1"])
            subprocess.call(["nexttrace", "-T", "210.13.67.106"])
            subprocess.call(["nexttrace", "-T", "223.70.155.77"])
            subprocess.call(["nexttrace", "-T", "211.156.140.17"])
            subprocess.call(["nexttrace", "-T", "166.111.4.39"])
            subprocess.call(["nexttrace", "-T", "159.226.254.1"])
            # Add more tracing commands for Others option as needed
        elif choice == 5:
            # HK
            subprocess.call(["nexttrace", "-T", "103.177.248.2"]) # Akari-HKG
            subprocess.call(["nexttrace", "-T", "23.247.139.3"]) # Apernet-HKG
            subprocess.call(["nexttrace", "-T", "18.162.80.8"]) # AWS-HKG
            subprocess.call(["nexttrace", "-T", "s3eastasia.blob.core.windows.net"]) # Azure-HKG
            subprocess.call(["nexttrace", "-T", "156.251.180.1"]) # Cera-HKG
            subprocess.call(["nexttrace", "-T", "154.3.33.110"]) # Dmit-HKG
            subprocess.call(["nexttrace", "-T", "209.146.125.124"]) # Eons-HKG
            subprocess.call(["nexttrace", "-T", "35.220.230.27"]) # GCP-HKG
            subprocess.call(["nexttrace", "-T", "42.3.27.8"]) # HKT-HKG
            subprocess.call(["nexttrace", "-T", "38.150.15.1"]) # Hytron-HKG
            subprocess.call(["nexttrace", "-T", "103.116.72.1"]) # Jinx-HKG
            subprocess.call(["nexttrace", "-T", "38.59.254.150"]) # Kirino-HKG
            subprocess.call(["nexttrace", "-T", "45.11.104.3"]) # Misaka-HKG
            subprocess.call(["nexttrace", "-T", "23.26.90.5"]) # Nearoute-HKG
            subprocess.call(["nexttrace", "-T", "202.8.105.130"]) # NeroCloud-HKG
            subprocess.call(["nexttrace", "-T", "103.213.4.13"]) # Skywolf-HKG
            subprocess.call(["nexttrace", "202.64.1.1"]) # WTT-HKG
            subprocess.call(["nexttrace", "-T", "157.119.103.1"]) # xTom-HKG
            subprocess.call(["nexttrace", "-T", "156.59.103.1"]) # Zenlayer-HKG
            # Add more tracing commands for HK option as needed
        elif choice == 6:
            # JP
            subprocess.call(["nexttrace", "-T", "13.112.63.251"]) # AWS-NRT
            subprocess.call(["nexttrace", "-T", "s3japaneast.blob.core.windows.net"]) # Azure-NRT
            subprocess.call(["nexttrace", "-T", "45.88.193.5"]) # Dmit-KIX
            subprocess.call(["nexttrace", "-T", "34.97.105.8"]) # GCP-KIX
            subprocess.call(["nexttrace", "-T", "185.188.5.1"]) # Jinx-NRT
            subprocess.call(["nexttrace", "-T", "212.107.30.1"]) # Kirino-NRT
            subprocess.call(["nexttrace", "-T", "103.170.232.48"]) # Misaka-NRT
            subprocess.call(["nexttrace", "-T", "89.116.88.2"]) # Nearoute-NRT
            subprocess.call(["nexttrace", "-T", "103.90.136.3"]) # NeroCloud-NRT
            subprocess.call(["nexttrace", "-T", "149.62.44.1"]) # xTom-NRT
        elif choice == 7:
            # SG
            subprocess.call(["nexttrace", "-T", "54.254.128.1"])
            # Add more tracing commands for SG option as needed
        elif choice == 8:
            # EU
            subprocess.call(["nexttrace", "-T", "38.59.228.4"]) # AkkoCloud-FRA
            # Add more tracing commands for SG option as needed
    else:
        print("无效输入，请重试！")
except ValueError:
    print("无效输入，请输入一个数字。")
except KeyboardInterrupt:
    print("\n程序已被中断。")
