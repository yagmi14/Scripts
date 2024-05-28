#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

options = [
    "0) 🇨🇳 CN",
    "1) 🇨🇳 CT",
    "2) 🇨🇳 CU",
    "3) 🇨🇳 CMCC",
    "4) 🇨🇳 Others",
    "5) 🇨🇳 IPV6",
    "6) 🇭🇰 HK",
    "7) 🇹🇼 TW",
    "8) 🇯🇵 JP",
    "9) 🇸🇬 SG",
    "10) 🇺🇸 US",    
    "11) 🇪🇺 EU",
    "12) 🇦🇺 AU",    
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
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "27.185.201.1"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "124.74.52.254"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.144.6.18"])
            # CU
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.240.159.62"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "210.51.57.10"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "163.177.38.106"])
            # CMCC
            subprocess.call(["nexttrace", "-MT", "111.62.68.17"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.204.34.2"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.198.26.254"])
            # Others
            subprocess.call(["nexttrace", "-MT", "58.32.4.1"])
            subprocess.call(["nexttrace", "-MT", "210.13.67.106"])
            subprocess.call(["nexttrace", "-MT", "223.70.155.77"])
            subprocess.call(["nexttrace", "-MT", "211.156.140.17"])
            subprocess.call(["nexttrace", "-MT", "166.111.4.39"])
            subprocess.call(["nexttrace", "-MT", "159.226.254.1"])
        elif choice == 1:
            # CT
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "219.141.150.166"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "27.185.201.1"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "124.74.52.254"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.150.151.122"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.144.6.18"])
        elif choice == 2:
            # CU
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.135.214.54"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.240.159.62"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "210.51.57.10"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "58.20.176.94"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "163.177.38.106"])
        elif choice == 3:
            # CMCC
            subprocess.call(["nexttrace", "-MT", "112.34.111.194"])
            subprocess.call(["nexttrace", "-MT", "111.62.68.17"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.204.34.2"])
            subprocess.call(["nexttrace", "-MT", "111.8.9.73"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.198.26.254"])
        elif choice == 4:
            # Others
            subprocess.call(["nexttrace", "-MT", "58.32.4.1"])
            subprocess.call(["nexttrace", "-MT", "210.13.67.106"])
            subprocess.call(["nexttrace", "-MT", "223.70.155.77"])
            subprocess.call(["nexttrace", "-MT", "211.156.140.17"])
            subprocess.call(["nexttrace", "-MT", "166.111.4.39"])
            subprocess.call(["nexttrace", "-MT", "159.226.254.1"])
            subprocess.call(["nexttrace", "-MT", "oss-cn-guangzhou.aliyuncs.com"]) # Alibaba-CAN                            
            subprocess.call(["nexttrace", "-MT", "52.80.5.207"]) # AWS-PEK
            subprocess.call(["nexttrace", "-MT", "52.83.214.0"]) # AWS-Ningxia
            subprocess.call(["nexttrace", "-MT", "42.159.128.11"]) # Azure-SHA
            subprocess.call(["nexttrace", "-MT", "110.41.83.4"]) # Huawei-CAN
            subprocess.call(["nexttrace", "-MT", "cos.ap-guangzhou.myqcloud.com"]) # Tencent-CAN                            
            # Add more tracing commands for Others option as needed
        elif choice == 5:
            # IPV6
            subprocess.call(["nexttrace", "-MT", "dlied4.csy.tcdnos.com"]) # CT
            subprocess.call(["nexttrace", "-MT", "ml-dlied4.bytes.tcdnos.com"]) # CU
            subprocess.call(["nexttrace", "-MT", "875e1151af8aa9e3b793f51f6049996d.dlied1.cdntips.net"]) # CM            
        elif choice == 6:
            # HK
            subprocess.call(["nexttrace", "-MT", "103.229.54.1"]) # Akari-HKG
            subprocess.call(["nexttrace", "-MT", "oss-cn-hongkong.aliyuncs.com"]) # Alibaba-HKG
            subprocess.call(["nexttrace", "-MT", "23.247.139.3"]) # Apernet-HKG
            subprocess.call(["nexttrace", "-MT", "156.251.180.1"]) # Cera-HKG
            subprocess.call(["nexttrace", "-MT4", "hkg.download.datapacket.com"]) # Datacamp-HKG                        
            subprocess.call(["nexttrace", "-MT", "154.3.33.110"]) # Dmit-HKG
            subprocess.call(["nexttrace", "-MT", "209.146.125.124"]) # Eons-HKG
            subprocess.call(["nexttrace", "-MT", "91.199.84.1"]) # Gcore-HKG                        
            subprocess.call(["nexttrace", "-MT", "35.220.230.27"]) # GCP-HKG
            subprocess.call(["nexttrace", "-MT", "42.3.27.27"]) # HKT-HKG
            subprocess.call(["nexttrace", "-MT", "103.116.72.2"]) # Jinx-HKG
            subprocess.call(["nexttrace", "-MT", "38.59.254.150"]) # Kirino-HKG
            subprocess.call(["nexttrace", "-MT", "45.11.104.3"]) # Misaka-HKG
            subprocess.call(["nexttrace", "-MT", "23.26.90.5"]) # Nearoute-HKG
            subprocess.call(["nexttrace", "-MT", "178.173.238.1"]) # NeroCloud-HKG
            subprocess.call(["nexttrace", "-MT", "157.254.32.3"]) # Sharon-HKG
            subprocess.call(["nexttrace", "-MT", "103.213.4.13"]) # Skywolf-HKG
            subprocess.call(["nexttrace", "-MT", "43.251.133.23"]) # WTT-HKG
            subprocess.call(["nexttrace", "-MT", "157.119.103.1"]) # xTom-HKG
            subprocess.call(["nexttrace", "-MT", "156.59.103.1"]) # Zenlayer-HKG
            subprocess.call(["nexttrace", "-MT", "18.162.80.8"]) # AWS-HKG
            subprocess.call(["nexttrace", "-MT", "s3eastasia.blob.core.windows.net"]) # Azure-HKG
            # Add more tracing commands for HK option as needed
        elif choice == 7:
            # TW
            subprocess.call(["nexttrace", "-MT", "hinet.net"]) # HiNet-TPE       
        elif choice == 8:
            # JP
            subprocess.call(["nexttrace", "-MT4", "speedtest.tokyo2.linode.com"]) # Akamai-NRT 
            subprocess.call(["nexttrace", "-MT4", "tyo.download.datapacket.com"]) # Datacamp-NRT                        
            subprocess.call(["nexttrace", "-MT", "45.88.193.5"]) # Dmit-NRT
            subprocess.call(["nexttrace", "-MT", "103.168.154.1"]) # Eons-NRT
            subprocess.call(["nexttrace", "-MT", "34.97.105.37"]) # GCP-KIX
            subprocess.call(["nexttrace", "-MT", "185.188.5.1"]) # Jinx-NRT
            subprocess.call(["nexttrace", "-MT", "106.180.224.1"]) # Kddi-NRT            
            subprocess.call(["nexttrace", "-MT", "212.107.30.1"]) # Kirino-NRT
            subprocess.call(["nexttrace", "-MT", "103.170.232.48"]) # Misaka-NRT
            subprocess.call(["nexttrace", "-MT", "89.116.88.18"]) # Nearoute-NRT
            subprocess.call(["nexttrace", "-MT", "103.90.136.3"]) # NeroCloud-NRT
            subprocess.call(["nexttrace", "-MT", "140.227.118.6"]) # Ntt&PC-NRT            
            subprocess.call(["nexttrace", "-MT", "157.254.198.1"]) # Sharon-NRT         
            subprocess.call(["nexttrace", "-MT", "126.40.32.14"]) # Softbank-NRT
            subprocess.call(["nexttrace", "-MT4", "hnd-jp-ping.vultr.com"]) # Vultr-NRT                                    
            subprocess.call(["nexttrace", "-MT", "149.62.44.1"]) # xTom-NRT
            subprocess.call(["nexttrace", "-MT", "13.112.63.251"]) # AWS-NRT
            subprocess.call(["nexttrace", "-MT", "s3japaneast.blob.core.windows.net"]) # Azure-NRT
        elif choice == 9:
            # SG
            subprocess.call(["nexttrace", "-MT", "-4", "speedtest.singapore.linode.com"]) # Akamai-SIN
            subprocess.call(["nexttrace", "-MT", "103.84.216.2"]) # Akari-SIN
            subprocess.call(["nexttrace", "-MT4", "sgp.download.datapacket.com"]) # Datacamp-SIN            
            subprocess.call(["nexttrace", "-MT", "159.89.192.4"]) # DigitalOcean-SIN
            subprocess.call(["nexttrace", "-MT", "38.150.8.1"]) # Eons-SIN
            subprocess.call(["nexttrace", "-MT", "159.138.84.2"]) # Huawei-SIN
            subprocess.call(["nexttrace", "-MT", "103.142.140.1"]) # Kirino-SIN
            subprocess.call(["nexttrace", "-MT", "194.156.163.2"]) # Misaka-SIN
            subprocess.call(["nexttrace", "-MT", "185.151.146.2"]) # Nearoute-SIN
            subprocess.call(["nexttrace", "-MT", "178.173.235.128"]) # NeroCloud-SIN
            subprocess.call(["nexttrace", "-MT4", "sgp.proof.ovh.net"]) # OVH-SIN   
            subprocess.call(["nexttrace", "-MT4", "sgp-ping.vultr.com"]) # Vultr-SIN                        
            subprocess.call(["nexttrace", "-MT", "54.254.128.1"]) # AWS-SIN
            subprocess.call(["nexttrace", "-MT", "s3southeastasia.blob.core.windows.net"]) # Azure-SIN
            # Add more tracing commands for SG option as needed
        elif choice == 10:
            # US
            subprocess.call(["nexttrace", "-MT4", "speedtest.los-angeles.linode.com"]) # Akamai-LAX
            subprocess.call(["nexttrace", "-MT", "77.247.126.11"]) # Clouvider-LAX
            subprocess.call(["nexttrace", "-MT4", "lax.download.datapacket.com"]) # Datacamp-LAX                                    
            subprocess.call(["nexttrace", "-MT4", "hil-speed.hetzner.com"]) # Hetzner-HIL 
            subprocess.call(["nexttrace", "-MT4", "mia.hostodo.com"]) # Hivelocity-TPA 
            subprocess.call(["nexttrace", "-MT4", "hil.proof.ovh.us"]) # OVH-HIL  
            subprocess.call(["nexttrace", "-MT4", "lax-ca-us-ping.vultr.com"]) # Vultr-LAX                                    
            subprocess.call(["nexttrace", "-MT", "18.236.0.0"]) # AWS-PDX                     
        elif choice == 11:
            # EU
            subprocess.call(["nexttrace", "-MT4", "speedtest.frankfurt.linode.com"]) # Akamai-FRA 
            subprocess.call(["nexttrace", "-MT", "185.42.223.2"]) # Clouvider-LHR
            subprocess.call(["nexttrace", "-MT4", "par.download.datapacket.com"]) # Datacamp-PAR            
            subprocess.call(["nexttrace", "-MT4", "nbg1-speed.hetzner.com"]) # Hetzner-NUE
            subprocess.call(["nexttrace", "-MT4", "speedtest.fra1.hivelocity.net"]) # Hivelocity-FRA                                           
            subprocess.call(["nexttrace", "-MT", "38.59.228.2"]) # Kirino-FRA
            subprocess.call(["nexttrace", "-MT", "45.142.247.3"]) # Misaka-BER
            subprocess.call(["nexttrace", "-MT", "45.131.69.1"]) # Misaka-MOW 
            subprocess.call(["nexttrace", "-MT4", "lookingglass.netcup.net"]) # Netcup-NUE 
            subprocess.call(["nexttrace", "-MT4", "gra.proof.ovh.net"]) # OVH-GRA              
            subprocess.call(["nexttrace", "-MT4", "fra-de-ping.vultr.com"]) # Vultr-FRA                                                                     
            subprocess.call(["nexttrace", "-MT", "3.64.0.0"]) # AWS-FRA                                 
            # Add more tracing commands for SG option as needed
        elif choice == 12:
            # AU
            subprocess.call(["nexttrace", "-MT4", "speedtest.syd1.linode.com"]) # Akamai-SDY   
            subprocess.call(["nexttrace", "-MT", "13.236.0.253"]) # AWS-SDY                        
    else:
        print("无效输入，请重试！")
except ValueError:
    print("无效输入，请输入一个数字。")
except KeyboardInterrupt:
    print("\n程序已被中断。")
