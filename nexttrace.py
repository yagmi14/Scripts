#!/usr/bin/env python

# -*- coding: utf-8 -*-

import subprocess

options = [
    "0) 🇨🇳 IPV6",    
    "1) 🇨🇳 CT",
    "2) 🇨🇳 CU",
    "3) 🇨🇳 CM",
    "4) 🇨🇳 Others",
    "5) 🇨🇳 SJW",    
    "6) 🇨🇳 SHA",
    "7) 🇨🇳 CAN",    
    "8) 🇭🇰 HK",
    "9) 🇹🇼 TW",
    "10) 🇯🇵 JP",
    "11) 🇸🇬 SG",
    "12) 🇺🇸 US",    
    "13) 🇪🇺 EU",
    "14) 🇦🇺 AU",
    "15) 🇺🇳 TG",
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
            # IPV6
            subprocess.call(["nexttrace", "-MT", "dlied4.csy.tcdnos.com"]) # CT
            subprocess.call(["nexttrace", "-MT", "ml-dlied4.bytes.tcdnos.com"]) # CU
            subprocess.call(["nexttrace", "-MT", "875e1151af8aa9e3b793f51f6049996d.dlied1.cdntips.net"]) # CM        
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
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "218.107.8.18"])
        elif choice == 3:
            # CM
            subprocess.call(["nexttrace", "-MT", "112.34.111.194"])
            subprocess.call(["nexttrace", "-MT", "111.62.68.17"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.204.34.2"])
            subprocess.call(["nexttrace", "-MT", "111.8.9.73"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "218.204.182.226"])
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
            # SJW
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "27.185.201.1"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.240.159.62"])
            subprocess.call(["nexttrace", "-MT", "111.62.68.17"])
        elif choice == 6:
            # SHA
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "124.74.52.254"])            
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "210.51.57.10"])
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "120.204.34.2"])
        elif choice == 7:
            # CAN
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "61.144.6.18"]) # CAN-CT
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "218.107.8.18"]) # CAN-CU
            subprocess.call(["nexttrace", "-MT", "-p", "65499", "218.204.182.226"]) # CAN-CM

        elif choice == 8:
            # HK
            subprocess.call(["nexttrace", "-M", "103.229.54.254"]) # Akari-HKG
            subprocess.call(["nexttrace", "-MT", "oss-cn-hongkong.aliyuncs.com"]) # Alibaba-HKG
            subprocess.call(["nexttrace", "-M", "23.247.139.3"]) # Apernet-HKG
            subprocess.call(["nexttrace", "-M", "156.251.180.1"]) # Cera-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "speedtestbb.hk.chinamobile.com"]) # CMHK-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "speedtest.hk210.hkg.cn.ctcsci.com"]) # CTCSCI-HKG
            subprocess.call(["nexttrace", "-MT4", "hkg.download.datapacket.com"]) # Datacamp-HKG                        
            subprocess.call(["nexttrace", "-M", "154.3.33.110"]) # Dmit-HKG
            subprocess.call(["nexttrace", "-M", "209.146.125.124"]) # Eons-HKG
            subprocess.call(["nexttrace", "-M", "91.199.84.1"]) # Gcore-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "ookla-speedtest-central.hgconair.hgc.com.hk"]) # HGC-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "speedtest12.hkbn.net"]) # HKBN-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "suntechspeedtest.com"]) # HKT-HKG
            subprocess.call(["nexttrace", "-MT", "-p", "8080", "hytron-hk.hytron.io"]) # Hytron-HKG
            subprocess.call(["nexttrace", "-M", "103.116.72.2"]) # Jinx-HKG
            subprocess.call(["nexttrace", "-M", "38.59.254.150"]) # Kirino-HKG
            subprocess.call(["nexttrace", "-M", "45.11.104.3"]) # Misaka-HKG
            subprocess.call(["nexttrace", "-M", "23.26.90.5"]) # Nearoute-HKG
            subprocess.call(["nexttrace", "-M", "178.173.249.1"]) # NeroCloud-HKG
            subprocess.call(["nexttrace", "-M", "157.254.32.1"]) # Sharon-HKG
            subprocess.call(["nexttrace", "-M", "103.213.4.13"]) # Skywolf-HKG
            subprocess.call(["nexttrace", "-M", "43.251.133.23"]) # WTT-HKG
            subprocess.call(["nexttrace", "-M", "157.119.103.1"]) # xTom-HKG
            subprocess.call(["nexttrace", "-M", "156.59.103.1"]) # Zenlayer-HKG
            subprocess.call(["nexttrace", "-MT", "ec2.ap-east-1.amazonaws.com"]) # AWS-HKG
            subprocess.call(["nexttrace", "-MT", "speedtestea.blob.core.windows.net"]) # Azure-HKG
            subprocess.call(["nexttrace", "-M", "35.220.230.27"]) # GCP-HKG
            # Add more tracing commands for HK option as needed
        elif choice == 9:
            # TW
            subprocess.call(["nexttrace", "-M", "35.229.225.8"]) # GCP-TW
            subprocess.call(["nexttrace", "-M", "hinet.net"]) # HiNet-TPE              
        elif choice == 10:
            # JP
            subprocess.call(["nexttrace", "-M4", "speedtest.tokyo2.linode.com"]) # Akamai-NRT 
            subprocess.call(["nexttrace", "-M4", "tyo.download.datapacket.com"]) # Datacamp-NRT                        
            subprocess.call(["nexttrace", "-M", "45.88.193.5"]) # Dmit-NRT
            subprocess.call(["nexttrace", "-M", "103.168.154.1"]) # Eons-NRT
            subprocess.call(["nexttrace", "-M", "185.188.5.1"]) # Jinx-NRT
            subprocess.call(["nexttrace", "-M", "106.180.224.1"]) # Kddi-NRT            
            subprocess.call(["nexttrace", "-M", "212.107.30.1"]) # Kirino-NRT
            subprocess.call(["nexttrace", "-M", "103.170.232.48"]) # Misaka-NRT
            subprocess.call(["nexttrace", "-M", "89.116.88.18"]) # Nearoute-NRT
            subprocess.call(["nexttrace", "-M", "103.90.136.3"]) # NeroCloud-NRT
            subprocess.call(["nexttrace", "-M", "140.227.118.6"]) # NttPC-NRT            
            subprocess.call(["nexttrace", "-M", "157.254.198.1"]) # Sharon-NRT         
            subprocess.call(["nexttrace", "-M", "126.40.32.184"]) # Softbank-NRT
            subprocess.call(["nexttrace", "-M4", "hnd-jp-ping.vultr.com"]) # Vultr-NRT                                    
            subprocess.call(["nexttrace", "-M", "149.62.44.1"]) # xTom-NRT
            subprocess.call(["nexttrace", "-M", "ec2.ap-northeast-1.amazonaws.com"]) # AWS-NRT
            subprocess.call(["nexttrace", "-M", "speedtestjpe.blob.core.windows.net"]) # Azure-NRT
            subprocess.call(["nexttrace", "-M", "34.146.177.11"]) # GCP-NRT            
        elif choice == 11:
            # SG
            subprocess.call(["nexttrace", "-M", "-4", "speedtest.singapore.linode.com"]) # Akamai-SIN
            subprocess.call(["nexttrace", "-M", "103.84.216.2"]) # Akari-SIN
            subprocess.call(["nexttrace", "-M4", "sgp.download.datapacket.com"]) # Datacamp-SIN            
            subprocess.call(["nexttrace", "-M", "159.89.192.4"]) # DigitalOcean-SIN
            subprocess.call(["nexttrace", "-M", "38.150.8.1"]) # Eons-SIN
            subprocess.call(["nexttrace", "-M", "159.138.84.2"]) # Huawei-SIN
            subprocess.call(["nexttrace", "-M", "103.142.140.1"]) # Kirino-SIN
            subprocess.call(["nexttrace", "-M", "194.156.163.2"]) # Misaka-SIN
            subprocess.call(["nexttrace", "-M", "185.151.146.2"]) # Nearoute-SIN
            subprocess.call(["nexttrace", "-M", "178.173.235.128"]) # NeroCloud-SIN
            subprocess.call(["nexttrace", "-M4", "sgp.proof.ovh.net"]) # OVH-SIN
            subprocess.call(["nexttrace", "-M4", "sg.lg.speedypage.com"]) # SpeedyPage-SIN            
            subprocess.call(["nexttrace", "-M4", "sgp-ping.vultr.com"]) # Vultr-SIN
            subprocess.call(["nexttrace", "-M", "185.194.54.1"]) # xTom-SIN         
            subprocess.call(["nexttrace", "-M", "ec2.ap-southeast-1.amazonaws.com"]) # AWS-SIN
            subprocess.call(["nexttrace", "-M", "feitsui-s3.azurewebsites.net"]) # Azure-SIN
            subprocess.call(["nexttrace", "-M", "34.87.56.6"]) # GCP-SIN
            # Add more tracing commands for SG option as needed
        elif choice == 12:
            # US
            subprocess.call(["nexttrace", "-M4", "speedtest.los-angeles.linode.com"]) # Akamai-LAX
            subprocess.call(["nexttrace", "-M", "77.247.126.11"]) # Clouvider-LAX
            subprocess.call(["nexttrace", "-M4", "lax.download.datapacket.com"]) # Datacamp-LAX
            subprocess.call(["nexttrace", "-M4", "speedtest.lv.buyvm.net"]) # FranTech-LAS
            subprocess.call(["nexttrace", "-M4", "hil-speed.hetzner.com"]) # Hetzner-HIL 
            subprocess.call(["nexttrace", "-M4", "mia.hostodo.com"]) # Hostodo-MIA 
            subprocess.call(["nexttrace", "-M4", "hil.proof.ovh.us"]) # OVH-HIL  
            subprocess.call(["nexttrace", "-M4", "lax-ca-us-ping.vultr.com"]) # Vultr-LAX                                    
            subprocess.call(["nexttrace", "-M", "ec2.us-west-2.amazonaws.com"]) # AWS-OR
            subprocess.call(["nexttrace", "-M", "35.247.10.7"]) # GCP-OR
        elif choice == 13:
            # EU
            subprocess.call(["nexttrace", "-M4", "speedtest.frankfurt.linode.com"]) # Akamai-FRA 
            subprocess.call(["nexttrace", "-M", "185.42.223.2"]) # Clouvider-LHR
            subprocess.call(["nexttrace", "-M4", "par.download.datapacket.com"]) # Datacamp-PAR
            subprocess.call(["nexttrace", "-M4", "speedtest.lu.buyvm.net"]) # FranTech-LUX
            subprocess.call(["nexttrace", "-M4", "nbg1-speed.hetzner.com"]) # Hetzner-NUE
            subprocess.call(["nexttrace", "-M4", "speedtest.fra1.hivelocity.net"]) # Hivelocity-FRA                                           
            subprocess.call(["nexttrace", "-M", "38.59.228.10"]) # Kirino-FRA
            subprocess.call(["nexttrace", "-M", "45.142.247.4"]) # Misaka-BER
            subprocess.call(["nexttrace", "-M", "45.142.246.240"]) # Misaka-MOW 
            subprocess.call(["nexttrace", "-M4", "lookingglass.netcup.net"]) # Netcup-NUE 
            subprocess.call(["nexttrace", "-M4", "gra.proof.ovh.net"]) # OVH-GRA              
            subprocess.call(["nexttrace", "-M4", "fra-de-ping.vultr.com"]) # Vultr-FRA                                                                     
            subprocess.call(["nexttrace", "-M", "ec2.eu-central-1.amazonaws.com"]) # AWS-FRA
            subprocess.call(["nexttrace", "-M", "34.89.121.0"]) # GCP-LON            
            # Add more tracing commands for SG option as needed
        elif choice == 14:
            # AU
            subprocess.call(["nexttrace", "-M4", "speedtest.syd1.linode.com"]) # Akamai-SDY
            subprocess.call(["nexttrace", "-M", "34.116.127.76"]) # GCP-SDY            
            subprocess.call(["nexttrace", "-M", "ec2.ap-southeast-2.amazonaws.com"]) # AWS-SDY
        elif choice == 15:
            # TG
            subprocess.call(["nexttrace", "-M", "91.108.56.100"]) # Telegram-SG
            subprocess.call(["nexttrace", "-M", "149.154.167.100"]) # Telegram-NL            
            subprocess.call(["nexttrace", "-M", "149.154.175.100"]) # Telegram-US

    else:
        print("无效输入，请重试！")
except ValueError:
    print("无效输入，请输入一个数字。")
except KeyboardInterrupt:
    print("\n程序已被中断。")
